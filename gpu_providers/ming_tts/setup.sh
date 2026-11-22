#!/usr/bin/env bash
set -euo pipefail
# Explicit opt-in installer for the Ming proof of concept; not run by workflow sync.
provider_root=/workspace/artflow-ming-poc
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -e "$provider_root" && ! -f "$provider_root/.artflow-ming-provider" ]]; then
  printf '%s\n' "Refusing to modify existing unmarked directory: $provider_root" >&2
  exit 1
fi
mkdir -p "$provider_root"
touch "$provider_root/.artflow-ming-provider"
if [[ ! -d "$provider_root/source/.git" ]]; then
  git clone https://github.com/inclusionAI/Ming-3.0-tts.git "$provider_root/source"
fi
git -C "$provider_root/source" checkout --detach c88c023ea6ccc08fd1e7a1d289cb6246c21deff1
/usr/bin/python3.12 -m venv --system-site-packages "$provider_root/venv"
"$provider_root/venv/bin/python" -c 'import torch, torchaudio; assert torch.cuda.is_available(), "CUDA PyTorch is required"'
"$provider_root/venv/bin/pip" install 'transformers==4.46.3' 'accelerate==1.3.0' 'x_transformers==2.9.2' 'diffusers==0.33.0' onnxruntime inflect 'soundfile==0.12.1'
"$provider_root/venv/bin/python" - "$provider_root/model" <<'PY'
import sys
from huggingface_hub import snapshot_download
snapshot_download(repo_id='inclusionAI/Ming-3.0-tts-0.5B', revision='ffd36ab5764c39c7e5565dfed66a3aeeced58ab9', local_dir=sys.argv[1])
PY
printf '%s  %s\n' \
  45c4d78d8ad6b1d942e3da86ba035fece02de569f7b2ca7e9d121dfaf18d674c "$provider_root/model/model.safetensors" \
  a6ac6a63997761ae2997373e2ee1c47040854b4b759ea41ec48e4e42df0f4d73 "$provider_root/model/campplus.onnx" \
  2fb0767361b3cd3f41dc9392709fc23fe5b40a39f19d70a38d04acabe991822c "$provider_root/model/config.json" | sha256sum -c -
install -m 0644 "$script_dir/worker.py" "$provider_root/worker.py"
printf '%s\n' 'Ming TTS prototype installed.'
