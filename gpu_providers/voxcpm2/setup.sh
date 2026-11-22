#!/usr/bin/env bash
set -euo pipefail
provider_root=/workspace/artflow-voxcpm2
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -e "$provider_root" && ! -f "$provider_root/.artflow-voxcpm2-provider" ]]; then
  printf '%s\n' "Refusing to modify existing unmarked directory: $provider_root" >&2
  exit 1
fi
if [[ -f "$provider_root/.ready-300e426-7936080" && -x "$provider_root/venv/bin/python" && -f "$provider_root/model/model.safetensors" && -f "$provider_root/model/audiovae.pth" ]]; then
  install -m 0644 "$script_dir/worker.py" "$script_dir/server.py" "$provider_root/"
  printf '%s\n' 'VoxCPM2 provider is already installed.'
  exit 0
fi
mkdir -p "$provider_root"
touch "$provider_root/.artflow-voxcpm2-provider"
if [[ ! -e "$provider_root/source" ]]; then
  git clone https://github.com/OpenBMB/VoxCPM.git "$provider_root/source"
fi
if [[ ! -d "$provider_root/source/.git" || -n "$(git -C "$provider_root/source" status --porcelain)" ]]; then
  printf '%s\n' 'VoxCPM2 source checkout is invalid or modified; refusing to change it.' >&2
  exit 1
fi
git -C "$provider_root/source" checkout --detach 300e4260b509066151d623dc9c0aa922cf82232b
/usr/bin/python3.12 -m venv --system-site-packages "$provider_root/venv"
"$provider_root/venv/bin/python" -c 'import torch, torchaudio; assert torch.cuda.is_available(), "CUDA PyTorch is required"'
"$provider_root/venv/bin/pip" install --no-deps "$provider_root/source"
"$provider_root/venv/bin/pip" install 'librosa==0.11.0'
"$provider_root/venv/bin/python" -c 'from voxcpm import VoxCPM; import soundfile'
"$provider_root/venv/bin/python" - "$provider_root/model" <<'PY'
import sys
from huggingface_hub import snapshot_download
snapshot_download(repo_id='openbmb/VoxCPM2', revision='7936080b41163874f38610f46f438e2c0757f9fd', local_dir=sys.argv[1])
PY
printf '%s  %s\n' \
  f7f964cfa9da23653baec6e6f7750719977ad944ed9f95fe52fe3a620506891d "$provider_root/model/model.safetensors" \
  94b5d51e107e0507d4acc976cfdadb64edd6fd06d1f751dadbf2fd1594274bf1 "$provider_root/model/audiovae.pth" \
  405f0dcd92f7feba6011ed4eac5c8d4f74cba9712f07fd5cfa3063bbdd95402c "$provider_root/model/config.json" \
  f8984687e4a92a3503d521396d454b7d68e9fdaab2a0288eb3536c7c1aa4bc20 "$provider_root/model/tokenizer.json" | sha256sum -c -
install -m 0644 "$script_dir/worker.py" "$script_dir/server.py" "$provider_root/"
touch "$provider_root/.ready-300e426-7936080"
printf '%s\n' 'VoxCPM2 provider installed.'
