#!/usr/bin/env bash
set -euo pipefail
provider_root=/workspace/artflow-chatterbox
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -e "$provider_root" && ! -f "$provider_root/.artflow-chatterbox-provider" ]]; then
  printf '%s\n' "Refusing to modify existing unmarked directory: $provider_root" >&2
  exit 1
fi
mkdir -p "$provider_root"
touch "$provider_root/.artflow-chatterbox-provider"
if [[ ! -f "$provider_root/.ready-ab55923-749d1c1" ]]; then
  if [[ ! -e "$provider_root/source" ]]; then
    git clone https://github.com/resemble-ai/chatterbox.git "$provider_root/source"
  fi
  if [[ ! -d "$provider_root/source/.git" || -n "$(git -C "$provider_root/source" status --porcelain)" ]]; then
    printf '%s\n' 'Chatterbox source checkout is invalid or modified.' >&2
    exit 1
  fi
  git -C "$provider_root/source" checkout --detach ab55923c27757c90cfcc407baa57dc25a7d25217
  /usr/bin/python3.12 -m venv --system-site-packages "$provider_root/venv"
  "$provider_root/venv/bin/python" -c 'import torch, torchaudio; assert torch.cuda.is_available()'
  "$provider_root/venv/bin/pip" install --no-deps "$provider_root/source"
  "$provider_root/venv/bin/pip" install 'numpy<2' 'librosa==0.11.0' 'transformers==5.2.0' 'diffusers==0.29.0' 'conformer==0.3.2' 's3tokenizer' 'pyloudnorm' 'omegaconf' 'pykakasi==2.3.0' 'pydub' 'PyYAML'
  "$provider_root/venv/bin/pip" install --no-deps 'git+https://github.com/resemble-ai/Perth.git@ff1c8ac55a976971245cdd53c18d6131ca00d993'
  "$provider_root/venv/bin/python" -c 'from chatterbox.tts_turbo import ChatterboxTurboTTS; import soundfile, perth; assert perth.PerthImplicitWatermarker is not None'
  "$provider_root/venv/bin/python" - "$provider_root/model" <<'PY'
import sys
from huggingface_hub import snapshot_download
snapshot_download(repo_id='ResembleAI/chatterbox-turbo', revision='749d1c1a46eb10492095d68fbcf55691ccf137cd', local_dir=sys.argv[1], ignore_patterns=['s3gen.safetensors'])
PY
  touch "$provider_root/.ready-ab55923-749d1c1"
fi
install -m 0644 "$script_dir/worker.py" "$script_dir/server.py" "$provider_root/"
printf '%s\n' 'Chatterbox Turbo provider installed.'
