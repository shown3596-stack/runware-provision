# Workflow sync — 24 October 2026

Applied `sync_provision.py --all --prune --apply` from the authoritative app
library. Added `ernie-image-turbo.json`, `qwen-image-2-1-turbo.json`, and
`z-image-turbo.json`; Qwen 2512, Krea 2 Turbo FP8 and Mage Flow Turbo were unchanged.
No snapshots or dependency entries needed pruning this time. All six destination
files match the app byte for byte, and app source hashes are unchanged.

The library now references **20 unique model files** (about **134.67 GB**) and
**31 node types**, with no custom-node repositories. Disabled branches remain
included, including the Qwen Image 2.1 prompt enhancer. Workflow IDs, defaults,
sampling settings and parameter markers were copied unchanged.

Ten model declarations were added with SHA-256 checksums and full pinned revisions
from publisher file pages in [Comfy-Org/ERNIE-Image](https://huggingface.co/Comfy-Org/ERNIE-Image),
[Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1), and
[Comfy-Org/Z-Image-Turbo](https://huggingface.co/Comfy-Org/Z-Image-Turbo).
The manifest records each exact source page, revision, destination, checksum and
rounded publisher size; rounded sizes are informational. These new entries carry
the 2026-10-24 source-verification date; earlier verification dates are preserved.
No model payloads were downloaded.

Nine core-node mappings were reviewed in upstream ComfyUI source:
`StringReplace` in [nodes_string.py](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_string.py),
`EmptyFlux2LatentImage` in [nodes_flux.py](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_flux.py),
`TextEncodeQwenImage21` and `QwenImage21Cache` in
[nodes_qwen.py](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_qwen.py),
and `ManualSigmas`, `KSamplerSelect`, `RandomNoise`, `SamplerCustomAdvanced` and
`CFGGuider` in [nodes_custom_sampler.py](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_custom_sampler.py).
These mappings establish ownership, not runtime compatibility or a tested
minimum ComfyUI version. No runtime upgrade was performed.

Validation passed: full sync/prune check, all-workflow provisioning dry run,
20 sync tests and 15 provisioning tests. No Pod installation, live schema checks
or GPU generation were performed.

## Previous sync — 23 October 2026

Synced the current app library unchanged: `qwen-2512.json` (Qwen 2512),
`krea-2-turbo-fp8.json` (Krea 2 Turbo FP8), and `mage-flow-turbo.json`
(Mage Flow Turbo). Their stable workflow IDs and parameter defaults are preserved.
Chroma1 HD was removed from the app at the user's request and was not promoted.

Full-library sync now includes removal of workflows deleted from the app. This
run removed the four obsolete UUID-named snapshots from the historical audit,
including Qwen Turbo, Krea INT8, and older duplicate copies. It also removed the
unused `krea2_turbo_int8_convrot.safetensors` and
`Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16.safetensors` model declarations,
the four obsolete per-workflow entries, and the unused `ResolutionSelector`
core-node mapping. Shared models and remaining graph/override references were
preserved.

The resulting **three snapshots** reference **10 unique model files** (about
**63.92 GB**) and **22 node types**, with no custom-node repositories. The full
`--all --prune --check` passes, app source hashes match their pre-sync values,
and manifest provenance notes/verification dates remain unchanged. These are
local repository removals, not model-file deletion or package uninstallation
on an existing Pod. The historical audit below records the removed library's
original state and sources.

Mage uses `mage_flow_turbo_int8_convrot.safetensors`,
`qwen3vl_4b_bf16.safetensors`, and `mage_flow_vae_bf16.safetensors` from
[Comfy-Org/Mage-Flow](https://huggingface.co/Comfy-Org/Mage-Flow/tree/6ff68fbf3c667325e961d551691b246791d5eec0).
Publisher API metadata supplied the exact byte sizes and SHA-256 checksums;
all three downloads are pinned to that revision in `dependencies.json`.
Its four-step Euler/simple sampler, CFG 1, original positive prompt, blank
negative prompt, 1024-square defaults and PNG output settings are preserved.
Custom dimensions should use multiples of 16, up to 8192 per dimension.

`TextEncodeMageFlowEdit` and `SaveImageAdvanced` were inspected in
[ComfyUI Mage nodes](https://github.com/Comfy-Org/ComfyUI/blob/d07dff4565ea9804277fff8cdfa0c817e08c3d44/comfy_extras/nodes_mage.py)
and [image nodes](https://github.com/Comfy-Org/ComfyUI/blob/d07dff4565ea9804277fff8cdfa0c817e08c3d44/comfy_extras/nodes_images.py).
This establishes source ownership, not a tested minimum runtime version.
The template must expose those nodes and the `mage` encoder family; no automatic
core upgrade is requested. The earlier model verification dates remain unchanged.
No model payload downloads, Pod installation, live schema checks or GPU inference
were performed during this sync.

## Historical audit — 22 October 2026

At the time of this historical audit, the four UUID-named JSON files were
unchanged snapshots copied from the separate `comfyui-api-poc` workflow library.
All four were inspected; these older snapshots have since been removed from the
current provisioning library. Each contains a named
library wrapper around an **API-format** graph, rather than UI `nodes`/`links`.
The original files were not modified. There are **9 unique model files** and
**21 unique node types**. No checkpoint, ControlNet, embedding, input image,
upscaler, or external custom-node repository is explicitly referenced.

| Discovered command name | Library file | Graph nodes | Model files | Approx. download |
| --- | --- | ---: | ---: | ---: |
| `qwen-2512-turbo` | `37625afe54d44ce18d1d448f0cfbd15f.json` | 11 | 4 | 32.39 GB |
| `qwen-2512` | `3b6da2434a25463084c06118dcd74bf5.json` | 19 | 4 | 31.73 GB |
| `imported-workflow` | `7dda5a7153ce42ab9ff9da464bcde99a.json` | 22 | 4 | 19.06 GB |
| `krea-2-turbo` | `93ff8dfe40cb45adb8672731aea68328.json` | 22 | 4 | 19.46 GB |

### Per-workflow models and settings

- **qwen-2512-turbo:** `qwen_image_2512_fp8_e4m3fn.safetensors`,
  `qwen_2.5_vl_7b_fp8_scaled.safetensors`, `qwen_image_vae.safetensors`, and
  `Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16.safetensors`.
  Qwen Image encoder type, two sampling steps, CFG 1, 1328 × 1328 latent.
  Requires substitution of `API_POSITIVE_PROMPT` by the existing app.
- **qwen-2512:** same Qwen diffusion model, encoder and VAE; LoRA is
  `Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors` instead.
  Switch defaults enable the four-step LoRA, CFG 1. Requires prompt,
  width and height parameter substitution. Disabled branch uses 50 steps/CFG 4.
- **imported-workflow:** `krea2_turbo_fp8_scaled.safetensors`,
  `qwen3vl_4b_fp8_scaled.safetensors`, `qwen_image_vae.safetensors`,
  `krea2_darkbrush.safetensors`. Encoder type `krea2`, eight steps, CFG 1.
  Prompt-refinement and LoRA switches default off. Prompt and ratio are parameters.
- **krea-2-turbo:** same Krea encoder, VAE and LoRA, but diffusion model is
  **`krea2_turbo_int8_convrot.safetensors`**, a distinct quantization; it must not
  be replaced silently with FP8 or a similarly named third-party INT8 export.
  Switches default off, fixed square ratio; prompt and seed are parameters.

Every referenced branch is included, even if currently disabled; no graph pruning
or workflow rewriting is performed. Both Krea exports append
`muted minimalist sketch style` when the LoRA is enabled; the publisher currently
lists `monochrome ink wash style` for darkbrush. Review the trigger in a separate
workflow copy if using that branch; this audit leaves the export unchanged.

### Nodes and ownership

All workflows share `CLIPLoader`, `CLIPTextEncode`, `KSampler`,
`LoraLoaderModelOnly`, `SaveImage`, `UNETLoader`, `VAEDecode`, `VAELoader`.

- **qwen-2512-turbo** additionally uses `ConditioningZeroOut`,
  `EmptySD3LatentImage`, `ModelSamplingAuraFlow`.
- **qwen-2512** additionally uses `EmptySD3LatentImage`, `ModelSamplingAuraFlow`,
  `ComfySwitchNode`, `PrimitiveBoolean`, `PrimitiveFloat`, `PrimitiveInt`.
- **Both Krea graphs** additionally use `ComfySwitchNode`, `ConditioningZeroOut`,
  `EmptyLatentImage`, `PreviewAny`, `PrimitiveBoolean`, `PrimitiveStringMultiline`,
  `ResolutionSelector`, `StringConcatenate`, `TextGenerate`.

These map to recent [ComfyUI core](https://github.com/Comfy-Org/ComfyUI), including
[logic/switches](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_logic.py),
[primitives](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_primitive.py),
[strings](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_string.py),
[resolution](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_resolution.py),
and [text generation](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_textgen.py).
Per-node source mappings are recorded in the manifest. Similar class/display names
in custom repositories do not establish a need to install those repositories.

### Verified download sources

Each file page published a download link, file-specific commit and SHA-256. The
manifest pins these selections and stores the checksum and destination. Rounded
sizes are informational; no exact byte sizes have been inferred from them.

| Asset | ComfyUI destination directory | Publisher/file |
| --- | --- | --- |
| Qwen 2512 FP8 diffusion | `models/diffusion_models/` | [Comfy-Org](https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/blob/main/split_files/diffusion_models/qwen_image_2512_fp8_e4m3fn.safetensors) |
| Qwen 2.5 VL FP8 encoder | `models/text_encoders/` | [Comfy-Org](https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/blob/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors) |
| Qwen Image VAE | `models/vae/` | [Comfy-Org](https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/blob/main/split_files/vae/qwen_image_vae.safetensors) |
| Krea 2 Turbo FP8 | `models/diffusion_models/` | [Comfy-Org](https://huggingface.co/Comfy-Org/Krea-2/blob/main/diffusion_models/krea2_turbo_fp8_scaled.safetensors) |
| Krea 2 Turbo INT8 ConvRot | `models/diffusion_models/` | [Comfy-Org](https://huggingface.co/Comfy-Org/Krea-2/blob/main/diffusion_models/krea2_turbo_int8_convrot.safetensors) |
| Qwen3 VL 4B FP8 encoder | `models/text_encoders/` | [Comfy-Org](https://huggingface.co/Comfy-Org/Krea-2/blob/main/text_encoders/qwen3vl_4b_fp8_scaled.safetensors) |
| Krea darkbrush LoRA | `models/loras/` | [Comfy-Org](https://huggingface.co/Comfy-Org/Krea-2/blob/main/loras/krea2_darkbrush.safetensors) |
| Qwen Lightning four-step FP32 LoRA | `models/loras/` | [LightX2V](https://huggingface.co/lightx2v/Qwen-Image-2512-Lightning/blob/main/Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors) |
| Qwen Turbo two-step BF16 LoRA | `models/loras/` | [Wuli-Art](https://huggingface.co/Wuli-art/Qwen-Image-2512-Turbo-LoRA-2-Steps/blob/1ae1b55d7a66923d67499e1dc1d0b8bd72b0ec65/Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16.safetensors) |

These are explicit publisher selections for reproducibility. The exports contain
filenames, not original download URLs or hashes, so they cannot prove that the
old Pod's bytes match these variants. Existing files must match the manifest's
checksum to pass verification. Sources were inspected through web retrieval;
shell access to Hugging Face was unavailable. No model payload was downloaded.

### Shared dependencies and remaining uncertainty

- Qwen Image VAE: all four graphs, downloaded once.
- Qwen 2512 FP8 diffusion + Qwen 2.5 encoder: both Qwen graphs.
- Qwen3 VL 4B encoder + darkbrush LoRA: both Krea graphs.
- All workflows together: approximately **66.40 GB** of unique model payloads.
- **No model URLs remain unresolved in the selected manifest.** Original asset
  provenance, a known-good template image/ComfyUI commit, Python/Torch/CUDA/kernel
  compatibility, and actual A5000 inference behavior remain unverified. No minimum
  ComfyUI version or known-good core commit is fabricated. Core is inherited from
  the template, so model pinning alone does not pin the complete runtime.
- Live verification checks registered node types, loader model choices and encoder
  families. A small real generation is still needed to establish compatibility,
  offloading behavior and memory usage with 24 GB VRAM.

Inspect again after adding/changing workflows. Unknown node ownership, dynamic
model selectors and unmapped assets are reported and block installation rather
than being skipped silently. UI widget-only exports need API re-export for
reliable provisioning.
