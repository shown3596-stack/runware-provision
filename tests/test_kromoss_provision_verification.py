import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import provision

class KromossProvisionVerification(unittest.TestCase):
    def test_saved_workflow_validates_real_model_names(self):
        directory = Path(__file__).resolve().parents[1] / 'workflows'
        workflow = next(w for w in provision.discover(directory) if w['key'] == 'kromoss-bf16-11000-dmd2-8-step.json')
        graph = json.loads(workflow['path'].read_text())['workflow']
        self.assertEqual(graph['32']['inputs']['unet_name'], 'kromoss_bf16_11000.safetensors')
        self.assertEqual(graph['34']['inputs']['lora_name'], '8-steps-dmd2-lora.safetensors')
        info = {node: {'input': {'required': {}}} for node in workflow['nodes']}
        for node in graph.values():
            fields = info[node['class_type']]['input']['required']
            for key, value in node['inputs'].items():
                if isinstance(value, str) and (provision.model_directory(node['class_type'], key) or (node['class_type'] == 'CLIPLoader' and key == 'type')):
                    fields[key] = [[value]]
        with patch.object(provision, 'urlopen', return_value=io.BytesIO(json.dumps(info).encode())):
            provision.verify_nodes([workflow], 'http://localhost:8188')
