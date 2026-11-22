# VoxCPM2 standalone speech

The Artflow Audio panel can use VoxCPM2 through the local helper and an isolated Pod runtime. It accepts voice descriptions and expressive cues such as `[laughing]` in the text. Audio is played in the Audio panel and can be downloaded; it is not currently retained in Artflow's generation gallery.

VoxCPM2 installation is opt-in. Run `start-session --with-voxcpm2` when preparing a Pod. Normal session preparation does not install this model; `--skip-provision` cannot be combined with this option. Alternatively, on a suitable Pod and reviewed provisioning checkout, run `bash gpu_providers/voxcpm2/setup.sh`.

The installer pins model and source revisions and checks the model files. It uses an isolated Python environment with the template's CUDA-enabled PyTorch and torchaudio, and downloads approximately 5 GB. The A5000 live test generated a 5.4-second sample in roughly 42 seconds including a fresh model load. It requires available GPU memory; cached ComfyUI models may need to be unloaded when idle. Verify compatibility on a fresh Pod; the package avoids optional training, web UI, normalization and denoising dependencies.
