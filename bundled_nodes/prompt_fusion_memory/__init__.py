"""Prompt Fusion RAM-only output nodes. Direct ComfyUI workflows are unaffected."""
import io
import re
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
    return web.json_response({'version': 1, 'images': True, 'video_mp4': True, 'capacity_bytes': _LIMIT})


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


NODE_CLASS_MAPPINGS = {'PromptFusionMemoryImage': PromptFusionMemoryImage, 'PromptFusionMemoryVideo': PromptFusionMemoryVideo}
