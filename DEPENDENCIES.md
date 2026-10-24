# Workflow sync — 24 October 2026

Latest release added `ltx-2-3-image-to-video.json` from the app, with its stable
ID, wrapper, defaults, parameter markers and complete 51-node graph preserved.
All eight snapshots match the authoritative app byte for byte; no snapshots or
dependency declarations needed pruning. App source hashes are unchanged.
The resulting library has **28 unique models** (about **198.73 GB**) and
**53 node types**, with no custom-node repositories.

Five model sources were verified against publisher API metadata and pinned with
full revisions, exact byte sizes and SHA-256 in `dependencies.json`:

| Destination | Publisher source | Exact bytes |
| --- | --- | ---: |
| `models/checkpoints/ltx-2.3-22b-dev-fp8.safetensors` | [Lightricks/LTX-2.3-fp8](https://huggingface.co/Lightricks/LTX-2.3-fp8/blob/91eda216f820e5ecb3d17dc9fe3b7cdaf56b587d/ltx-2.3-22b-dev-fp8.safetensors) | 29,145,431,166 |
| `models/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors` | [Comfy-Org/ltx-2](https://huggingface.co/Comfy-Org/ltx-2/blob/ccde4ba417d7900669fd56dd292a883cee11ff37/split_files/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors) | 9,447,702,218 |
| `models/latent_upscale_models/ltx-2.3-spatial-upscaler-x2-1.1.safetensors` | [Lightricks/LTX-2.3](https://huggingface.co/Lightricks/LTX-2.3/blob/c1521179de480464f366a98a9d9b2acc4cc097b9/ltx-2.3-spatial-upscaler-x2-1.1.safetensors) | 995,743,560 |
| `models/loras/ltx_2.3_22b_distilled_1.1_lora_dynamic_fro09_avg_rank_111_bf16.safetensors` | [Comfy-Org/ltx-2.3](https://huggingface.co/Comfy-Org/ltx-2.3/blob/f20f3a54378001e5e6d642acc84719cc78addf4b/split_files/loras/ltx_2.3_22b_distilled_1.1_lora_dynamic_fro09_avg_rank_111_bf16.safetensors) | 2,741,024,390 |
| `models/loras/gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors` | [Comfy-Org/ltx-2](https://huggingface.co/Comfy-Org/ltx-2/blob/ccde4ba417d7900669fd56dd292a883cee11ff37/split_files/loras/gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors) | 628,203,616 |

LTX adds about 42.96 GB of unique models. The checkpoint is downloaded once even
though three loaders reference it. The disabled prompt-enhancement branch remains
included. No input image is treated as a downloadable model; `API_INPUT_IMAGE` is
supplied by the local app's image-upload flow at generation time.

Twenty-two additional core-node mappings were inspected at ComfyUI commit
`7cebca52227c63b4180ceed448cbd7ad22903b6d`. The manifest links each source file:
`nodes.py`, `nodes_lt.py`, `nodes_lt_audio.py`, `nodes_lt_upsampler.py`,
`nodes_hunyuan.py`, `nodes_post_processing.py`, `nodes_math.py`, `nodes_video.py`
and `nodes_textgen.py`. This verifies ownership, not a tested minimum runtime.
The provisioning scanner now recognizes node-specific text-encoder and latent
upscaler filenames, rejects unresolved or incorrect upscaler links, and checks
both loader dropdowns during live model verification. No core/runtime upgrade
was performed.

The video workflow retains both sampling stages, audio, x2 upscaling, LoRA
strengths, the disabled prompt enhancer and the image-conditioning switch.
Defaults are 1024-square final dimensions, 25 fps and approximately 10 seconds
(249 shared audio/video frames on the `8n+1` grid). Final dimensions use /64
steps; both noise stages and the optional enhancer use the app's generation seed.
The local helper supports the input image and video result; the image extension
bridge excludes video workflows. No live Pod/GPU generation or model payload
download was performed, so memory, kernels and image/video quality remain untested.

Release checks passed: full sync/prune check, all-workflow installation dry run,
17 provisioning tests (including two new LTX loader tests), 20 sync tests and
four offline LTX parameter-substitution trials. Earlier verification dates are
preserved; new model source checks are dated 2026-10-24.

## Earlier sync — MOSS, 24 October 2026

Latest sync added `moss-image-sft-4-step.json` unchanged from the app. The other
six snapshots were unchanged; no snapshot deletions or dependency pruning were
needed. All seven snapshots match the app byte for byte and source hashes are
unchanged. The library now has **23 unique models** (about **155.77 GB**) and
**31 node types**, with no custom-node repositories.

MOSS adds three pinned models with publisher SHA-256 and exact byte sizes:

| Asset | Publisher revision | Size |
| --- | --- | ---: |
| SFT BF16 checkpoint | [Comfy-Org/MOSS-Image](https://huggingface.co/Comfy-Org/MOSS-Image/blob/24147db865fcdc207270f844777587223fed8d6e/diffusion_models/moss_image_sft_bf16.safetensors) | 10,164,655,808 bytes |
| Qwen3.5 9B INT8 ConvRot encoder | [Comfy-Org/MOSS-Image](https://huggingface.co/Comfy-Org/MOSS-Image/blob/24147db865fcdc207270f844777587223fed8d6e/text_encoders/qwen3.5_9b_int8_convrot.safetensors) | 9,748,121,532 bytes |
| Four-step v2.0 LoRA | [akhaliq/MOSS-Image-SFT-4-steps](https://huggingface.co/akhaliq/MOSS-Image-SFT-4-steps/blob/2ded95c37a029360245926fe72e475e30039bbfb/moss_image_sft_4step_v2.0.safetensors) | 1,189,176,752 bytes |

Publisher API metadata supplied the pinned revisions, sizes and SHA-256 values
recorded in `dependencies.json`; no model payloads were downloaded. The encoder
selection is the Comfy-Org variant, not another publisher's identically named
file. MOSS reuses the existing `flux2-vae.safetensors` declaration. The graph's
LoRA strength 1, Euler/simple sampler, four steps, CFG 1 and defaults are unchanged.
The upstream [CLIP loader](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy/sd.py)
was inspected for `moss_image` selection. Its node types already have reviewed core
mappings. These checks do not establish GPU, memory or runtime compatibility.

MOSS sync validation passed: full `--all --prune --check`, all-workflow provisioning
dry run, 20 sync tests and 15 provisioning tests. No Pod installation, live schema
checks or GPU generation were performed; earlier verification dates are preserved.

## Earlier sync — 24 October 2026

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
