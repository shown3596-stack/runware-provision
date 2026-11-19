"""Install the pinned InfiniSplat node's isolated runtime without changing ComfyUI Python."""
import os
from pathlib import Path
import subprocess
import sys


def main():
    target = Path(sys.argv[1])
    uv_root = target / '.provision-uv'
    uv = uv_root / 'bin' / 'uv'
    if not uv.is_file():
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--target', str(uv_root), 'uv==0.13.9'], check=True)
    env = os.environ.copy()
    env['PATH'] = str(uv.parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([str(uv), 'run', '--no-project', str(target / 'install.py')], cwd=target, env=env, check=True)


if __name__ == '__main__':
    main()
