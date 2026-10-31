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

    def test_zimage_power_node_loaders_map_distinct_gguf_directories(self):
        self.write('z.json', {
            '1': {'class_type': 'LoadZImageModel //ZImagePowerNodes', 'inputs': {'checkpoint': 'model.gguf'}},
            '2': {'class_type': 'LoadQwen34bModel //ZImagePowerNodes', 'inputs': {'checkpoint': 'text.gguf'}},
        })
        workflow = p.discover(self.root)[0]
        self.assertEqual(workflow['assets'], {'models/diffusion_models/model.gguf', 'models/text_encoders/text.gguf'})
        self.assertEqual(workflow['issues'], [])

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
        library = p.ROOT / 'workflows'
        expected = {path.relative_to(library).as_posix() for path in library.rglob('*.json')}
        listed = {line.rsplit('[', 1)[1].removesuffix(']') for line in result.stdout.splitlines() if line}
        self.assertEqual(listed, expected)
        self.assertTrue(listed)

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
        with patch.object(p, 'ROOT', self.root), patch.object(p, 'bundled_memory_node'), patch.object(p, 'verify_nodes') as live, \
                patch.object(p, 'running_comfy', return_value={'pid': 123}) as running, \
                patch.object(p, 'restart_comfy') as restart, \
                patch.object(p.shutil, 'which', return_value='/usr/bin/curl'), \
                patch.object(p.subprocess, 'run', side_effect=curl) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(p.main(['--install', *args]), 0)
            self.assertEqual(p.main(['--install', *args]), 0)
            self.assertEqual(p.main(['--install', '--no-restart', *args]), 0)
            self.assertEqual(p.main(['--verify', *args]), 0)
        self.assertEqual(run.call_count, 1)  # two workflows, two runs, one shared download
        self.assertEqual(live.call_count, 5)  # three preflights, opt-out and standalone verification
        self.assertEqual(running.call_count, 2)
        self.assertEqual(restart.call_count, 2)  # install restarts even when files are already present

    def test_process_capture_preserves_launch_environment_and_rejects_ambiguity(self):
        proc = self.root / 'proc'
        proc.mkdir()
        comfy = self.root / 'ComfyUI'
        comfy.mkdir()
        def process(pid, script):
            entry = proc / str(pid)
            entry.mkdir()
            (entry / 'cwd').symlink_to(comfy, target_is_directory=True)
            (entry / 'cmdline').write_bytes(
                b'/venv/bin/python\0' + script + b'\0--listen\0' + b'127.0.0.1\0--port\0' + b'8188\0')
            (entry / 'environ').write_bytes(b'PATH=/venv/bin:/usr/bin\0TOKEN=value=with=equals\0')
        process(123, b'main.py')
        process(124, b'other.py')
        captured = p.running_comfy(comfy, proc)
        self.assertEqual(captured['pid'], 123)
        self.assertEqual(captured['command'], ['/venv/bin/python', 'main.py', '--listen', '127.0.0.1', '--port', '8188'])
        self.assertEqual(captured['env']['TOKEN'], 'value=with=equals')
        process(125, str(comfy / 'main.py').encode())
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            p.running_comfy(comfy, proc)

    def test_restart_waits_for_shutdown_then_readiness_and_detaches(self):
        process = dict(pid=123, command=['/venv/bin/python', 'main.py', '--port', '8188'],
                       cwd=self.root, env={'PATH': '/venv/bin'})
        with patch.object(p, 'running_comfy', return_value=process), \
                patch.object(p.os, 'kill') as kill, \
                patch.object(p, 'process_alive', side_effect=[True, False]), \
                patch.object(p.time, 'sleep'), \
                patch.object(p.subprocess, 'Popen') as popen, \
                patch.object(p, 'verify_nodes', side_effect=[ValueError('starting'), None]) as live:
            popen.return_value.poll.return_value = None
            p.restart_comfy(self.root, process, [], 'http://127.0.0.1:8188')
        kill.assert_called_once_with(123, p.signal.SIGTERM)
        self.assertEqual(live.call_count, 2)
        self.assertEqual(popen.call_args.args[0], process['command'])
        self.assertEqual(popen.call_args.kwargs['env'], process['env'])
        self.assertEqual(popen.call_args.kwargs['cwd'], self.root)
        self.assertTrue(popen.call_args.kwargs['start_new_session'])
        self.assertTrue((self.root / '.provision-comfyui.log').exists())

    def test_restart_does_not_launch_if_shutdown_times_out(self):
        process = dict(pid=123)
        with patch.object(p, 'running_comfy', return_value=process), \
                patch.object(p.os, 'kill'), patch.object(p, 'process_alive', return_value=True), \
                patch.object(p.time, 'monotonic', side_effect=[0, 31]), \
                patch.object(p.subprocess, 'Popen') as popen:
            with self.assertRaisesRegex(ValueError, 'did not stop'):
                p.restart_comfy(self.root, process, [], 'http://127.0.0.1:8188')
        popen.assert_not_called()

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

    def test_aria2_uses_separate_resumable_partial_and_validates(self):
        target = self.root / 'model.safetensors'
        part = target.with_name(target.name + '.aria2.part')
        part.write_bytes(b'partial')
        def aria(command, **kwargs):
            self.assertIn('--continue=true', command)
            self.assertIn('--split=4', command)
            self.assertIn('--out=' + part.name, command)
            part.write_bytes(self.body)
            return subprocess.CompletedProcess(command, 0)
        with patch.object(p.subprocess, 'run', side_effect=aria):
            p.download(target, self.model, 'aria2', 4)
        self.assertEqual(target.read_bytes(), self.body)
        self.assertFalse(part.exists())

    def test_install_runs_multiple_downloads_concurrently(self):
        import threading
        workflows = self.root / 'workflows'
        workflows.mkdir()
        (workflows / 'two.json').write_text(json.dumps({
            '1': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'test.safetensors'}},
            '2': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'other.safetensors'}},
        }))
        self.manifest['models']['models/vae/other.safetensors'] = self.model
        (self.root / 'dependencies.json').write_text(json.dumps(self.manifest))
        comfy = self.root / 'ComfyUI'
        (comfy / 'models').mkdir(parents=True)
        (comfy / 'main.py').touch()
        barrier = threading.Barrier(2, timeout=3)
        def transfer(target, model, downloader, connections):
            barrier.wait()
        with patch.object(p, 'ROOT', self.root), patch.object(p, 'bundled_memory_node'), patch.object(p, 'verify_nodes'), \
                patch.object(p.shutil, 'which', return_value='/usr/bin/curl'), \
                patch.object(p, 'download', side_effect=transfer) as run:
            self.assertEqual(p.main(['--install', '--all', '--no-restart', '--comfy-dir', str(comfy),
                                     '--download-jobs', '2']), 0)
        self.assertEqual(run.call_count, 2)

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

    def test_bundled_memory_node_installs_verifies_and_preserves_user_edits(self):
        p.bundled_memory_node(self.root)
        node = self.root / 'custom_nodes/prompt_fusion_memory/__init__.py'
        self.assertEqual(node.read_bytes(), (p.ROOT / 'bundled_nodes/prompt_fusion_memory/__init__.py').read_bytes())
        p.bundled_memory_node(self.root, verify=True)
        node.write_text('user modification')
        with self.assertRaisesRegex(ValueError, 'modified'):
            p.bundled_memory_node(self.root)
        with self.assertRaisesRegex(ValueError, 'differs'):
            p.bundled_memory_node(self.root, verify=True)
        self.assertEqual(node.read_text(), 'user modification')

    def test_pinned_node_files_install_verify_and_reject_changed_files(self):
        package = {'commit': 'a' * 40, 'files': {
            'nodes.py': {'url': 'https://example.invalid/' + 'a' * 40 + '/nodes.py',
                         'sha256': hashlib.sha256(self.body).hexdigest()}}}
        def curl(command, **kwargs):
            Path(command[command.index('--output') + 1]).write_bytes(self.body)
            return subprocess.CompletedProcess(command, 0)
        with patch.object(p.subprocess, 'run', side_effect=curl) as run:
            p.custom_node(self.root, 'test-node', package)
            p.custom_node(self.root, 'test-node', package)
            p.custom_node(self.root, 'test-node', package, verify=True)
            self.assertEqual(run.call_count, 1)
            (self.root / 'custom_nodes/test-node/nodes.py').write_text('changed')
            with self.assertRaises(ValueError):
                p.custom_node(self.root, 'test-node', package, verify=True)
            with self.assertRaises(ValueError):
                p.custom_node(self.root, 'test-node', package)

    def test_invalid_pinned_node_paths_fail_planning(self):
        self.manifest['custom_nodes']['bad'] = {'repo': 'https://example.invalid/repo',
            'commit': 'a' * 40, 'nodes': ['Test'], 'files': {'../escape.py': {
                'url': 'https://example.invalid/' + 'a' * 40 + '/escape.py', 'sha256': 'a' * 64}}}
        workflow = dict(slug='test', key='test.json', issues=[], nodes={'Test'}, assets=set())
        self.assertTrue(any('invalid pinned file' in issue for issue in p.plan([workflow], self.manifest)[2]))

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


    def test_ltx_loader_assets_and_reviewed_upscaler_links(self):
        graph = {
            'checkpoint': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'ltx.safetensors'}},
            'audio': {'class_type': 'LTXVAudioVAELoader', 'inputs': {'ckpt_name': 'ltx.safetensors'}},
            'encoder': {'class_type': 'LTXAVTextEncoderLoader', 'inputs': {
                'ckpt_name': 'ltx.safetensors', 'text_encoder': 'gemma.safetensors'}},
            'upscale-loader': {'class_type': 'LatentUpscaleModelLoader', 'inputs': {'model_name': 'upscaler.safetensors'}},
            'upscale': {'class_type': 'LTXVLatentUpsampler', 'inputs': {'upscale_model': ['upscale-loader', 0]}},
            'lora': {'class_type': 'LoraLoader', 'inputs': {'lora_name': 'enhancer.safetensors'}},
        }
        path = self.write('ltx.json', {'name': 'LTX', 'workflow': graph})
        workflow = p.discover(self.root)[0]
        self.assertEqual(workflow['issues'], [])
        self.assertEqual(workflow['assets'], {
            'models/checkpoints/ltx.safetensors', 'models/text_encoders/gemma.safetensors',
            'models/latent_upscale_models/upscaler.safetensors', 'models/loras/enhancer.safetensors'})
        for link in [['missing', 0], ['encoder', 0], ['upscale-loader', 1],
                     ['upscale-loader', False], 'upscaler.safetensors']:
            graph['upscale']['inputs']['upscale_model'] = link
            path.write_text(json.dumps(graph))
            self.assertTrue(any('reviewed LatentUpscaleModelLoader' in issue for issue in p.discover(self.root)[0]['issues']))
        graph['upscale']['inputs']['upscale_model'] = ['upscale-loader', 0]
        graph['encoder']['inputs']['text_encoder'] = 'API_ENCODER'
        path.write_text(json.dumps(graph))
        self.assertTrue(any('dynamic model selection' in issue for issue in p.discover(self.root)[0]['issues']))
        graph['encoder']['inputs']['text_encoder'] = 'gemma.safetensors'
        graph['upscale-loader']['class_type'] = 'UnreviewedLoader'
        path.write_text(json.dumps(graph))
        self.assertTrue(any('unclassified asset' in issue for issue in p.discover(self.root)[0]['issues']))

    def test_ltx_loader_choices_checked_live_and_skipped_before_download(self):
        graph = {
            'encoder': {'class_type': 'LTXAVTextEncoderLoader', 'inputs': {'text_encoder': 'gemma.safetensors'}},
            'upscale-loader': {'class_type': 'LatentUpscaleModelLoader', 'inputs': {'model_name': 'up.safetensors'}},
        }
        self.write('ltx.json', graph)
        workflows = p.discover(self.root)
        schema = {
            'LTXAVTextEncoderLoader': {'input': {'required': {'text_encoder': [['gemma.safetensors'], {}]}}},
            'LatentUpscaleModelLoader': {'input': {'required': {'model_name': ['COMBO', {'options': ['up.safetensors']}]}}},
        }
        def server():
            return patch.object(p, 'urlopen', return_value=contextlib.closing(io.BytesIO(json.dumps(schema).encode())))
        with server():
            p.verify_nodes(workflows, 'http://localhost:8188')
        for kind, field in [('LTXAVTextEncoderLoader', 'text_encoder'), ('LatentUpscaleModelLoader', 'model_name')]:
            original = schema[kind]['input']['required'][field]
            schema[kind]['input']['required'][field] = [[], {}]
            with server(), self.assertRaisesRegex(ValueError, 'does not offer'):
                p.verify_nodes(workflows, 'http://localhost:8188')
            with server():
                p.verify_nodes(workflows, 'http://localhost:8188', check_models=False)
            schema[kind]['input']['required'][field] = original

    def test_explicit_preview_addon_must_register_even_without_graph_reference(self):
        workflows = self.root / 'workflows'
        workflows.mkdir()
        (workflows / 'image.json').write_text(json.dumps({
            '1': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'test.safetensors'}}}))
        self.manifest['custom_nodes'] = {'preview': {
            'repo': 'https://example.invalid/preview.git', 'commit': 'a' * 40, 'nodes': ['PanoramaPreview']}}
        self.manifest['workflows'] = {'image.json': {'custom_nodes': ['preview']}}
        (self.root / 'dependencies.json').write_text(json.dumps(self.manifest))
        comfy = self.root / 'ComfyUI'
        model = comfy / 'models/vae/test.safetensors'
        model.parent.mkdir(parents=True)
        model.write_bytes(self.body)
        (comfy / 'main.py').touch()
        schema = {'VAELoader': {'input': {'required': {'vae_name': [['test.safetensors'], {}]}}}}
        schema.update({name: {'input': {'required': {}}} for name in ('PromptFusionMemoryImage', 'PromptFusionMemoryVideo')})
        def server():
            return patch.object(p, 'urlopen', return_value=contextlib.closing(io.BytesIO(json.dumps(schema).encode())))
        args = ['--verify', '--all', '--comfy-dir', str(comfy)]
        with patch.object(p, 'ROOT', self.root), patch.object(p, 'bundled_memory_node'), patch.object(p, 'custom_node') as checkout, \
                patch.object(p.shutil, 'which', return_value='/usr/bin/git'), contextlib.redirect_stdout(io.StringIO()):
            with server(), self.assertRaisesRegex(ValueError, 'PanoramaPreview'):
                p.main(args)
            schema['PanoramaPreview'] = {'input': {'required': {}}}
            with server():
                self.assertEqual(p.main(args), 0)
            self.assertTrue(all(call.kwargs['verify'] for call in checkout.call_args_list))


if __name__ == '__main__':
    unittest.main()
