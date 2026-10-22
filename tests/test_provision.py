"""CPU-only tests with tiny local fixtures; no model downloads or GPU jobs."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('provision', Path(__file__).resolve().parents[1] / 'provision.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class ProvisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.body = b'tiny simulated model payload'
        self.model = dict(url='https://example.invalid/model', size_bytes=len(self.body),
                          sha256=hashlib.sha256(self.body).hexdigest())
        self.manifest = dict(models={'models/vae/test.safetensors': self.model},
                             custom_nodes={}, core_nodes={'VAELoader': 'core'}, workflows={})

    def write(self, name, graph):
        path = self.root / name
        path.write_text(json.dumps(graph))
        return path

    def test_discover_wrapped_api_raw_api_ui_and_unknown(self):
        graph = {'1': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'test.safetensors'}}}
        self.write('one.json', dict(name='My workflow', workflow=graph))
        self.write('two.json', graph)
        self.write('three.json', {'nodes': [{'type': 'VAELoader', 'widgets_values': ['test.safetensors']}]})
        self.write('four.json', {'not': 'a workflow'})
        workflows = p.discover(self.root)
        self.assertEqual(sorted(w['format'] for w in workflows), ['API', 'API', 'UI', 'unknown'])
        chosen = p.select(workflows, 'my-workflow')
        assets, packages, issues = p.plan(chosen, self.manifest)
        self.assertEqual(assets, ['models/vae/test.safetensors'])
        self.assertEqual((packages, issues), ([], []))
        self.assertTrue(p.plan(p.select(workflows, 'three'), self.manifest)[2])
        with self.assertRaises(ValueError):
            p.select(workflows, 'flux-klein')

    def test_unknown_nodes_dynamic_and_unclassified_assets_block(self):
        self.write('unknown.json', {'1': {'class_type': 'UnknownLoader', 'inputs': {
            'vae_name': ['2', 0], 'other_file': 'mystery.gguf'}}})
        issues = p.plan(p.discover(self.root), self.manifest)[2]
        self.assertEqual(len(issues), 3)
        self.model['url'] = None
        w = dict(slug='w', key='w.json', issues=[], nodes=set(), assets={'models/vae/test.safetensors'})
        self.assertIn('unresolved', p.plan([w], self.manifest)[2][0])

    def test_bundled_workflows_have_resolved_pinned_dependencies(self):
        workflows = p.discover(p.ROOT / 'workflows')
        manifest = json.loads((p.ROOT / 'dependencies.json').read_text())
        assets, packages, issues = p.plan(workflows, manifest)
        self.assertTrue(workflows)
        self.assertTrue(assets)
        self.assertEqual(issues, [])
        for model in manifest['models'].values():
            self.assertRegex(model['sha256'], r'^[0-9a-f]{64}$')
            self.assertIn('/resolve/' + model['revision'] + '/', model['url'])

    def test_external_workflow_directory_and_missing_directory(self):
        self.write('external.json', {
            'name': 'External library',
            'workflow': {'1': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'test.safetensors'}}},
        })
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(p.main(['--list', '--workflows-dir', str(self.root)]), 0)
        self.assertIn('external-library', output.getvalue())
        self.assertNotIn('qwen-2512', output.getvalue())
        with self.assertRaisesRegex(ValueError, 'directory does not exist'):
            p.main(['--list', '--workflows-dir', str(self.root / 'missing')])

    def test_bundled_workflows_work_from_another_directory(self):
        result = subprocess.run(
            [str(Path(p.sys.executable)), str(p.ROOT / 'provision.py'), '--list'],
            cwd=self.root, capture_output=True, text=True, check=True,
        )
        self.assertIn('qwen-2512-turbo', result.stdout)

    def test_complete_cli_install_twice_then_verify(self):
        workflows = self.root / 'workflows'
        workflows.mkdir()
        graph = {'1': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'test.safetensors'}}}
        for name in ['first', 'second']:
            (workflows / (name + '.json')).write_text(json.dumps(graph))
        (self.root / 'dependencies.json').write_text(json.dumps(self.manifest))
        comfy = self.root / 'ComfyUI'
        (comfy / 'models').mkdir(parents=True)
        (comfy / 'main.py').touch()
        def curl(command, **kwargs):
            Path(command[command.index('--output') + 1]).write_bytes(self.body)
            return subprocess.CompletedProcess(command, 0)
        args = ['--all', '--comfy-dir', str(comfy)]
        with patch.object(p, 'ROOT', self.root), patch.object(p, 'verify_nodes') as live, \
                patch.object(p.shutil, 'which', return_value='/usr/bin/curl'), \
                patch.object(p.subprocess, 'run', side_effect=curl) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(p.main(['--install', *args]), 0)
            self.assertEqual(p.main(['--install', *args]), 0)
            self.assertEqual(p.main(['--verify', *args]), 0)
        self.assertEqual(run.call_count, 1)  # two workflows, two runs, one shared download
        self.assertEqual(live.call_count, 5)  # installation preflights and final checks

    def test_atomic_download_resume_and_second_run_skips_network(self):
        target = self.root / 'models' / 'test.safetensors'
        target.parent.mkdir()
        part = target.with_name(target.name + '.part')
        part.write_bytes(self.body[:5])
        def curl(command, **kwargs):
            self.assertFalse(target.exists())
            self.assertEqual(part.read_bytes(), self.body[:5])
            self.assertIn('--continue-at', command)
            part.write_bytes(self.body)
            return subprocess.CompletedProcess(command, 0)
        with patch.object(p.subprocess, 'run', side_effect=curl) as run:
            p.download(target, self.model)
            p.download(target, self.model)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(target.read_bytes(), self.body)
        self.assertFalse(part.exists())

    def test_failure_keeps_partial_checksum_failure_never_publishes(self):
        target = self.root / 'test.safetensors'
        part = target.with_name(target.name + '.part')
        part.write_bytes(b'partial')
        with patch.object(p.subprocess, 'run', return_value=subprocess.CompletedProcess([], 28)):
            with self.assertRaises(ValueError):
                p.download(target, self.model)
        self.assertTrue(part.exists())
        self.assertFalse(target.exists())
        with patch.object(p.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)):
            with self.assertRaises(ValueError):
                p.download(target, self.model)
        self.assertFalse(part.exists())
        self.assertFalse(target.exists())

    def test_range_unsupported_restarts_and_corrupt_final_is_preserved(self):
        target = self.root / 'test.safetensors'
        part = target.with_name(target.name + '.part')
        part.write_bytes(b'old')
        def curl(command, **kwargs):
            if part.exists():
                return subprocess.CompletedProcess(command, 33)
            part.write_bytes(self.body)
            return subprocess.CompletedProcess(command, 0)
        with patch.object(p.subprocess, 'run', side_effect=curl):
            p.download(target, self.model)
        target.write_bytes(b'incorrect existing file')
        with patch.object(p.subprocess, 'run') as run, self.assertRaises(ValueError):
            p.download(target, self.model)
        run.assert_not_called()
        self.assertEqual(target.read_bytes(), b'incorrect existing file')

    def test_dry_run_no_files_no_network_and_path_containment(self):
        before = sorted(self.root.rglob('*'))
        with patch.object(p, 'locate') as locate, patch.object(p, 'urlopen') as http, \
                patch.object(p.subprocess, 'run') as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(p.main(['--install', '--all', '--dry-run']), 0)
        locate.assert_not_called()
        http.assert_not_called()
        run.assert_not_called()
        self.assertEqual(sorted(self.root.rglob('*')), before)
        for path in ['../escape', '/tmp/escape']:
            with self.assertRaises(ValueError):
                p.within(self.root, path)
        (self.root / 'link').symlink_to('/tmp')
        with self.assertRaises(ValueError):
            p.within(self.root, 'link/escape')

    def test_custom_node_pinned_requirements_install_only_once(self):
        target = self.root / 'custom_nodes' / 'example'
        target.mkdir(parents=True)
        (target / 'requirements.txt').write_text('example==1.0\n')
        commit = 'a' * 40
        package = dict(commit=commit, repo='https://example.invalid/example.git', nodes=['Example'])
        def git(path, *args):
            return commit if args[0] == 'rev-parse' else (package['repo'] if args[0] == 'remote' else '')
        with patch.object(p, 'git', side_effect=git), patch.object(p.subprocess, 'run') as run:
            p.custom_node(self.root, 'example', package)
            p.custom_node(self.root, 'example', package)
            p.custom_node(self.root, 'example', package, verify=True)
        self.assertEqual(run.call_count, 1)
        (target / 'requirements.txt').write_text('example==2.0\n')
        with patch.object(p, 'git', side_effect=git), self.assertRaises(ValueError):
            p.custom_node(self.root, 'example', package, verify=True)

    def test_live_node_and_loader_choice_checks(self):
        path = self.write('api.json', {'1': {'class_type': 'CLIPLoader', 'inputs': {'type': 'krea2'}}})
        workflows = [dict(path=path, slug='api', format='API', nodes={'CLIPLoader'})]
        def server(data):
            return patch.object(p, 'urlopen', return_value=contextlib.closing(io.BytesIO(json.dumps(data).encode())))
        with server({}), self.assertRaisesRegex(ValueError, 'not registered'):
            p.verify_nodes(workflows, 'http://localhost:8188')
        schema = {'CLIPLoader': {'input': {'required': {'type': [['sdxl'], {}]}}}}
        with server(schema), self.assertRaisesRegex(ValueError, 'does not offer'):
            p.verify_nodes(workflows, 'http://localhost:8188')
        schema['CLIPLoader']['input']['required']['type'] = ['COMBO', {'options': ['krea2']}]
        with server(schema):
            p.verify_nodes(workflows, 'http://localhost:8188')
        with patch.object(p, 'urlopen', side_effect=OSError('offline')), self.assertRaisesRegex(ValueError, 'Cannot verify'):
            p.verify_nodes(workflows, 'http://localhost:8188')


if __name__ == '__main__':
    unittest.main()
