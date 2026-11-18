#!/usr/bin/env python3
"""Install SHARP's two isolated node environments on a compatible ComfyUI Pod."""
import os
import json
from pathlib import Path
import subprocess
import sys

PACKS = {
    'ComfyUI-Sharp': ('https://github.com/PozzettiAndrea/ComfyUI-Sharp.git', '92c0015af61b71e6fd88301cfb336e7034f19796'),
    'ComfyUI-GaussianPack': ('https://github.com/PozzettiAndrea/ComfyUI-GaussianPack.git', '059313a53ffa7ecc8697eddc02d2cee4727e5085'),
}


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def preflight(root):
    nodes = root / 'custom_nodes'
    if not nodes.is_dir():
        raise ValueError('ComfyUI custom_nodes directory not found')
    other = [p.name for p in nodes.iterdir() if p.is_dir() and p.name not in PACKS
             and not p.name.startswith(('.', '_')) and any(p.rglob('comfy-env.toml'))]
    if other:
        raise ValueError('SHARP isolated setup cannot rewrite the shared comfy-env workspace while other packs use it: ' + ', '.join(other))
    workspace = Path(os.environ.get('COMFY_ENV_ROOT', str(Path.home() / '.ce')))
    if workspace.exists() and (workspace / 'pixi.toml').exists():
        marker = nodes / '.provision-sharp-workspace.json'
        if not marker.is_file() or json.loads(marker.read_text()) != {'root': str(root), 'workspace': str(workspace)}:
            raise ValueError(f'Existing comfy-env workspace at {workspace}; refusing to overwrite it. Review it before installing SHARP.')
    elif os.statvfs(root).f_bavail * os.statvfs(root).f_frsize < 40_000_000_000:
        raise ValueError('SHARP setup needs at least 40 GB free for its environments and package cache.')
    return workspace


def install(root):
    root = Path(root).resolve()
    workspace = preflight(root)
    for name, (repo, commit) in PACKS.items():
        target = root / 'custom_nodes' / name
        if not target.exists():
            subprocess.run(['git', 'clone', '--no-checkout', repo, str(target)], check=True)
            subprocess.run(['git', '-C', str(target), 'checkout', '--detach', commit], check=True)
        if git(target, 'rev-parse', 'HEAD') != commit or git(target, 'status', '--porcelain', '--untracked-files=no'):
            raise ValueError(f'{name} checkout differs from the reviewed revision')
    paths = [root / 'custom_nodes' / name / 'requirements.txt' for name in PACKS]
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(paths[0]), '-r', str(paths[1])], check=True)
    marker = root / 'custom_nodes' / '.provision-sharp-workspace.json'
    marker.write_text(json.dumps({'root': str(root), 'workspace': str(workspace)}) + '\n')
    from comfy_env.install.workspace import install_workspace
    install_workspace(root)
    runtime = Path(os.environ.get('COMFY_ENV_ROOT', str(Path.home() / '.ce'))) / '.pixi' / 'envs' / 'gaussianpack-nodes' / 'bin' / 'python'
    subprocess.run([sys.executable, '-m', 'uv', 'pip', 'install', '--python', str(runtime),
                    'comfy-aimdo==0.6.0', 'comfy-kitchen==0.2.41', 'einops', 'safetensors', 'scipy'], check=True)
    print('SHARP isolated environments installed; restart ComfyUI and verify node registration.', flush=True)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: install_sharp_runtime.py /path/to/ComfyUI')
    install(sys.argv[1])
