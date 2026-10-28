#!/usr/bin/env python3
"""Inspect local ComfyUI exports; provision an existing Pod. Python 3.10+, stdlib only."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
MODEL_INPUTS = {
    'unet_name': 'diffusion_models', 'ckpt_name': 'checkpoints',
    'clip_name': 'text_encoders', 'clip_name1': 'text_encoders',
    'clip_name2': 'text_encoders', 'clip_name3': 'text_encoders',
    'vae_name': 'vae', 'lora_name': 'loras', 'control_net_name': 'controlnet',
    'clip_vision': 'clip_vision', 'style_model_name': 'style_models',
    'upscale_model': 'upscale_models',
}
# These names are node-specific: model_name is not a general loader filename.
NODE_MODEL_INPUTS = {
    ('LatentUpscaleModelLoader', 'model_name'): 'latent_upscale_models',
    ('LTXAVTextEncoderLoader', 'text_encoder'): 'text_encoders',
}
MODEL_OBJECT_INPUTS = {
    ('LTXVLatentUpsampler', 'upscale_model'): ('LatentUpscaleModelLoader', 0),
}
ASSET = re.compile(r'\.(safetensors|ckpt|pt|pth|bin|gguf|onnx)$', re.I)


def model_directory(kind, field):
    if (kind, field) in MODEL_OBJECT_INPUTS:
        return None
    return NODE_MODEL_INPUTS.get((kind, field), MODEL_INPUTS.get(field))


def slug(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def discover(directory):
    result = []
    for path in sorted(directory.rglob('*.json')):
        document = json.loads(path.read_text())
        graph = document.get('workflow', document)
        name = document.get('name', path.stem)
        issues, assets, nodes = [], set(), set()
        if isinstance(graph, dict) and isinstance(graph.get('nodes'), list):
            fmt = 'UI'
            raw_nodes = graph['nodes']
            issues.append('UI widget positions are not a reliable input schema; export API format for installation.')
        elif isinstance(graph, dict) and graph and all(
                isinstance(n, dict) and 'class_type' in n and isinstance(n.get('inputs'), dict)
                for n in graph.values()):
            fmt = 'API'
            raw_nodes = list(graph.values())
        else:
            fmt, raw_nodes = 'unknown', []
            issues.append('Unrecognized workflow format.')
        for node in raw_nodes:
            kind = node.get('class_type', node.get('type', 'UNKNOWN'))
            nodes.add(kind)
            inputs = node.get('inputs', {}) if fmt == 'API' else node.get('widgets_values_named', {})
            for key, value in inputs.items():
                object_source = MODEL_OBJECT_INPUTS.get((kind, key))
                if object_source:
                    loader, slot = object_source
                    if (fmt != 'API' or not isinstance(value, list) or len(value) != 2
                            or not isinstance(value[0], str) or type(value[1]) is not int
                            or value[1] != slot or not isinstance(graph.get(value[0]), dict)
                            or graph[value[0]].get('class_type') != loader):
                        issues.append(f'{kind}.{key}: expected a reviewed {loader} output link; got {value!r}')
                    continue
                asset_directory = model_directory(kind, key)
                if asset_directory:
                    if not isinstance(value, str) or value.startswith('API_'):
                        issues.append(f'{kind}.{key}: dynamic model selection needs review: {value!r}')
                    else:
                        assets.add(f'models/{asset_directory}/{value.replace(chr(92), "/")}')
                elif any(ASSET.search(s) for s in strings(value)):
                    issues.append(f'{kind}.{key}: unclassified asset reference: {value!r}')
                if any('embedding:' in s.lower() for s in strings(value)):
                    issues.append(f'{kind}.{key}: embedding reference needs an explicit manifest entry.')
            if fmt == 'UI':
                for value in strings(node.get('widgets_values', [])):
                    if ASSET.search(value):
                        issues.append(f'{kind}: model candidate {value!r}; directory/input unresolved.')
        result.append(dict(name=name, slug=slug(name) or path.stem, path=path,
                           key=path.relative_to(directory).as_posix(), format=fmt,
                           assets=assets, nodes=nodes, issues=issues))
    counts = Counter(w['slug'] for w in result)
    for w in result:
        if counts[w['slug']] > 1:
            w['slug'] += '-' + w['path'].stem
    return result


def select(workflows, name):
    if not name:
        return workflows
    found = [w for w in workflows if name in (w['slug'], w['name'], w['path'].stem, w['key'])]
    if len(found) != 1:
        raise ValueError(f'Workflow {name!r} is unknown or ambiguous; use --list.')
    return found


def plan(workflows, manifest):
    assets, packages, issues = set(), set(), []
    for w in workflows:
        assets.update(w['assets'])
        issues.extend(f"{w['slug']}: {s}" for s in w['issues'])
        entry = manifest.get('workflows', {}).get(w['key'], {})
        packages.update(entry.get('custom_nodes', []))
        assets.update(entry.get('extra_models', []))
        issues.extend(f"{w['slug']}: {s}" for s in entry.get('review', []))
        for node in w['nodes']:
            owners = [key for key, p in manifest['custom_nodes'].items() if node in p['nodes']]
            if owners:
                packages.update(owners)
            elif node not in manifest['core_nodes']:
                issues.append(f"{w['slug']}: node {node!r} has no verified core/custom-node mapping.")
    for asset in sorted(assets):
        model = manifest['models'].get(asset)
        if not model or not model.get('url') or model.get('review'):
            issues.append(f'{asset}: unresolved model source; review dependencies.json.')
        elif not (model.get('sha256') or model.get('size_bytes')):
            issues.append(f'{asset}: add size_bytes or sha256 before installing.')
    for name in packages:
        p = manifest['custom_nodes'].get(name, {})
        if not p.get('repo') or not re.fullmatch(r'[a-fA-F0-9]{40}', p.get('commit', '')) or p.get('review'):
            issues.append(f'{name}: custom-node repository/commit unresolved.')
        if 'files' in p:
            files = p['files']
            if not isinstance(files, dict) or not files:
                issues.append(f'{name}: custom-node file list unresolved.')
            else:
                for filename, item in files.items():
                    if (not isinstance(filename, str) or Path(filename).is_absolute() or '..' in Path(filename).parts
                            or not isinstance(item, dict) or not item.get('url')
                            or not re.fullmatch(r'[a-f0-9]{64}', item.get('sha256', ''))
                            or p.get('commit', '') not in item['url']):
                        issues.append(f'{name}: invalid pinned file {filename!r}.')
    return sorted(assets), sorted(packages), issues


def inspect(workflows, manifest):
    for w in workflows:
        assets, packages, issues = plan([w], manifest)
        print(f"\n{w['slug']} — {w['name']} ({w['format']}, {w['key']})")
        print('  Nodes: ' + ', '.join(sorted(w['nodes'])))
        print('  Custom packages: ' + (', '.join(packages) or 'none identified'))
        for asset in assets:
            m = manifest['models'].get(asset, {})
            print(f"  {asset} (~{m.get('approx_gb', '?')} GB)")
            print(f"    {m.get('url') or 'UNRESOLVED URL'}")
        for issue in issues:
            print('  REVIEW: ' + issue)
        if not issues:
            print('  Sources resolved; live ComfyUI compatibility requires --verify and a smoke generation.')
    shared = Counter(a for w in workflows for a in w['assets'])
    print('\nShared assets:')
    for asset, count in sorted(shared.items()):
        if count > 1:
            print(f'  {count} workflows: {asset}')


def locate(explicit):
    if explicit:
        candidates = [Path(explicit).expanduser()]
    else:
        candidates = [Path(p) for p in ('/workspace/ComfyUI', '/workspace/runpod-slim/ComfyUI',
                                       '/workspace/ComfyUI/ComfyUI', '/opt/ComfyUI', '/ComfyUI')]
        candidates += [Path.home() / 'ComfyUI', Path.cwd() / 'ComfyUI', Path.cwd()]
    found = {p.resolve() for p in candidates if (p / 'main.py').is_file() and (p / 'models').is_dir()}
    if len(found) != 1:
        raise ValueError('Cannot uniquely locate ComfyUI; pass --comfy-dir /actual/path/ComfyUI.')
    return found.pop()


def within(root, relative):
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError(f'Path escapes ComfyUI: {relative}')
    return path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def valid(path, model):
    if not path.is_file() or path.stat().st_size == 0:
        return False
    if model.get('size_bytes') is not None and path.stat().st_size != model['size_bytes']:
        return False
    return not model.get('sha256') or digest(path) == model['sha256']


def download(target, model, downloader="curl", connections=4):
    if target.exists():
        if valid(target, model):
            print(f'Present: {target.name}', flush=True)
            return
        raise ValueError(f'Existing file failed validation: {target}. Move/remove it and retry.')
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ('.aria2.part' if downloader == 'aria2' else '.part'))
    if valid(part, model):
        part.replace(target)
        if downloader == 'aria2':
            part.with_name(part.name + '.aria2').unlink(missing_ok=True)
        return
    start = time.monotonic()
    print(f"Download: {target.name} (~{model.get('approx_gb', '?')} GB), resume at {part.stat().st_size if part.exists() else 0} bytes", flush=True)
    if downloader == 'aria2':
        command = ['aria2c', '--allow-overwrite=true', '--auto-file-renaming=false',
                   '--continue=true', '--max-tries=4', '--retry-wait=3',
                   '--connect-timeout=30', '--summary-interval=0',
                   '--max-connection-per-server=' + str(connections),
                   '--split=' + str(connections), '--min-split-size=16M',
                   '--dir=' + str(part.parent), '--out=' + part.name, model['url']]
    else:
        command = ['curl', '--fail', '--location', '--retry', '3', '--connect-timeout', '30',
                   '--speed-limit', '1024', '--speed-time', '120', '--progress-bar',
                   '--continue-at', '-', '--output', str(part), model['url']]
    result = subprocess.run(command)
    if downloader == 'curl' and result.returncode == 33:  # No range support.
        part.unlink(missing_ok=True)
        subprocess.run(command, check=True)
    elif result.returncode:
        raise ValueError(f'Download failed ({downloader} {result.returncode}); partial retained. Rerun to resume.')
    downloaded = time.monotonic()
    print(f'Downloaded {target.name} in {downloaded - start:.1f}s; validating checksum...', flush=True)
    if not valid(part, model):
        part.unlink(missing_ok=True)
        if downloader == 'aria2':
            part.with_name(part.name + '.aria2').unlink(missing_ok=True)
        raise ValueError(f'Validation failed: {target.name}; invalid partial removed, no final file published.')
    part.replace(target)
    print(f'Validated {target.name}: {target.stat().st_size:,} bytes in {time.monotonic() - downloaded:.1f}s', flush=True)


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def custom_node(root, name, package, verify=False):
    """Pinned git checkout and interpreter-specific requirements stamp."""
    target = within(root, 'custom_nodes/' + name)
    commit = package['commit']
    if 'files' in package:
        for filename, item in package['files'].items():
            destination = within(target, filename)
            if verify:
                if not valid(destination, item):
                    raise ValueError(f'{name}: missing or invalid pinned file {filename}.')
            else:
                download(destination, item)
        print(f'Custom node present: {name} @ {commit}')
        return
    if not target.exists():
        if verify:
            raise ValueError(f'Missing custom node: {name}')
        target.parent.mkdir(parents=True, exist_ok=True)
        # Interrupted clones never leave a seemingly installed final directory.
        staging = target.with_name(name + '.installing')
        if staging.exists():
            raise ValueError(f'Remove interrupted clone {staging} and rerun.')
        subprocess.run(['git', 'clone', '--no-checkout', package['repo'], str(staging)], check=True)
        subprocess.run(['git', '-C', str(staging), 'checkout', '--detach', commit], check=True)
        staging.rename(target)
    if git(target, 'rev-parse', 'HEAD') != commit or git(target, 'status', '--porcelain', '--untracked-files=no'):
        raise ValueError(f'{name}: checkout differs from pinned commit; resolve manually.')
    if git(target, 'remote', 'get-url', 'origin') != package['repo']:
        raise ValueError(f'{name}: repository origin differs from manifest.')
    requirements = target / 'requirements.txt'
    stamp = target / '.provision-installed.json'
    identity = dict(commit=commit, python=str(Path(sys.executable).resolve()),
                    version=sys.version, requirements=digest(requirements) if requirements.exists() else None)
    if not stamp.exists() or json.loads(stamp.read_text()) != identity:
        if verify:
            raise ValueError(f'{name}: Python dependencies not provisioned using this interpreter.')
        if requirements.exists():
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(requirements)], check=True)
        stamp.write_text(json.dumps(identity))
    print(f'Custom node present: {name} @ {commit}')


def verify_nodes(workflows, url, check_models=True):
    try:
        with urlopen(url.rstrip('/') + '/object_info', timeout=30) as response:
            info = json.load(response)
    except Exception as error:
        raise ValueError(f'Cannot verify registered nodes at {url}: {error}. Start ComfyUI and rerun --verify.') from error
    missing = sorted({n for w in workflows for n in w['nodes']} - info.keys())
    if missing:
        raise ValueError('Nodes not registered: ' + ', '.join(missing) +
                         '. Check ComfyUI version/startup errors; manually restart after custom-node installation.')
    # Check loader dropdowns too: a class can exist while its model family is unsupported.
    for w in workflows:
        doc = json.loads(w['path'].read_text())
        graph = doc.get('workflow', doc)
        if w['format'] != 'API':
            continue
        for node in graph.values():
            schema = info[node['class_type']].get('input', {})
            fields = {**schema.get('required', {}), **schema.get('optional', {})}
            for key, value in node['inputs'].items():
                directory = model_directory(node['class_type'], key)
                if not check_models and directory:
                    continue
                if not directory and not (node['class_type'] == 'CLIPLoader' and key == 'type'):
                    continue
                spec = fields.get(key, [])
                choices = spec[0] if spec and isinstance(spec[0], list) else (
                    spec[1].get('options') if len(spec) > 1 and isinstance(spec[1], dict) else None)
                if choices is not None and isinstance(value, str) and value not in choices:
                    raise ValueError(f"{w['slug']}: {node['class_type']}.{key} does not offer {value!r}. Check version/model paths and refresh or manually restart ComfyUI.")
    print('Required node types and ' + ('model choices' if check_models else 'model families') +
          ' verified. GPU inference has not been tested.')


def running_comfy(root, proc=Path('/proc')):
    """Capture only a Python main.py process belonging to this installation."""
    matches = []
    for entry in proc.iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            command = (entry / 'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
            command = [os.fsdecode(arg) for arg in command]
            if not command or not Path(command[0]).name.startswith('python'):
                continue
            cwd = (entry / 'cwd').resolve(strict=True)
            if not any(arg and (cwd / arg).resolve() == root / 'main.py'
                       for arg in command[1:] if not arg.startswith('-')):
                continue
            environment = dict(os.fsdecode(item).split('=', 1)
                               for item in (entry / 'environ').read_bytes().split(b'\0') if b'=' in item)
            matches.append(dict(pid=int(entry.name), command=command, cwd=cwd, env=environment))
        except (OSError, ValueError):
            continue  # Processes may exit while /proc is being scanned.
    if len(matches) != 1:
        raise ValueError('Cannot identify exactly one running Python main.py for this ComfyUI installation. '
                         'Start it first, or use --no-restart and restart it yourself before --verify.')
    return matches[0]


def process_alive(pid):
    try:
        # A terminated child can remain as a zombie until its parent reaps it.
        return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0] != 'Z'
    except FileNotFoundError:
        return False


def restart_comfy(root, process, workflows, url):
    if running_comfy(root) != process:
        raise ValueError('ComfyUI process changed during installation; rerun to capture its current launch settings.')
    log_path = root / '.provision-comfyui.log'
    # Open the log before stopping a working server, so a permissions error is harmless.
    with log_path.open('ab') as log:
        print(f'Restarting ComfyUI (PID {process["pid"]}); startup log: {log_path}', flush=True)
        os.kill(process['pid'], signal.SIGTERM)
        deadline = time.monotonic() + 30
        while process_alive(process['pid']):
            if time.monotonic() >= deadline:
                raise ValueError('ComfyUI did not stop within 30s; no replacement was started. '
                                 'Stop it manually and rerun --verify.')
            time.sleep(0.5)
        child = subprocess.Popen(process['command'], cwd=process['cwd'], env=process['env'],
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
    deadline = time.monotonic() + 120
    while True:
        if child.poll() is not None:
            raise ValueError(f'ComfyUI exited with code {child.returncode}; check {log_path}.')
        try:
            verify_nodes(workflows, url)
            print(f'ComfyUI restarted (PID {child.pid}).', flush=True)
            return
        except ValueError as error:
            if time.monotonic() >= deadline:
                raise ValueError(f'ComfyUI did not become ready: {error} Check {log_path}.') from error
            time.sleep(1)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    for flag in ('list', 'inspect', 'install', 'verify'):
        mode.add_argument('--' + flag, action='store_true')
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--workflow')
    selection.add_argument('--all', action='store_true')
    parser.add_argument('--dry-run', action='store_true', help='Print plan only; no network or filesystem changes')
    parser.add_argument('--workflows-dir', type=Path,
                        help='Workflow library directory (default: workflows/ beside this script)')
    parser.add_argument('--comfy-dir', default=os.environ.get('COMFYUI_DIR'))
    parser.add_argument('--comfy-url', default='http://127.0.0.1:8188', help='Read-only node verification endpoint')
    parser.add_argument('--no-restart', action='store_true',
                        help='Leave ComfyUI running after installation (restart manually if needed)')
    parser.add_argument('--download-jobs', type=int, default=3,
                        help='Maximum simultaneous model downloads (default: 3)')
    parser.add_argument('--downloader', choices=('curl', 'aria2'), default='curl',
                        help='Transfer tool; aria2 enables segmented downloads (default: curl)')
    parser.add_argument('--connections', type=int, default=4,
                        help='aria2 connections per model, 1–16 (default: 4)')
    args = parser.parse_args(argv)
    if not 1 <= args.download_jobs <= 16 or not 1 <= args.connections <= 16:
        parser.error('--download-jobs and --connections must be between 1 and 16')
    if (args.install or args.verify) and not (args.workflow or args.all):
        parser.error('--install/--verify requires --workflow NAME or --all')
    start = time.monotonic()
    manifest = json.loads((ROOT / 'dependencies.json').read_text())
    directory = (args.workflows_dir or ROOT / 'workflows').expanduser().resolve()
    if not directory.is_dir():
        raise ValueError(f'Workflow directory does not exist: {directory}')
    workflows = select(discover(directory), args.workflow)
    if not workflows:
        raise ValueError(f'No workflow JSON files found under {directory}.')
    if args.list:
        for w in workflows:
            print(f"{w['slug']:24} {w['format']:4} {w['name']} [{w['key']}]")
        return 0
    if args.inspect:
        inspect(workflows, manifest)
        return 0
    assets, packages, issues = plan(workflows, manifest)
    for asset in assets:
        m = manifest['models'].get(asset, {})
        print(f"Model: {asset} (~{m.get('approx_gb', '?')} GB)\n  {m.get('url') or 'UNRESOLVED'}")
    for name in packages:
        print(f"Custom node: {name}: {manifest['custom_nodes'].get(name)}")
    print(f'Unique model payload: ~{sum(manifest["models"].get(a, {}).get("approx_gb", 0) for a in assets):.2f} GB; existing valid files will be skipped.')
    if issues:
        raise ValueError('Unresolved dependencies:\n  ' + '\n  '.join(issues))
    # Explicit per-workflow add-ons can supply UI nodes absent from the API graph.
    # Their declared node classes must still register after installation/restart.
    addon_nodes = {node for name in packages for node in manifest['custom_nodes'][name]['nodes']}
    verification_workflows = [{**w, 'nodes': w['nodes'] | addon_nodes} for w in workflows]
    if args.dry_run:
        print('Dry run: no changes or network requests. Target: ' + (args.comfy_dir or 'auto-detect on Pod'))
        return 0
    root = locate(args.comfy_dir)
    print(f'ComfyUI: {root}; Python: {sys.executable}', flush=True)
    executable = 'aria2c' if args.downloader == 'aria2' else 'curl'
    if args.install and assets and not shutil.which(executable):
        raise ValueError(f'{executable} is required for the selected downloader.')
    if packages and not shutil.which('git'):
        raise ValueError('git is required for custom nodes.')
    if args.install and not packages:
        # Fail before large downloads if the template lacks required core nodes/model families.
        verify_nodes(workflows, args.comfy_url, check_models=False)
    # A single Pod lock prevents simultaneous writers/resumers corrupting the same .part.
    with (root / '.provision.lock').open('a') if args.install else nullcontext() as lock:
        if lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        process = running_comfy(root) if args.install and not args.no_restart else None
        errors = []
        if args.install:
            # Executor shutdown waits for active transfers before releasing the Pod lock.
            with ThreadPoolExecutor(max_workers=args.download_jobs) as pool:
                futures = [pool.submit(download, within(root, asset), manifest['models'][asset],
                                       args.downloader, args.connections) for asset in assets]
                for future in futures:
                    future.result()
        else:
            for asset in assets:
                target = within(root, asset)
                if not valid(target, manifest['models'][asset]):
                    errors.append(f'Missing or invalid model: {target}')
                else:
                    print(f'Validated: {target.name}')
        for name in packages:
            custom_node(root, name, manifest['custom_nodes'][name], verify=args.verify)
        if errors:
            raise ValueError('\n'.join(errors))
        if process:
            restart_comfy(root, process, verification_workflows, args.comfy_url)
        else:
            verify_nodes(verification_workflows, args.comfy_url)
    print(f'Complete in {time.monotonic() - start:.1f}s.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('Interrupted; rerun to resume partial downloads.', file=sys.stderr)
        sys.exit(130)
