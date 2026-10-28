"""CPU-only checks for the packaged node, without ComfyUI or GPU dependencies."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

class Routes:
    def get(self, path): return lambda f: f
    def delete(self, path): return lambda f: f

class NodeTests(unittest.TestCase):
    def setUp(self):
        server = types.ModuleType('server'); server.PromptServer = types.SimpleNamespace(instance=types.SimpleNamespace(routes=Routes()))
        aio = types.ModuleType('aiohttp'); aio.web = types.SimpleNamespace()
        numpy = types.ModuleType('numpy')
        pil = types.ModuleType('PIL'); pil.Image = types.SimpleNamespace()
        modules = {'server': server, 'aiohttp': aio, 'numpy': numpy, 'PIL': pil}
        with patch.dict(sys.modules, modules):
            spec = importlib.util.spec_from_file_location('test_pf_memory_node', Path(__file__).resolve().parents[1] / 'bundled_nodes/prompt_fusion_memory/__init__.py')
            self.node = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.node)

    def test_store_is_bounded_and_refuses_reusing_tokens(self):
        node = self.node; node._LIMIT = 8
        node._store('a' * 64, [(b'1234', 'image/png')])
        with self.assertRaisesRegex(ValueError, 'already exists'): node._store('a' * 64, [(b'1', 'image/png')])
        with self.assertRaisesRegex(ValueError, 'capacity'): node._store('b' * 64, [(b'12345', 'image/png')])
        self.assertEqual(node._results['a' * 64][1][0][0], b'1234')
        node._results['a' * 64] = (0, node._results['a' * 64][1])
        node._store('b' * 64, [(b'12', 'image/png')])
        self.assertNotIn('a' * 64, node._results)

    def test_image_batch_encodes_in_memory_and_preserves_order(self):
        class Array:
            def __rmul__(self, value): return self
            def astype(self, dtype): return self
        class Tensor:
            def cpu(self): return self
            def numpy(self): return Array()
        self.node.np.clip = lambda value, low, high: value
        self.node.np.uint8 = 'uint8'
        class Image:
            def save(self, buffer, format): buffer.write(b'png-result')
        self.node.Image.fromarray = lambda array: Image()
        result = self.node.PromptFusionMemoryImage().save([Tensor(), Tensor()], 'e' * 64)
        self.assertEqual([x['filename'] for x in result['ui']['images']], ['0', '1'])
        self.assertEqual(self.node._results['e' * 64][1], [(b'png-result', 'image/png')] * 2)

    def test_video_encodes_to_bytes_buffer_and_preserves_input_object(self):
        types_module = types.ModuleType('comfy_api.latest')
        types_module.Types = types.SimpleNamespace(VideoContainer=lambda x:x, VideoCodec=lambda x:x)
        class Video:
            def save_to(self, output, format, codec):
                self.settings = (format, codec); output.write(bytes([0, 0, 0, 24]) + b'ftypmp42')
        video = Video()
        with patch.dict(sys.modules, {'comfy_api': types.ModuleType('comfy_api'), 'comfy_api.latest': types_module}):
            result = self.node.PromptFusionMemoryVideo().save(video, 'c' * 64)
        self.assertEqual(video.settings, ('mp4', 'h264'))
        self.assertEqual(result['ui']['images'][0]['type'], 'pf_memory')
        self.assertEqual(self.node._results['c' * 64][1][0][1], 'video/mp4')
