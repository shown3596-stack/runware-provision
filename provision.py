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
import tempfile
import threading
import time
from urllib.request import urlopen
from urllib.parse import urlsplit, unquote

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
    ('LoadZImageModel //ZImagePowerNodes', 'checkpoint'): 'diffusion_models',
    ('LoadQwen34bModel //ZImagePowerNodes', 'checkpoint'): 'text_encoders',
}
MODEL_OBJECT_INPUTS = {
    ('LTXVLatentUpsampler', 'upscale_model'): ('LatentUpscaleModelLoader', 0),
}
ASSET = re.compile(r'\.(safetensors|ckpt|pt|pth|bin|gguf|onnx)$', re.I)


def human_bytes(value):
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if value < 1024 or unit == 'TiB':
            return f'{value:.1f} {unit}' if unit != 'B' else f'{value:.0f} B'
        value /= 1024


class DownloadDisplay:
    """Coordinate concurrent transfers without letting their terminal output collide."""
    def __init__(self, total, stream=None):
        self.total = total
        self.stream = stream or sys.stderr
        self.tty = self.stream.isatty()
        self.lock = threading.Lock()
        self.items = {}
        self.progress = {}
        self.completed = 0
        self.results = []
        self.stop = threading.Event()
        self.thread = None
        self.lines = 0

    def __enter__(self):
        self.thread = threading.Thread(target=self._refresh, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set()
        if self.thread:
            self.thread.join()
            if self.tty and self.lines:
                self._clear()
            for result in self.results:
                print(result, file=self.stream, flush=True)

    def update(self, target, state, part=None, size=None, downloader='curl', detail=''):
        with self.lock:
            if state in ('ready', 'present', 'failed'):
                self.items.pop(target, None)
                self.progress.pop(target, None)
                if state != 'failed':
                    self.completed += 1
            else:
                try:
                    initial = part.stat().st_size if part else 0
                except OSError:
                    initial = 0
                self.items[target] = (state, part, size, downloader, time.monotonic(), initial)
            message = f'[{self.completed}/{self.total}] {target.name}: {state}{detail}'
            if self.tty and state in ('ready', 'present', 'failed'):
                self.results.append(message)
            elif not self.tty:
                print(message, file=self.stream, flush=True)

    def transfer_progress(self, target, detail):
        with self.lock:
            if target not in self.items:
                return
            self.progress[target] = detail
            if not self.tty and not isinstance(detail, tuple):
                print(f'[{self.completed}/{self.total}] {target.name}: {detail}', file=self.stream, flush=True)

    def _clear(self):
        if self.lines:
            self.stream.write(f'\033[{self.lines}A')
            for _ in range(self.lines):
                self.stream.write('\r\033[2K\n')
            self.stream.write(f'\033[{self.lines}A')
            self.stream.flush()
            self.lines = 0

    def _format(self, target, item, width=None):
        state, part, size, downloader, started, initial = item
        detail = state
        if state == 'downloading':
            if downloader == 'hf-xet':
                current, total, initial_progress = self.progress.get(target, (0, size, 0))
                ratio = min(current / total, 1) if total else None
                detail = human_bytes(current)
                if total:
                    detail += f'/{human_bytes(total)}'
                elapsed = time.monotonic() - started
                if elapsed > 0:
                    detail += f' {human_bytes(max(0, current - initial_progress) / elapsed)}/s'
            elif downloader == 'aria2':
                detail = self.progress.get(target, 'connecting / downloading')
                match = re.search(r'\((\d+(?:\.\d+)?)%\)', detail)
                ratio = min(float(match.group(1)) / 100, 1) if match else None
            else:
                try:
                    current = part.stat().st_size
                except OSError:
                    current = 0
                ratio = min(current / size, 1) if size else None
                detail = human_bytes(current)
                if size:
                    detail += f'/{human_bytes(size)}'
                elapsed = time.monotonic() - started
                if elapsed > 0 and current >= initial:
                    detail += f' {human_bytes((current - initial) / elapsed)}/s'
            if ratio is not None:
                filled = int(ratio * 16)
                detail = f"[{'#' * filled}{'-' * (16 - filled)}] {ratio:5.1%} {detail}"
            else:
                detail = f'[        ?       ] {detail}'
        prefix = f'[{self.completed}/{self.total}] '
        name = target.name
        if width is not None:
            available = max(1, width - len(prefix) - len(detail) - 3)
            if len(name) > available:
                name = name[:max(0, available - 1)] + '…'
        return f'{prefix}{name}: {detail}'

    def _refresh(self):
        interval = 0.25 if self.tty else 5
        while not self.stop.wait(interval):
            with self.lock:
                width = shutil.get_terminal_size((80, 24)).columns - 1 if self.tty else None
                lines = [self._format(target, item, width) for target, item in self.items.items()]
                if self.tty:
                    self._clear()
                    for line in lines:
                        print(line[:max(0, width)], file=self.stream)
                    self.stream.flush()
                    self.lines = len(lines)
                else:
                    for line in lines:
                        print(line, file=self.stream, flush=True)


download_display = None


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


def ensure_downloader(downloader):
    if downloader == 'hf-xet':
        try:
            import huggingface_hub
            import hf_xet
        except ImportError as error:
            raise ValueError('hf-xet requires huggingface_hub and hf_xet; install with: python3 -m pip install -U huggingface_hub hf_xet') from error
        if os.environ.get('HF_HUB_DISABLE_XET', '').upper() in ('1', 'ON', 'YES', 'TRUE'):
            raise ValueError('HF_HUB_DISABLE_XET is set; unset it to use --downloader hf-xet.')
        return
    executable = 'aria2c' if downloader == 'aria2' else 'curl'
    if shutil.which(executable):
        return
    if downloader != 'aria2':
        raise ValueError('curl is required for the selected downloader.')
    hint = 'Install aria2 manually or rerun with --downloader curl.'
    apt = shutil.which('apt-get')
    if not apt:
        raise ValueError(f'aria2c is missing and apt-get is unavailable. {hint}')
    prefix = []
    if os.geteuid() != 0:
        sudo = shutil.which('sudo')
        if not sudo:
            raise ValueError(f'aria2c installation requires root or passwordless sudo. {hint}')
        prefix = [sudo, '-n']
    print('aria2c is missing; installing aria2 with apt-get...', flush=True)
    env = dict(os.environ, DEBIAN_FRONTEND='noninteractive')
    try:
        subprocess.run(prefix + [apt, 'update'], check=True, env=env)
        subprocess.run(prefix + [apt, 'install', '-y', 'aria2'], check=True, env=env)
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError(f'Automatic aria2 installation failed: {error}. {hint}') from error
    if not shutil.which('aria2c'):
        raise ValueError(f'aria2 was installed but aria2c is not on PATH. {hint}')


def aria2_transfer(command, target):
    """Read aria2's periodic summaries while retaining its diagnostics on failure."""
    stop = threading.Event()
    with tempfile.TemporaryFile() as output:
        def monitor():
            offset, pending = 0, ''
            last_report = time.monotonic()
            started = last_report
            while not stop.wait(2):
                chunk = os.pread(output.fileno(), 65536, offset)
                offset += len(chunk)
                pending += chunk.decode('utf-8', errors='replace')
                lines = pending.split('\n')
                pending = lines.pop()[-4096:]
                for line in lines:
                    match = re.search(r'\[#\S+\s+([^\]]+)]', line)
                    if match:
                        detail = match.group(1).strip()
                        if download_display:
                            download_display.transfer_progress(target, detail)
                        else:
                            print(f'{target.name}: {detail}', flush=True)
                        last_report = time.monotonic()
                if time.monotonic() - last_report >= 10:
                    detail = f'waiting for aria2 transfer update ({int(time.monotonic() - started)}s elapsed)'
                    if download_display:
                        download_display.transfer_progress(target, detail)
                    else:
                        print(f'{target.name}: {detail}', flush=True)
                    last_report = time.monotonic()
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        try:
            result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT)
        finally:
            stop.set()
            thread.join()
        output.seek(0, os.SEEK_END)
        length = output.tell()
        output.seek(max(0, length - 8192))
        diagnostic = output.read().decode('utf-8', errors='replace').strip()
    return result.returncode, diagnostic


def hf_xet_transfer(target, model, token):
    """Download a pinned Hub file into a resumable, target-specific staging directory."""
    from huggingface_hub import hf_hub_download
    from tqdm.auto import tqdm

    url = urlsplit(model['url'])
    parts = url.path.split('/')
    if len(parts) < 6 or parts[3] != 'resolve' or not all(parts[1:5]):
        raise ValueError(f'Unsupported Hugging Face model URL: {model["url"]}')
    repo_id = unquote(parts[1]) + '/' + unquote(parts[2])
    revision = unquote(parts[4])
    filename = unquote('/'.join(parts[5:]))
    if not filename or any(part in ('', '.', '..') for part in filename.split('/')):
        raise ValueError('Invalid Hugging Face filename in manifest.')
    staging = target.parent / ('.' + target.name + '.hf-download')

    class Progress(tqdm):
        def __init__(self, *args, **kwargs):
            self.transferred = kwargs.get('initial', 0) or 0
            self.initial_progress = self.transferred
            self.transfer_total = kwargs.get('total') or model.get('size_bytes')
            self.transfer_lock = threading.Lock()
            kwargs['disable'] = True
            super().__init__(*args, **kwargs)

        def update(self, n=1):
            with self.transfer_lock:
                self.transferred += n
                if download_display:
                    download_display.transfer_progress(target, (self.transferred, self.transfer_total, self.initial_progress))

    try:
        return Path(hf_hub_download(repo_id=repo_id, filename=filename, revision=revision,
                                    local_dir=staging, token=token, tqdm_class=Progress))
    except Exception as error:
        detail = str(error)
        if token:
            detail = detail.replace(token, '[redacted]')
        raise ValueError(f'Hugging Face download failed for {target}: {detail}; rerun to resume.') from None


def download(target, model, downloader="curl", connections=4):
    try:
        _download(target, model, downloader, connections)
    except Exception:
        if download_display:
            download_display.update(target, 'failed')
        raise


def _download(target, model, downloader, connections):
    url = urlsplit(model['url'])
    token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGING_FACE_HUB_TOKEN')
    token = token if url.scheme == 'https' and url.hostname == 'huggingface.co' and url.port in (None, 443) else None
    if token and not re.fullmatch(r'[A-Za-z0-9_-]+', token):
        raise ValueError('Invalid Hugging Face token in environment; check HF_TOKEN.')
    if downloader == 'hf-xet' and not (url.scheme == 'https' and url.hostname == 'huggingface.co' and url.port in (None, 443)):
        ensure_downloader('curl')
        downloader = 'curl'
    if token and downloader == 'aria2':
        # curl limits Authorization to the original host when following redirects.
        ensure_downloader('curl')
        downloader = 'curl'
    def status(state, part=None, detail=''):
        if download_display:
            download_display.update(target, state, part, model.get('size_bytes'), downloader, detail)
        else:
            print(f'{target.name}: {state}{detail}', flush=True)

    if target.exists():
        status('checking existing file')
        if valid(target, model):
            status('present')
            return
        raise ValueError(f'Existing file failed validation: {target}. Move/remove it and retry.')
    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = {'aria2': '.aria2.part', 'hf-xet': '.hf.part'}.get(downloader, '.part')
    part = target.with_name(target.name + suffix)
    if part.exists():
        status('checking partial file')
    if valid(part, model):
        part.replace(target)
        if downloader == 'aria2':
            part.with_name(part.name + '.aria2').unlink(missing_ok=True)
        status('ready')
        return
    transfer_start = time.monotonic()
    status('downloading', part)
    if downloader == 'hf-xet':
        downloaded_path = hf_xet_transfer(target, model, token)
        downloaded_path.replace(part)
    elif downloader == 'aria2':
        command = ['aria2c', '--allow-overwrite=true', '--auto-file-renaming=false',
                   '--continue=true', '--max-tries=4', '--retry-wait=3',
                   '--connect-timeout=30', '--timeout=60', '--summary-interval=5',
                   '--enable-color=false', '--show-console-readout=false',
                   '--max-connection-per-server=' + str(connections),
                   '--split=' + str(connections), '--min-split-size=16M',
                   '--dir=' + str(part.parent), '--out=' + part.name, model['url']]
    else:
        command = ['curl', '--fail', '--location', '--retry', '3', '--connect-timeout', '30',
                   '--speed-limit', '1024', '--speed-time', '120', '--silent', '--show-error',
                   '--continue-at', '-', '--output', str(part), model['url']]
        if token:
            command[1:1] = ['--config', '-']
    if downloader == 'hf-xet':
        returncode, detail = 0, ''
    elif downloader == 'aria2':
        returncode, detail = aria2_transfer(command, target)
    else:
        kwargs = {'input': f'header = "Authorization: Bearer {token}"\n'} if token else {}
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, **kwargs)
        returncode, detail = result.returncode, result.stderr or ''
    if downloader == 'curl' and returncode == 33:  # No range support.
        part.unlink(missing_ok=True)
        status('restarting without resume')
        status('downloading', part)
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, **kwargs)
        returncode, detail = result.returncode, result.stderr or ''
    if returncode:
        if token:
            detail = detail.replace(token, '[redacted]')
        raise ValueError(f'Download failed for {target} ({downloader} {returncode}): {detail.strip()}; partial retained. Rerun to resume.')
    downloaded = time.monotonic()
    status('validating checksum')
    if not valid(part, model):
        part.unlink(missing_ok=True)
        if downloader == 'aria2':
            part.with_name(part.name + '.aria2').unlink(missing_ok=True)
        raise ValueError(f'Validation failed: {target.name}; invalid partial removed, no final file published.')
    part.replace(target)
    status('ready', detail=f' (transfer {downloaded - transfer_start:.1f}s; validation {time.monotonic() - downloaded:.1f}s)')


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def custom_node(root, name, package, verify=False, downloader='curl', connections=4):
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
                download(destination, item, downloader, connections)
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
        if package.get('runtime') == 'qwen3_tts_isolated':
            installer = target / 'install.py'
            script = ("import os,runpy,torch; from pathlib import Path; "
                      "m=runpy.run_path(os.environ['QWEN_INSTALLER']); "
                      "m['main'].__globals__['shared_site_packages']=lambda: Path(torch.__file__).resolve().parent.parent; "
                      "m['main']()")
            env = dict(os.environ, QWEN3_TTS_SKIP_MODEL_DOWNLOAD='1', QWEN_INSTALLER=str(installer))
            subprocess.run([sys.executable, '-c', script], env=env, check=True)
        elif requirements.exists():
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(requirements)], check=True)
        stamp.write_text(json.dumps(identity))
    if package.get('runtime') == 'qwen3_tts_isolated':
        runtime = target / '.venv' / 'bin' / 'python'
        subprocess.run([str(runtime), '-c', 'from qwen_tts import Qwen3TTSModel; import torch; assert torch.cuda.is_available()'], check=True)
    print(f'Custom node present: {name} @ {commit}')


def bundled_memory_node(root, verify=False):
    """Install only our own checksum-tracked bundled node; never replace user files."""
    source = ROOT / 'bundled_nodes' / 'prompt_fusion_memory' / '__init__.py'
    if not source.is_file():
        raise ValueError('Bundled Prompt Fusion memory node is missing from provisioning checkout.')
    target = within(root, 'custom_nodes/prompt_fusion_memory')
    code, stamp = target / '__init__.py', target / '.prompt-fusion-node.json'
    expected = digest(source)
    if code.is_file() and digest(code) == expected:
        if verify:
            return
    elif verify:
        raise ValueError('Prompt Fusion memory output node is missing or differs from provisioning.')
    elif target.exists():
        try:
            prior = json.loads(stamp.read_text())['sha256']
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise ValueError('Existing prompt_fusion_memory node is not managed by provisioning.') from error
        if not code.is_file() or digest(code) != prior:
            raise ValueError('Existing prompt_fusion_memory node was modified; resolve it before updating.')
    else:
        target.mkdir(parents=True)
    temporary = target / '__init__.py.provision.tmp'
    shutil.copyfile(source, temporary)
    temporary.replace(code)
    stamp.write_text(json.dumps({'sha256': expected}) + '\n')
    print('Prompt Fusion memory output node installed.', flush=True)


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
    global download_display
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
    parser.add_argument('--download-jobs', type=int, default=1,
                        help='Maximum simultaneous model downloads (default: 1)')
    parser.add_argument('--downloader', choices=('curl', 'aria2', 'hf-xet'), default='hf-xet',
                        help='Transfer tool; hf-xet uses the Hugging Face client for Hub files (default: hf-xet)')
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
    print('Bundled node: prompt_fusion_memory (RAM-only image and video results).')
    if issues:
        raise ValueError('Unresolved dependencies:\n  ' + '\n  '.join(issues))
    # Explicit per-workflow add-ons can supply UI nodes absent from the API graph.
    # Their declared node classes must still register after installation/restart.
    addon_nodes = {node for name in packages for node in manifest['custom_nodes'][name]['nodes']}
    addon_nodes.update({'PromptFusionMemoryImage', 'PromptFusionMemoryVideo'})
    if any('SaveQwen3TTSAudio' in workflow['nodes'] for workflow in workflows):
        addon_nodes.add('PromptFusionMemoryQwenAudio')
    verification_workflows = [{**w, 'nodes': w['nodes'] | addon_nodes} for w in workflows]
    if args.dry_run:
        print('Dry run: no changes or network requests. Target: ' + (args.comfy_dir or 'auto-detect on Pod'))
        return 0
    root = locate(args.comfy_dir)
    print(f'ComfyUI: {root}; Python: {sys.executable}', flush=True)
    needs_downloader = assets or any('files' in manifest['custom_nodes'][name] for name in packages)
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
        if args.install and needs_downloader:
            sources = [manifest['models'][asset] for asset in assets]
            sources += [item for name in packages for item in manifest['custom_nodes'][name].get('files', {}).values()]
            has_hub = any(urlsplit(item['url']).hostname == 'huggingface.co' for item in sources)
            ensure_downloader(args.downloader if args.downloader != 'hf-xet' or has_hub else 'curl')
        bundled_memory_node(root, verify=args.verify)
        errors = []
        if args.install:
            # Executor shutdown waits for active transfers before releasing the Pod lock.
            print(f'Installing {len(assets)} models with up to {args.download_jobs} concurrent downloads...', flush=True)
            with DownloadDisplay(len(assets)) as display:
                download_display = display
                try:
                    with ThreadPoolExecutor(max_workers=args.download_jobs) as pool:
                        futures = [pool.submit(download, within(root, asset), manifest['models'][asset],
                                               args.downloader, args.connections) for asset in assets]
                        for future in futures:
                            future.result()
                finally:
                    download_display = None
            print('Model downloads and validation complete.', flush=True)
        else:
            for asset in assets:
                target = within(root, asset)
                if not valid(target, manifest['models'][asset]):
                    errors.append(f'Missing or invalid model: {target}')
                else:
                    print(f'Validated: {target.name}')
        for name in packages:
            package = manifest['custom_nodes'][name]
            if args.install and 'files' in package:
                with DownloadDisplay(len(package['files'])) as display:
                    download_display = display
                    try:
                        custom_node(root, name, package, downloader=args.downloader, connections=args.connections)
                    finally:
                        download_display = None
            else:
                custom_node(root, name, package, verify=args.verify,
                            downloader=args.downloader, connections=args.connections)
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
