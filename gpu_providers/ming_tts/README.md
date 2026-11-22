# Ming TTS standalone prototype

This opt-in provider uses Ming 3.0 TTS 0.5B outside ComfyUI. It runs English free-form voice instructions and returns a WAV. The Artflow prototype plays audio in the Audio controls and offers a download; it does not persist it in the job gallery. Text normalization is disabled in this first version, so spell out numbers when needed.

On a compatible Runpod template with Python 3.12 and CUDA-enabled system PyTorch/torchaudio, run from a published provisioning checkout:

```sh
bash gpu_providers/ming_tts/setup.sh
```

The setup installs into `/workspace/artflow-ming-poc`, pins the upstream code and model revision, and verifies model, speaker encoder and config checksums. The model weights require about 3 GB. Normal workflow synchronization and `start-session` do not automatically install this prototype. The existing unmarked-directory check prevents overwriting unrelated files. The tested host had an A5000 with system PyTorch 2.10; other template versions and GPUs require validation.
