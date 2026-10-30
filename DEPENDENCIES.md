# Krea 2 Turbo FP8 Realism LoRA selective sync — 30 October 2026

Added `krea-2-turbo-fp8-realism-lora.json`, ID
`150d5fa5a18c49a8bd544c2db0eba96b`. This uses the shared Krea Turbo FP8
checkpoint, FP8 text encoder and Qwen VAE, with the realism LoRA enabled at
0.8, eight Euler/simple steps, CFG 1 and prompt refinement disabled. Its
square selector resolves to 1024 × 1024; the app exposes width and height.
The distinct Krea 2 Realism checkpoint workflow is retained.

The LoRA is pinned to [gokaygokay/Krea-2-Realism-LoRA](https://huggingface.co/gokaygokay/Krea-2-Realism-LoRA),
revision `32f0436ac10e985134364e7555898c9f121a46ce`, SHA-256
`6c38a7934c54a56e0f67753660a4500a094d6dce28a0ee4a0d1dc9f4975d32d2`,
469,288,512 bytes. The installed Pod file was checksum-verified earlier;
this graph has not been GPU-tested in this sync.

# Krea 2 Turbo FP8 4-Step LoRA selective sync — 30 October 2026

Added `krea-2-turbo-fp8-4-step-lora.json`, ID
`f3c446383d81447799b5d3519b39d5a3`, retaining four Euler/simple steps,
CFG 1 and zeroed negative conditioning. The FP8 Turbo diffusion model, BF16
Qwen3 VL encoder and Qwen VAE are shared with existing workflows.

The new ComfyUI-format adapter is pinned to publisher revision
`9adb4934b88a2ea35aac4e443a668fe0dffbc190`, SHA-256
`7590b2d2772f45d7b1252124c63918b1b807e93fbf9eab20546fa7233b4dc482`
and size 438,140,968 bytes, from
[lvladikov/Krea2-Turbo-Distill-4step-LoRA](https://huggingface.co/lvladikov/Krea2-Turbo-Distill-4step-LoRA).
The publisher describes this as a four-step Turbo adapter. This particular graph
and FP8 combination have not been GPU-tested in this sync.

# Krea 2 Turbo BF16 3-Step LoRA selective sync — 29 October 2026

Added `krea-2-turbo-bf16-3-step-lora.json` from the app with ID
`230b2790938a420db70fb932eb3cf0f9`. The graph retains three Euler/simple
steps, CFG 1, zeroed negative conditioning and the original 1024-square defaults.
The publisher identifies the supplied BF16 model and ComfyUI-format rank-64
adapter for this workflow; the adapter is a checkpoint from ongoing training.

Two newly declared files are pinned to publisher repository revisions and SHA-256
from Hugging Face metadata; the BF16 text encoder and Qwen VAE are shared:

- `models/diffusion_models/krea2_turbo_bf16.safetensors`: Comfy-Org/Krea-2,
  revision `1171f4dc7e325bf3734586942e737872506c73e1`, SHA-256
  `78bbf8f4165eda19cea3cb06c78089221932a39e2eed8af9da741f942c47ffb3`, 26,283,332,608 bytes.
- `models/loras/krea2_turbo_3step_rank_64_lora_comfyui.safetensors`:
  lvladikov/Krea2-Turbo-Distill-3step-LoRA, revision
  `4e24ec56cba92ba735b72d2a78de35281d017a0d`, SHA-256
  `619e8a2a7491b2b80a822fac65339a20704d79fd416a262385ac80ca6c5f5a2f`, 438,141,072 bytes.

No model payloads were downloaded; GPU execution and memory use are unverified.

# Krea 2 Realism FP8: editable steps — 29 October 2026

`krea-2-realism-fp8.json` now exposes its existing KSampler steps through
`API_STEPS`, default 6. The workflow ID, model, conditioning, sampler, CFG and
dimension defaults are unchanged. Prompt Fusion uses its existing generic
integer control; the queued snapshot and result metadata retain the chosen
count. The app and provision snapshots match; no dependency changes were made.
Offline checks verify the six-step default, eight-step submission through the
memory-only output path, captured metadata, snapshot isolation and invalid input.
Eight parameter-substitution trials, sync and provisioning tests and a selective
dry run also pass. No GPU comparison has been performed; try six and eight with
the same dimensions and similar prompts when a prepared Pod is available.

# MOSS Image SFT 4 Step: editable steps — 28 October 2026

The existing `moss-image-sft-4-step.json` sampler now exposes `API_STEPS` with
its original default of 4. Prompt Fusion's existing generic integer control
passes the value through the bridge; queued snapshots and generated metadata
retain it. No model, CFG, sampler, image dimensions, or other workflow changed.
The selected app/provision snapshots match and use existing dependencies.

Eight offline substitutions and a bridge test check default 4, chosen 6, actual
mocked ComfyUI submission, captured metadata, workflow edit isolation and invalid
values. No live GPU comparison was performed. The selected Pod was unreachable
when checked; provision and verify the workflow before using it, refresh Prompt
Fusion's workflow list, and compare 4 and 6 at the same dimensions and prompts.
The preference for this workflow is currently disabled; enable it in session
setup after the corrected provisioning snapshot is published. Steps affect time
and quality; author suggestions at higher resolution are starting points rather
than verified results on this Pod. The generic validation currently accepts
integer steps from 1 to 10000.

# RapidMOSS native-loader repair — 28 October 2026

Real user jobs `a599dd41-a59c-4772-8bfe-93c595df0b7e` and
`0866cfc6-1cad-4c18-8426-a369f65db748` produced noisy images with the previous
BF16 graph. The Pod log reported missing separate `layers.*.proj.{q,k,v}.weight`
and unexpected fused `layers.*.proj.qkv.weight` for the Comfy-Org BF16 checkpoint
under `MOSSImageUNETLoader`, leaving core model weights unloaded. This is the
concrete cause addressed, not a claim based on image appearance alone.

The app and selected provisioning snapshot now use ComfyUI's native `UNETLoader`
for the same BF16 checkpoint, native `CLIPLoader` with `moss_image` and Comfy-Org
INT8 encoder, shared `flux2-vae.safetensors`, and `BasicGuider` as the RapidMOSS
author recommends. The native adapter detects `comfy.ldm.moss_image.model.MOSSImage`
and handles fused QKV. The original prompt, dimensions, output, adapter, four
steps, and strength remain unchanged. Prior custom-loader graph is preserved in
`../workflow-imports/rapid-moss-sft-bf16-custom-loader.json`.

Source review, live Pod log diagnosis, eight offline substitutions, link checks,
selective app/provision parity, 20 sync tests, 22 provisioning tests, 12 native
batch tests and installation dry runs passed. These do not prove visual quality
or GPU inference. After supplying the missing native encoder and VAE to the Pod,
refresh Prompt Fusion workflows and test a single image; check for no missing or
unexpected model weights in ComfyUI logs and record the output and prompt ID.
Native batch output quality is unverified. Publishing the corrected provisioning
snapshot remains a separate action; selective sync retains unrelated dependencies.

# Rapid MOSS BF16 correction — 28 October 2026

The saved Rapid MOSS SFT 4 Step graph now selects the shared Comfy-Org
`moss_image_sft_bf16.safetensors` instead of the supplied nif0 INT8 diffusion
file. The [adapter author](https://huggingface.co/darask0/MOSS-Image_4-step_adapter_lora/blob/main/comfyui/rapid-moss/README.md)
recommends SFT BF16 and does not validate INT8 diffusion models. The existing
MOSSImageUNETLoader, quantized text encoder, VAE, adapter and four-step sampling
remain as supplied. ScheduledCFGGuidance stays at CFG 1; the author recommends
BasicGuider, so this specific guidance path still requires a live comparison.
The selective sync retains the unused INT8 manifest record without pruning.
The six required model/adapter files total ~16.95 GB; the BF16 model is shared
with MOSS Image SFT 4 Step. GPU execution, batching and RAM/VRAM use have not
been verified. The earlier Pod inspection established loader filename choices,
not actual BF16 inference. Provision or verify the corrected selection on a
prepared Pod and run a single-image smoke test when authorized. This revision is
local until published. Earlier 27 October details describe the original graph.

# Rapid MOSS SFT 4 Step — 27 October 2026

Selective sync adds `rapid-moss-sft-4-step.json` (ID
`4a76a6a398fc453489c33b21acb6c064`). It preserves the supplied RapidMOSS
adapter, four steps, ScheduledCFGGuidance and zeroed negative conditioning.
The positive prompt and dimensions are editable, defaulting to the supplied text
and 1328 × 1024; the helper supplies fresh seeds. The malformed API export's three
missing class names and UNKNOWN inputs were resolved using the connected Pod's
actual `/object_info` schemas. Original: `../workflow-imports/rapid-moss-sft.original.json`.

The manifest pins the six required model/adapter files (~12.20 GB) and the three
custom node packages to the versions installed on the current Pod. The adapter
files are explicit extra models because the graph selects an adapter directory,
not its internal files. RapidMOSS and MOSS-Image are published as repository
subdirectories: the installer now downloads and checks their individually pinned
source files. KJNodes remains a pinned Git checkout. Existing files with mismatched
checksums are refused rather than overwritten. Installed model/adapter files and
node classes were verified on the connected Pod; the parameterized graph was also
checked against its live schema and dropdown choices. Offline substitution,
selective sync/check, installer and sync tests and dry runs passed.

GPU generation, native batching, output quality and performance remain untested.
The adapter author recommends BasicGuider; the supplied ScheduledCFGGuidance
settings are preserved pending an actual test. Start with one image. When live
inference is authorized, check the queue, submit a small generation through the
normal helper, and record prompt ID, exact seed, output and errors; do not silently
retry uncertain jobs. This sync is local; publish the provisioning repository before
using it on a replacement Pod. The new workflow is disabled by default for automatic
provisioning; explicitly select it when required.

# MiniMax H3 Turbo Text to Image — 27 October 2026

Selective sync adds `minimax-h3-turbo-text-to-image.json`, ID
`6017bfa8dd9b41208fca8d6d594fac40`, with four files from
[Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3/tree/e5eb578a89295337b8ff433a035929ce0279e0b6),
pinned by revision and publisher file-page SHA-256 in the manifest (~43.87 GB).
BasicScheduler and ModelAttentionBackend are mapped to their upstream core source.
The graph preserves the supplied sampler, model, VAE and LoRA. Prompt and dimensions
are editable; selector defaults resolve to 1296 × 728; seeds are generated by the helper.
There is no negative prompt path. Source graph is preserved in the app's
`workflow-originals/minimax-h3-t2i.json`.

Offline parameter substitution, selective sync/check, provisioning tests and dry runs
pass. **Generation is not verified:** the supplied graph passes the sampled
`EmptyLatentImage` output to `LTXVSeparateAVLatent`, whose upstream implementation
expects two streams. Confirm that this particular MiniMax sampler produces a joint
AV latent before relying on it; if not, the graph needs an author-confirmed correction.
Do not assume native batching works through that separator. No model downloads,
Pod installation, helper restart or GPU test occurred. When a prepared Pod and live
validation are authorized, run `python3 provision.py --verify --workflow
minimax-h3-turbo-text-to-image` on the Pod, inspect its node schemas and model choices,
then submit one small image through the normal helper and verify its output and seed;
record failure and prompt ID without silently retrying. Installation, if needed, is
`python3 provision.py --install --workflow minimax-h3-turbo-text-to-image` on the Pod.

# Krea 2 Realism FP8 selective sync — 26 October 2026

Added `krea-2-realism-fp8.json` unchanged from the new app entry, ID
`28989ad1e1db4dc083cf9ec2678355a8`. It copies the existing Krea 2 Turbo graph
and swaps the diffusion file, changes eight steps to six, and gives output its
own prefix. Euler/simple, CFG 1, shared encoder/VAE, zeroed negative conditioning
and disabled optional Darkbrush/prompt-enhancement branches remain intact.
The new wrapper defaults to 1152 × 1792 and a natural-language photo prompt,
following the publisher's approximately 2MP/six-step recommendation.

One new pinned file:

- Destination: `models/diffusion_models/Krea2Realism_V1.safetensors`.
- Publisher: [RudySen/Krea2-Realism-Checkpoint](https://huggingface.co/RudySen/Krea2-Realism-Checkpoint/blob/0ee8fad5208edb4cd7efd9f1f3a253a37104557a/Krea2Realism_V1.safetensors).
- Revision: `0ee8fad5208edb4cd7efd9f1f3a253a37104557a`.
- SHA-256: `cc0d6a265cba48d9f4785ee00540695512816127f1d6de47d226a7aa15ca1787`.
- Size: 13,141,769,680 bytes; checked against publisher API metadata.

This selects the original FP8 release. W4A8 and INT8 ConvRot variants are not
added. No new core ownership declarations or custom nodes are needed. The new
workflow's four declared assets total ~19.11 GB; ~13.14 GB is additional when
the shared files are present. The library now has 14 workflows and 36 model
files (~272.43 GB). Prior workflow and dependency entries are unchanged.

Eight offline substitutions, graph/link review, selective preview/apply/check,
20 sync tests, 18 provisioning tests and selected/all install dry runs pass.
All 26 previous app/provision workflow files retain their hashes, and the new
snapshots match byte for byte. Publication, actual model installation and GPU
validation remain pending. No model payload downloaded or service restarted.

# LTX Video 2B distilled selective sync — 26 October 2026

Added `ltx-video-2b-0-9-8-distilled-image-to-video.json` from the app, ID
`f57f93030a584707b6884ff43164131f`, as an additional 18-node native workflow.
One eight-step Euler pass uses the published distilled sigma sequence and CFG 1
through BasicGuider. Defaults are 768 × 512, about 3 seconds / 24 FPS (73 frames),
image strength 0.8, and silent H.264 MP4. Upload, dimension, timing and silent
bridge handling use existing helper contracts without code changes.

Two new sources were checked against publisher API metadata and pinned:

| Destination | Revision | SHA-256 | Bytes |
| --- | --- | --- | ---: |
| `models/checkpoints/ltxv-2b-0.9.8-distilled.safetensors` | `8984fa25007f376c1a299016d0957a37a2f797bb` | `76aa8c4786af752fa6f951947129d5290c3c6c0b2fadcadea6b5e114ae2cad8f` | 6,340,744,492 |
| `models/text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors` | `934251d1e6168bcb45a069abc5bd5cdd5f8fea00` | `a498f0485dc9536735258018417c3fd7758dc3bccc0a645feaa472b34955557a` | 5,157,348,688 |

Publisher repositories are `Lightricks/LTX-Video` and
`Comfy-Org/stable-diffusion-3.5`. The checkpoint includes its video VAE; no
separate VAE, audio, upscaler or custom-node package is needed. All graph node
types already have reviewed core ownership declarations. This entry uses the
regular checkpoint and scaled FP8 T5 encoder with `CLIPLoader` type `ltxv`.
It is an authored single-pass graph, not an API export of the publisher's
multiscale custom-node example. That UI example and the 2B config are preserved
in the shared `examples/workflows/` folder for comparison.

The library now contains 13 workflows and 35 unique model files (~259.28 GB).
The new entry adds ~11.50 GB. All prior graph hashes and dependency entries are
unchanged. Six parameter substitution trials and focused new-graph checks pass,
including full 64-bit seeds, input routing, silent video adaptation, dimension
validation and the 8n+1 frame grid. Selective preview/apply/check, selected/all
install dry runs and 54 sync/provision/media/video-bridge logic tests pass.
One existing ASGI video endpoint test times out, including when run by itself
with its original LTX 2.3 fixture; it does not use the new graph. No helper code
was changed. Publication, Pod model installation and live GPU validation remain
pending; no model payload was downloaded and no service restarted.

# MOSS Base DMD selective sync — 26 October 2026

Added `moss-image-base-dmd-8-step.json` from the app with stable ID
`374aaa27a3e049908c8e4cc4328393b6`. Based on the existing MOSS SFT four-step
graph, this entry switches to MOSS Base BF16, lodestones' model-card-recommended
`lora.safetensors`, eight Euler/simple steps and its own output prefix. CFG 1,
LoRA strength 1, encoder/VAE, parameters, defaults and output wiring are retained.
Native MOSS supplies shift 5 and multiplier 1. The original SFT entry is unchanged.

Publisher API metadata verified these new exact files:

| Installed file | Revision | SHA-256 | Bytes |
| --- | --- | --- | ---: |
| `moss_image_base_bf16.safetensors` | `530a4c94f92c35ef6818b1b035a983fe9dcf5f54` | `cacd158728a1fb9e57c408a922b54752ec71fceb566b3821269927964e62b41f` | 10,164,655,808 |
| `moss_image_base_dmd_8step.safetensors` (source `lora.safetensors`) | `da05cb3b52899179e2bb5f7efe1058fefcbae21b` | `f0e6cd07f222dfaea798afe3b796e2c2995cadfd44ad56e02ca616f0467aec28` | 1,189,176,800 |

Sources: [Comfy-Org MOSS Base](https://huggingface.co/Comfy-Org/MOSS-Image/blob/530a4c94f92c35ef6818b1b035a983fe9dcf5f54/diffusion_models/moss_image_base_bf16.safetensors)
and [lodestones DMD adapter](https://huggingface.co/lodestones/MOSS-Image-Base-8-steps-dmd/blob/da05cb3b52899179e2bb5f7efe1058fefcbae21b/lora.safetensors).
The later DMD2 adapter and experimental data-space sampler are not selected.
ComfyUI native sampling and MOSS fused-qkv LoRA mapping were inspected in
`comfy/supported_models.py` and `comfy/lora.py` at revision
`cdf272f3514353aab04dc2d9fceef57a260dc156`; no new node ownership declarations
or custom packages are required.

The library now has 12 workflows and 33 unique models (~247.79 GB). The new
workflow's four dependencies total ~21.44 GB; only ~11.35 GB is additional when
the shared encoder/VAE are present. Previous model entries and dates are preserved.

Eight offline substitution trials, selective sync preview/apply/check, 20 sync
tests, 18 provisioning tests and selected install dry run passed. Existing
workflow hashes are unchanged. No model payload download, publication, Pod
installation/restart or GPU generation was performed. Live LoRA application,
runtime precision, memory and output quality checks remain pending.

# LTX single-stage selective sync — 26 October 2026

Added `ltx-2-3-distilled-fp8-single-stage-image-to-video.json` unchanged from the
app library, preserving ID `880ae5f372f74e6e857684d2f8e758e3` and the 37-node
graph. It uses one eight-step Euler/CFG-1 sampler at final resolution; no latent
upscaler, half-size stage or refinement sampler. Defaults are 512 square,
2 seconds and 25 FPS; source conditioning, audio and optional disabled Gemma
prompt enhancement remain. Both prior LTX workflows are retained.

The new entry shares three already-pinned models (about 39.61 GB): distilled
FP8 checkpoint, Gemma FP4 encoder and the disabled optional Gemma LoRA. It adds
no unique models, sources, node ownership mappings or custom-node packages.
The library now has 11 workflows, 31 unique models and the existing panorama
add-on. Original dependency declarations and verification dates are preserved.

Selective preview/apply/check, 20 sync tests, 18 provisioning tests, and both
selected/all-workflow installation dry runs passed. All 11 snapshots match the
app, and all ten prior library graphs retain their hashes. No model payloads downloaded, Pod services restarted or GPU jobs submitted.
Publication and actual model installation remain separate from this local sync.

# LTX distilled selective sync — 25 October 2026

Added `ltx-2-3-distilled-fp8-image-to-video.json` byte for byte from the local app
library, preserving ID `9aaad34009854cafa70f41435d11c560`, parameters, default
settings and the complete 50-node graph. The original LTX workflow and all eight
other snapshots/dependency declarations are retained. No pruning was requested.

The new workflow loads the official v1.0 distilled FP8 checkpoint directly;
it removes the distillation LoRA only from its own graph. Euler/CFG 1 uses the
official eight-step base and three-step refinement sigma schedules. Shared
Gemma FP4 encoding, audio/video VAEs, x2 latent upscaling, the disabled optional
Gemma enhancer and its LoRA, source image handling and output audio connection
are preserved. No new core-node mappings or custom packages are needed.

The single additional model is
`models/checkpoints/ltx-2.3-22b-distilled-fp8.safetensors`:

- Publisher: [Lightricks/LTX-2.3-fp8](https://huggingface.co/Lightricks/LTX-2.3-fp8/blob/91eda216f820e5ecb3d17dc9fe3b7cdaf56b587d/ltx-2.3-22b-distilled-fp8.safetensors).
- Revision: `91eda216f820e5ecb3d17dc9fe3b7cdaf56b587d`.
- SHA-256: `d9646b6f2d5c42d337b23671634c43bfeece6989644f51b4a3aa088465ccd3b2`.
- Exact size: 29,531,884,062 bytes, verified with publisher revision API metadata.

The library now has **10 workflows**, **31 unique models** (about **236.43 GB**)
and the existing panorama add-on package. The distilled workflow alone
references four model files totalling about 40.60 GB; existing valid shared files
are reused. Earlier verification dates and original workflow dependencies stay
unchanged.

Selective preview, apply and check passed; the selected install dry run resolves
all four models and existing core-node ownership. All 20 sync tests, 18
provisioning tests and the all-workflow install dry run passed. All ten snapshots
match the app; all nine prior snapshots and dependency entries are unchanged.
No model payloads downloaded,
Pod installation/restart or GPU generation performed. Git publication and Pod
installation are separate from this local repository sync.

# Workflow sync — 25 October 2026

Added `qwen-image-2-1-360-panorama.json` unchanged from the app: source-image input,
editable prompt and dimensions, positive-only `BasicGuider`, fixed eight-step
Euler sigma schedule, Turbo LoRA strength 1, and 2880 × 1440 defaults. The malformed
optional preview node from the original API export remains omitted; the saved
PNG path is intact. Other eight snapshots are unchanged. All nine match the app
byte for byte, with source hashes unchanged and no stale snapshots to prune.

The library references **30 unique model files** (about **206.90 GB**) and
**54 graph node types**, plus one explicitly requested native preview add-on.
Two new models add about 8.17 GB; the encoder and VAE are shared:

| Destination | Pinned publisher source | Exact bytes |
| --- | --- | ---: |
| `models/diffusion_models/qwen_image_2.1_int8_convrot.safetensors` | [Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/blob/0217efd1d9c9452e84f6448903d6e21bfa171ffd/diffusion_models/qwen_image_2.1_int8_convrot.safetensors) | 7,256,783,064 |
| `models/loras/qwen_image_2.1_turbo_lora_avg_rank_178_bf16.safetensors` | [Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/blob/0217efd1d9c9452e84f6448903d6e21bfa171ffd/loras/qwen_image_2.1_turbo_lora_avg_rank_178_bf16.safetensors) | 913,314,512 |

Publisher API metadata supplied full revisions, SHA-256 and exact sizes recorded
in the manifest. New source checks are dated 2026-10-25; earlier verification
dates are preserved. `BasicGuider` was verified in ComfyUI core source at
`7cebca52227c63b4180ceed448cbd7ad22903b6d`.

At the user's request, the workflow's explicit `custom_nodes` override includes
[nomadoor/ComfyUI-Panorama-Stickers](https://github.com/nomadoor/ComfyUI-Panorama-Stickers/tree/ef900eb1a0e5b4b104a562ba91ae744d5f22608c),
pinned to full commit `ef900eb1a0e5b4b104a562ba91ae744d5f22608c` (version 1.5.2).
Its entrypoint exports `PanoramaStickers`, `PanoramaCutout`, `PanoramaPreview` and
`PanoramaSeamPrep` and serves bundled assets from `web`. The reviewed repository
has no `requirements.txt` or pyproject dependency list; its Python nodes use
ComfyUI's NumPy/Pillow/Torch environment. PyAV is optional at import time for
video preview. The exact checkout includes the frontend; no npm build is added.

The add-on is for interactive viewing in native ComfyUI, not required by the
saved API generation graph. To view a result, connect **Load Image** to
**Panorama Preview** with coverage **360**. The local app still displays a flat
panorama. The per-workflow override keeps this user-requested viewer in future
pruning even though no API node references it. Installation and verification now
check that declared add-on classes register with ComfyUI, rather than accepting
only a successful checkout/stamp.

Validation passed: full sync/prune check, all-workflow install dry run, 18
provisioning tests (including a test that a missing explicit preview node fails
live verification), 20 sync tests and eight offline substitution trials. No
models or custom packages were installed, no Pod was changed, and no GPU or
interactive browser verification was performed during this local sync.

## Previous sync — LTX, 24 October 2026

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
