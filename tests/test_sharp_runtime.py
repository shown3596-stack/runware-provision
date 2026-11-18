import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

p = Path(__file__).resolve().parents[1] / 'scripts/install_sharp_runtime.py'
spec = importlib.util.spec_from_file_location('sharp_runtime', p)
sharp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sharp)

class SharpPreflightTests(unittest.TestCase):
    def test_refuses_unrelated_workspace_and_allows_owned_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'comfy'; nodes = root / 'custom_nodes'; nodes.mkdir(parents=True)
            workspace = Path(temp) / 'workspace'; workspace.mkdir(); (workspace / 'pixi.toml').write_text('test')
            with patch.dict(os.environ, {'COMFY_ENV_ROOT': str(workspace)}):
                with self.assertRaisesRegex(ValueError, 'refusing to overwrite'):
                    sharp.preflight(root)
                (nodes / '.provision-sharp-workspace.json').write_text(json.dumps({'root': str(root), 'workspace': str(workspace)}))
                self.assertEqual(sharp.preflight(root), workspace)
                other = nodes / 'other'; other.mkdir(); (other / 'comfy-env.toml').write_text('')
                with self.assertRaisesRegex(ValueError, 'other packs'):
                    sharp.preflight(root)
