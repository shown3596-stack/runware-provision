# Chatterbox Turbo

The Artflow session launcher offers this standalone provider as an optional installation. Selecting it installs the pinned upstream source, model and isolated Python environment under `/workspace/artflow-chatterbox`; it does not modify ComfyUI's Python packages. The setup installs both the one-shot worker and the persistent server, including when rerun on an already prepared pod.

Artflow's Load/Unload controls keep the model on the GPU via a private helper-owned SSH process. Reference voice WAVs remain in Artflow's local data directory and are sent only for the generation request; they are removed from the pod after use. Reprovisioning a pod does not recreate local voice samples, so retain the local Artflow data directory when moving or reinstalling Artflow.
