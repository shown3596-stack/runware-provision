import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import provision

class ModelDefaultsTest(unittest.TestCase):
    def test_declared_defaults_resolve_as_dependencies(self):
        document = {'name':'example', 'workflow': {'1':{'class_type':'UNETLoader','inputs':{'unet_name':'API_DIFFUSION_MODEL'}}, '2':{'class_type':'LoraLoaderModelOnly','inputs':{'lora_name':'API_LORA'}}}, 'parameter_defaults':{'API_DIFFUSION_MODEL':'model.safetensors','API_LORA':'style.safetensors'}}
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,'example.json').write_text(json.dumps(document))
            item = provision.discover(Path(tmp))[0]
            self.assertEqual(item['assets'], {'models/diffusion_models/model.safetensors','models/loras/style.safetensors'})
            self.assertEqual(item['issues'], [])
            del document['parameter_defaults']['API_LORA']
            Path(tmp,'example.json').write_text(json.dumps(document))
            self.assertTrue(provision.discover(Path(tmp))[0]['issues'])
