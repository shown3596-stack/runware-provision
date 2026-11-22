#!/usr/bin/env bash
set -euo pipefail
# Run from this directory on a CUDA-enabled Pod with Python 3.12 and PyTorch.
provider_root=/workspace/artflow-depth-poc
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -e "$provider_root" && ! -f "$provider_root/.artflow-depth-provider" ]]; then
  printf '%s\n' "Refusing to modify existing unmarked directory: $provider_root" >&2
  exit 1
fi
if [[ -f "$provider_root/.ready-aa389cbb-85e67fdf" && -x "$provider_root/venv/bin/python" && -f "$provider_root/weights-b/model.safetensors" && -f "$provider_root/worker.py" ]]; then
  install -m 0644 "$script_dir/worker.py" "$provider_root/worker.py"
  printf '%s\n' 'Depth Pro 2 standalone provider is already installed.'
  exit 0
fi
mkdir -p "$provider_root"
touch "$provider_root/.artflow-depth-provider"
/usr/bin/python3.12 -m venv --system-site-packages "$provider_root/venv"
"$provider_root/venv/bin/python" -c 'import torch; assert torch.cuda.is_available(), "CUDA PyTorch is required"'
"$provider_root/venv/bin/pip" install 'timm==1.0.27' pillow-heif 'git+https://github.com/apple-aiml-research/ml-depth-pro-2.git@aa389cbb0b74341664ed663a0966c859905cd6c0'
"$provider_root/venv/bin/python" - "$provider_root/weights-b" <<'PY'
import sys
from huggingface_hub import snapshot_download
snapshot_download(repo_id='apple/DepthPro2-B', revision='85e67fdfb7f5b36a6f6c4495e6789d331b1d8a04', local_dir=sys.argv[1])
PY
printf '%s  %s\n' \
  895c4cd7d2f1756f4adfdfe29c6e227784c463b33db194ab439c0e8f2a07337e "$provider_root/weights-b/config.json" \
  244ff85e0d9bde6e0f985de1c61420abc4c2110265b495c974556225ac2b60ed "$provider_root/weights-b/model.safetensors" | sha256sum -c -
install -m 0644 "$script_dir/worker.py" "$provider_root/worker.py"
touch "$provider_root/.ready-aa389cbb-85e67fdf"
printf '%s\n' 'Depth Pro 2 standalone provider installed.'
