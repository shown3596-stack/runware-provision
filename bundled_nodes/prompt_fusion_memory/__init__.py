"""Prompt Fusion RAM-only output nodes. Direct ComfyUI workflows are unaffected."""
import io
import os
import re
import stat
import threading
import time
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from aiohttp import web
import numpy as np
from PIL import Image
from server import PromptServer

_LIMIT = 384 * 1024 * 1024
_TTL = 24 * 60 * 60
_lock = threading.RLock()
_results = {}
_TOKEN = re.compile(r'^[a-f0-9]{64}$')


def _expire(now):
    with _lock:
        for key in list(_results):
            if now - _results[key][0] > _TTL:
                del _results[key]


def _cleanup_loop():
    while True:
        time.sleep(60)
        _expire(time.monotonic())
        # Interrupted predictors may leave an incomplete file in tmpfs.
        try:
            for entry in os.scandir('/dev/shm'):
                if re.fullmatch(r'prompt-fusion-sharp-[a-f0-9]{64}_[0-9]+\.ply', entry.name):
                    info = entry.stat(follow_symlinks=False)
                    if stat.S_ISREG(info.st_mode) and time.time() - info.st_mtime > _TTL:
                        os.unlink(entry.path)
                elif re.fullmatch(r'prompt-fusion-infini-[a-z0-9_]{8}', entry.name):
                    info = entry.stat(follow_symlinks=False)
                    if stat.S_ISDIR(info.st_mode) and time.time() - info.st_mtime > _TTL:
                        shutil.rmtree(entry.path)
        except OSError:
            pass


threading.Thread(target=_cleanup_loop, name='prompt-fusion-memory-expiry', daemon=True).start()


def _store(token, items):
    if not _TOKEN.fullmatch(token):
        raise ValueError('Invalid output token')
    size = sum(len(data) for data, _ in items)
    now = time.monotonic()
    with _lock:
        _expire(now)
        if token in _results:
            raise ValueError('Output token already exists')
        if not items or size > _LIMIT or size + sum(sum(len(data) for data, _ in entry[1]) for entry in _results.values()) > _LIMIT:
            raise ValueError('Prompt Fusion in-memory output capacity exhausted; retrieve previous outputs first')
        _results[token] = (now, items)


@PromptServer.instance.routes.get('/prompt-fusion-memory/v1/capabilities')
async def capabilities(request):
    try:
        from comfy_extras.nodes_gaussian_splat import _parse_ply_gaussian, _gaussian_spz_bytes
        sharp_spz = callable(_parse_ply_gaussian) and callable(_gaussian_spz_bytes)
    except ImportError:
        sharp_spz = False
    try:
        import folder_paths
        pack = Path(folder_paths.base_path) / 'custom_nodes' / 'ComfyUI-InfiniSplat'
        model = Path(folder_paths.models_dir) / 'infinisplat/checkpoints/infinisplat_rgb.ckpt'
        infini_spz = sharp_spz and (pack / '.venv/bin/python').is_file() and (pack / 'worker.py').is_file() and (pack / 'upstream/src/demo/infer_batch_images.py').is_file() and model.is_file()
    except (ImportError, AttributeError, OSError):
        infini_spz = False
    return web.json_response({'version': 1, 'images': True, 'video_mp4': True, 'qwen_audio': True, 'sharp_spz': sharp_spz, 'infinisplat_spz': infini_spz, 'sharp_splat_limit': sharp_spz, 'sharp_splat_limit_300k': sharp_spz, 'sharp_splat_limit_500k': sharp_spz, 'capacity_bytes': _LIMIT})


@PromptServer.instance.routes.get('/prompt-fusion-memory/v1/{token}/{index}')
async def read_output(request):
    token = request.match_info['token']
    index = request.match_info['index']
    if not _TOKEN.fullmatch(token) or not index.isdigit():
        raise web.HTTPNotFound()
    with _lock:
        entry = _results.get(token)
        if not entry or int(index) >= len(entry[1]):
            raise web.HTTPNotFound()
        data, mime = entry[1][int(index)]
    return web.Response(body=data, content_type=mime, headers={'Cache-Control': 'no-store'})


@PromptServer.instance.routes.delete('/prompt-fusion-memory/v1/{token}')
async def acknowledge_output(request):
    token = request.match_info['token']
    if not _TOKEN.fullmatch(token):
        raise web.HTTPNotFound()
    with _lock:
        _results.pop(token, None)
    return web.Response(status=204)


class PromptFusionMemoryImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'images': ('IMAGE',), 'token': ('STRING',)}}
    RETURN_TYPES = ()
    FUNCTION = 'save'
    OUTPUT_NODE = True
    CATEGORY = 'Prompt Fusion'

    def save(self, images, token):
        items = []
        for image in images:
            buf = io.BytesIO()
            Image.fromarray(np.clip(255.0 * image.cpu().numpy(), 0, 255).astype(np.uint8)).save(buf, format='PNG')
            data = buf.getvalue()
            if len(data) > 32 * 1024 * 1024 or len(data) + sum(len(item[0]) for item in items) > _LIMIT:
                raise ValueError('In-memory image output exceeds the supported size')
            items.append((data, 'image/png'))
        _store(token, items)
        return {'ui': {'images': [{'filename': str(i), 'subfolder': token, 'type': 'pf_memory'} for i in range(len(items))]}}


class PromptFusionMemoryVideo:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'video': ('VIDEO',), 'token': ('STRING',)}}
    RETURN_TYPES = ()
    FUNCTION = 'save'
    OUTPUT_NODE = True
    CATEGORY = 'Prompt Fusion'

    def save(self, video, token):
        from comfy_api.latest import Types
        buf = io.BytesIO()
        video.save_to(buf, format=Types.VideoContainer('mp4'), codec=Types.VideoCodec('h264'))
        data = buf.getvalue()
        if len(data) > 256 * 1024 * 1024:
            raise ValueError('In-memory video exceeds the supported size')
        if len(data) < 12 or data[4:8] != b'ftyp':
            raise ValueError('Video encoder did not return MP4')
        _store(token, [(data, 'video/mp4')])
        return {'ui': {'images': [{'filename': '0.mp4', 'subfolder': token, 'type': 'pf_memory'}]}}


class PromptFusionMemoryQwenAudio:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'audio_batch': ('QWEN3_TTS_AUDIO_BATCH',), 'token': ('STRING',)}}
    RETURN_TYPES = ()
    FUNCTION = 'save'
    OUTPUT_NODE = True
    CATEGORY = 'Prompt Fusion'

    def save(self, audio_batch, token):
        from pathlib import Path
        import shutil
        import folder_paths
        root = Path(audio_batch['root']).resolve(strict=True)
        expected_parent = Path(folder_paths.get_temp_directory()).resolve() / 'qwen3-tts'
        if root.parent != expected_parent or not re.fullmatch('[a-f0-9]{32}', root.name):
            raise ValueError('Invalid Qwen audio temporary directory')
        files = audio_batch.get('files') or []
        if len(files) != 1:
            raise ValueError('Exactly one audio candidate is supported')
        path = Path(files[0]).resolve(strict=True)
        if not path.is_relative_to(root) or path.stat().st_size > 32 * 1024 * 1024:
            raise ValueError('Invalid or oversized audio result')
        data = path.read_bytes()
        if len(data) < 12 or data[:4] != b'RIFF' or data[8:12] != b'WAVE':
            raise ValueError('Expected WAV audio')
        _store(token, [(data, 'audio/wav')])
        shutil.rmtree(root)
        return {'ui': {'audio': [{'filename': '0', 'subfolder': token, 'type': 'pf_memory'}]}}


def _check_tmpfs():
    with open('/proc/mounts', encoding='utf-8') as mounts:
        if not any(len(parts := line.split()) >= 3 and parts[1:3] == ['/dev/shm', 'tmpfs'] for line in mounts):
            raise ValueError('SHARP output requires /dev/shm to be tmpfs')


class PromptFusionSharpRamGuard:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'image': ('IMAGE',), 'token': ('STRING',)}}
    RETURN_TYPES = ('IMAGE',)
    FUNCTION = 'check'
    CATEGORY = 'Prompt Fusion'

    def check(self, image, token):
        if not _TOKEN.fullmatch(token):
            raise ValueError('Invalid output token')
        _check_tmpfs()
        fs = os.statvfs('/dev/shm')
        if fs.f_bavail * fs.f_frsize < 256 * 1024 * 1024:
            raise ValueError('Not enough RAM-backed storage for SHARP output')
        return (image,)


class PromptFusionMemorySharp:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'ply_path': ('STRING',), 'token': ('STRING',)},
                'optional': {'max_splats': ('INT', {'default': 0, 'min': 0, 'max': 500000})}}
    RETURN_TYPES = ()
    FUNCTION = 'save'
    OUTPUT_NODE = True
    CATEGORY = 'Prompt Fusion'

    def save(self, ply_path, token, max_splats=0):
        if type(max_splats) is not int or max_splats not in (0, 150000, 300000, 500000):
            raise ValueError('Unsupported SHARP splat limit')
        if not _TOKEN.fullmatch(token) or not re.fullmatch('/dev/shm/prompt-fusion-sharp-' + token + r'_[0-9]+\.ply', ply_path):
            raise ValueError('Invalid SHARP RAM output path')
        _check_tmpfs()
        fd = os.open(ply_path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > 256 * 1024 * 1024:
                raise ValueError('Invalid or oversized SHARP PLY')
            with os.fdopen(fd, 'rb', closefd=False) as source:
                data = source.read(256 * 1024 * 1024 + 1)
            if len(data) != info.st_size or not (data.startswith(b'ply\n') or data.startswith(b'ply\r\n')):
                raise ValueError('Expected complete PLY output')
            import torch
            from comfy_extras.nodes_gaussian_splat import _parse_ply_gaussian, _gaussian_spz_bytes
            arrays = _parse_ply_gaussian(data)
            if arrays[4].shape[1] != 1:
                raise ValueError('SPZ conversion would discard higher-order colour data')
            if max_splats and len(arrays[0]) > max_splats:
                # Deterministic weighted sampling favours larger, opaque splats
                # while still giving smaller splats a chance of being selected.
                opacity = np.clip(arrays[3].reshape(-1), 0, 1)
                scales = np.maximum(arrays[1], 1e-12)
                weights = opacity * np.power(np.prod(scales, axis=1), 2.0 / 3.0)
                weights = np.nan_to_num(weights, nan=0.0, posinf=0.0, neginf=0.0)
                weights = np.maximum(weights, 1e-30)
                rng = np.random.default_rng(0)
                keys = -np.log(np.maximum(rng.random(len(weights)), 1e-15)) / weights
                selected = np.sort(np.argpartition(keys, max_splats - 1)[:max_splats])
                arrays = tuple(array[selected] for array in arrays)
            compressed = _gaussian_spz_bytes(*[torch.from_numpy(array) for array in arrays])
            _store(token, [(compressed, 'application/x-spz')])
        finally:
            os.close(fd)
            os.unlink(ply_path)
        return {'ui': {'images': [{'filename': '0', 'subfolder': token, 'type': 'pf_memory'}]}}


class PromptFusionMemoryInfiniSplat:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'image': ('IMAGE',), 'token': ('STRING',), 'focal_length_mm': ('FLOAT', {'min': 0.1, 'max': 500.0}), 'gaussian_count': ('INT', {'min': 10000, 'max': 4000000, 'step': 10000}), 'query_chunk_size': ('INT', {'min': 1000, 'max': 160000}), 'seed': ('INT', {'min': 0, 'max': 0xffffffffffffffff}), 'filter_floaters': ('BOOLEAN',)}}
    RETURN_TYPES = ()
    FUNCTION = 'save'
    OUTPUT_NODE = True
    CATEGORY = 'Prompt Fusion'

    def save(self, image, token, focal_length_mm, gaussian_count, query_chunk_size, seed, filter_floaters):
        if not _TOKEN.fullmatch(token) or type(gaussian_count) is not int or not 10000 <= gaussian_count <= 4000000 or gaussian_count % 10000 or len(image) != 1:
            raise ValueError('Invalid InfiniSplat output request')
        _check_tmpfs()
        if os.statvfs('/dev/shm').f_bavail * os.statvfs('/dev/shm').f_frsize < 512 * 1024 * 1024:
            raise ValueError('Not enough RAM-backed storage for InfiniSplat')
        import torch
        import folder_paths
        import comfy.model_management as mm
        from comfy_extras.nodes_gaussian_splat import _parse_ply_gaussian, _gaussian_spz_bytes
        pack = Path(folder_paths.base_path) / 'custom_nodes' / 'ComfyUI-InfiniSplat'
        python, worker = pack / '.venv/bin/python', pack / 'worker.py'
        checkpoint = Path(folder_paths.models_dir) / 'infinisplat/checkpoints/infinisplat_rgb.ckpt'
        if not python.is_file() or not worker.is_file() or not checkpoint.is_file():
            raise ValueError('InfiniSplat runtime or checkpoint is missing; provision it first')
        mm.unload_all_models()
        mm.soft_empty_cache()
        with tempfile.TemporaryDirectory(prefix='prompt-fusion-infini-', dir='/dev/shm') as directory:
            root = Path(directory)
            (root / 'input').mkdir()
            pixels = (image[0, ..., :3].detach().cpu().clamp(0, 1).numpy() * 255).round().astype(np.uint8)
            Image.fromarray(pixels).save(root / 'input/0000.png')
            request = {'input_dir': str(root / 'input'), 'output_dir': str(root / 'output'), 'checkpoint': str(checkpoint), 'model_dir': str(checkpoint.parent.parent), 'focal_length_mm': focal_length_mm, 'gaussian_count': gaussian_count, 'query_chunk_size': query_chunk_size, 'seed': seed, 'filter_floaters': filter_floaters, 'download_model': False, 'device': str(mm.get_torch_device()), 'camera_estimation': 'manual'}
            (root / 'request.json').write_text(json.dumps(request))
            env = os.environ.copy()
            env.pop('PYTHONPATH', None)
            env.pop('PYTHONHOME', None)
            env['HF_HUB_DISABLE_TELEMETRY'] = '1'
            with (root / 'worker.log').open('wb') as log:
                process = subprocess.Popen([str(python), str(worker), str(root / 'request.json')], cwd=str(pack / 'upstream'), env=env, stdout=log, stderr=subprocess.STDOUT)
                try:
                    while process.poll() is None:
                        mm.throw_exception_if_processing_interrupted()
                        time.sleep(0.25)
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.wait()
            if process.returncode:
                raise ValueError('InfiniSplat failed: ' + (root / 'worker.log').read_text(errors='replace')[-4000:])
            result = root / 'output/0000/0000.ply'
            if not result.is_file() or result.stat().st_size > 256 * 1024 * 1024:
                raise ValueError('InfiniSplat returned a missing or oversized PLY')
            arrays = _parse_ply_gaussian(result.read_bytes())
            if arrays[4].shape[1] != 1:
                raise ValueError('SPZ conversion would discard higher-order colour data')
            compressed = _gaussian_spz_bytes(*[torch.from_numpy(array) for array in arrays])
            _store(token, [(compressed, 'application/x-spz')])
        return {'ui': {'images': [{'filename': '0', 'subfolder': token, 'type': 'pf_memory'}]}}


NODE_CLASS_MAPPINGS = {'PromptFusionMemoryImage': PromptFusionMemoryImage, 'PromptFusionMemoryVideo': PromptFusionMemoryVideo, 'PromptFusionMemoryQwenAudio': PromptFusionMemoryQwenAudio, 'PromptFusionSharpRamGuard': PromptFusionSharpRamGuard, 'PromptFusionMemorySharp': PromptFusionMemorySharp, 'PromptFusionMemoryInfiniSplat': PromptFusionMemoryInfiniSplat}
