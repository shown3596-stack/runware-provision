#!/usr/bin/env python3
"""Inspect local ComfyUI exports; provision an existing Pod. Python 3.10+, stdlib only."""
import argparse
from collections import Counter
from contextlib import nullcontext
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
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
ASSET = re.compile(r'\.(safetensors|ckpt|pt|pth|bin|gguf|onnx)$', re.I)


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
                if key in MODEL_INPUTS:
                    if not isinstance(value, str) or value.startswith('API_'):
                        issues.append(f'{kind}.{key}: dynamic model selection needs review: {value!r}')
                    else:
                        assets.add(f'models/{MODEL_INPUTS[key]}/{value.replace(chr(92), "/")}')
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


def download(target, model):
    if target.exists():
        if valid(target, model):
            print(f'Present: {target.name}', flush=True)
            return
        raise ValueError(f'Existing file failed validation: {target}. Move/remove it and retry.')
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + '.part')
    if valid(part, model):
        part.replace(target)
        return
    start = time.monotonic()
    print(f"Download: {target.name} (~{model.get('approx_gb', '?')} GB), resume at {part.stat().st_size if part.exists() else 0} bytes", flush=True)
    command = ['curl', '--fail', '--location', '--retry', '3', '--connect-timeout', '30',
               '--speed-limit', '1024', '--speed-time', '120', '--progress-bar',
               '--continue-at', '-', '--output', str(part), model['url']]
    result = subprocess.run(command)
    if result.returncode == 33:  # Server does not support byte ranges. Restart safely.
        part.unlink(missing_ok=True)
        subprocess.run(command, check=True)
    elif result.returncode:
        raise ValueError(f'Download failed (curl {result.returncode}); partial retained. Rerun to resume.')
    if not valid(part, model):
        part.unlink(missing_ok=True)
        raise ValueError(f'Validation failed: {target.name}; invalid partial removed, no final file published.')
    part.replace(target)
    print(f'Validated {target.stat().st_size:,} bytes in {time.monotonic() - start:.1f}s', flush=True)


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def custom_node(root, name, package, verify=False):
    """Pinned git checkout + requirements stamp. No packages are needed by current exports."""
    target = within(root, 'custom_nodes/' + name)
    commit = package['commit']
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
                if not check_models and key in MODEL_INPUTS:
                    continue
                if key not in MODEL_INPUTS and not (node['class_type'] == 'CLIPLoader' and key == 'type'):
                    continue
                spec = fields.get(key, [])
                choices = spec[0] if spec and isinstance(spec[0], list) else (
                    spec[1].get('options') if len(spec) > 1 and isinstance(spec[1], dict) else None)
                if choices is not None and isinstance(value, str) and value not in choices:
                    raise ValueError(f"{w['slug']}: {node['class_type']}.{key} does not offer {value!r}. Check version/model paths and refresh or manually restart ComfyUI.")
    print('Required node types and ' + ('model choices' if check_models else 'model families') +
          ' verified. GPU inference has not been tested.')


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
    args = parser.parse_args(argv)
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
    if args.dry_run:
        print('Dry run: no changes or network requests. Target: ' + (args.comfy_dir or 'auto-detect on Pod'))
        return 0
    root = locate(args.comfy_dir)
    print(f'ComfyUI: {root}; Python: {sys.executable}', flush=True)
    if args.install and assets and not shutil.which('curl'):
        raise ValueError('curl is required for resumable model downloads.')
    if packages and not shutil.which('git'):
        raise ValueError('git is required for custom nodes.')
    if args.install and not packages:
        # Fail before large downloads if the template lacks required core nodes/model families.
        verify_nodes(workflows, args.comfy_url, check_models=False)
    # A single Pod lock prevents simultaneous writers/resumers corrupting the same .part.
    with (root / '.provision.lock').open('a') if args.install else nullcontext() as lock:
        if lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        errors = []
        for asset in assets:
            target = within(root, asset)
            if args.install:
                download(target, manifest['models'][asset])
            elif not valid(target, manifest['models'][asset]):
                errors.append(f'Missing or invalid model: {target}')
            else:
                print(f'Validated: {target.name}')
        for name in packages:
            custom_node(root, name, manifest['custom_nodes'][name], verify=args.verify)
        if errors:
            raise ValueError('\n'.join(errors))
        verify_nodes(workflows, args.comfy_url)
    print(f'Complete in {time.monotonic() - start:.1f}s. ComfyUI was not restarted.')
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
