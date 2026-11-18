"""Prompt Fusion RAM-only output nodes. Direct ComfyUI workflows are unaffected."""
import io
import os
import re
import stat
import threading
import time
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
    return web.json_response({'version': 1, 'images': True, 'video_mp4': True, 'qwen_audio': True, 'sharp_spz': sharp_spz, 'capacity_bytes': _LIMIT})


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
        return {'required': {'ply_path': ('STRING',), 'token': ('STRING',)}}
    RETURN_TYPES = ()
    FUNCTION = 'save'
    OUTPUT_NODE = True
    CATEGORY = 'Prompt Fusion'

    def save(self, ply_path, token):
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
            compressed = _gaussian_spz_bytes(*[torch.from_numpy(array) for array in arrays])
            _store(token, [(compressed, 'application/x-spz')])
        finally:
            os.close(fd)
            os.unlink(ply_path)
        return {'ui': {'images': [{'filename': '0', 'subfolder': token, 'type': 'pf_memory'}]}}


NODE_CLASS_MAPPINGS = {'PromptFusionMemoryImage': PromptFusionMemoryImage, 'PromptFusionMemoryVideo': PromptFusionMemoryVideo, 'PromptFusionMemoryQwenAudio': PromptFusionMemoryQwenAudio, 'PromptFusionSharpRamGuard': PromptFusionSharpRamGuard, 'PromptFusionMemorySharp': PromptFusionMemorySharp}
