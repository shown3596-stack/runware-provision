# Disposable Runpod ComfyUI setup

Provision only the models needed by an existing workflow, on a Pod that already
has ComfyUI. `provision.py` uses Python 3.10+ standard library and `curl`; `git`
and pip are needed only for custom nodes. This is a standalone provisioning repository. It includes unchanged snapshots of
the workflows audited from `comfyui-api-poc`; the original app and workflow
library remain in that separate repository.

## Krea 2 Turbo FP8 Realism LoRA

`krea-2-turbo-fp8-realism-lora` uses Turbo FP8 with a separate realism
adapter at strength 0.8. It differs from the Krea 2 Realism FP8 checkpoint
workflow. See the dependency report for its pinned source and settings.

## Krea 2 Turbo FP8 4-Step LoRA

`krea-2-turbo-fp8-4-step-lora` uses the FP8 Turbo model and a four-step
adapter, with the BF16 Qwen3 VL encoder and Qwen VAE. See the dependency
report for pinned sources. GPU execution has not been verified in this sync.

## Krea 2 Turbo BF16 3-Step LoRA

The `krea-2-turbo-bf16-3-step-lora` workflow uses the BF16 Krea Turbo
model and a three-step rank-64 adapter. It shares the Qwen3 VL BF16 text
encoder and Qwen VAE with existing workflows. See the dependency report for
pinned sources and limitations; GPU execution has not been verified.

## MiniMax H3 image workflow

`minimax-h3-turbo-text-to-image` is available for selective provisioning (~43.87 GB
of model files). Its supplied latent separation path has not been verified on a GPU;
see [the dependency report](DEPENDENCIES.md) before using it. At that sync the library contained 15 workflows and 40 unique model files (~316.30 GB).

## Rapid MOSS SFT 4 Step

`rapid-moss-sft-4-step` uses native MOSS loading, BF16 SFT, the Comfy-Org
INT8 text encoder, FLUX.2 VAE and RapidMOSS adapter. Its model files are shared
with MOSS Image SFT 4 Step except for the adapter. The native-loader repair has
not yet been GPU-tested; see the dependency report before use. See [the dependency report](DEPENDENCIES.md).
The installer supports individually checksum-pinned source files for custom nodes
published as repository subdirectories.

## Prompt Fusion output handling

Provisioning installs the bundled `prompt_fusion_memory` node and verifies its
image and video classes after ComfyUI restarts. Prompt Fusion can then retrieve
outputs from Pod RAM without generated files in the ComfyUI output directory.
Direct ComfyUI workflows retain their own save behavior. This RAM output path
has offline coverage but has not yet been smoke-tested on a real Pod/GPU.

## Inspect locally before renting a GPU

```bash
python3 provision.py --list
python3 provision.py --inspect
python3 provision.py --inspect --workflow qwen-2512.json
python3 provision.py --install --workflow qwen-2512.json --dry-run
```

Use `python` instead if that is your Python 3 command. Names are discovered from
`workflows/**/*.json`, including the app's `{name, workflow}` wrapper; exact names,
file stems and generated slugs work. Current app snapshots are `qwen-2512.json`,
`krea-2-turbo-fp8.json`, `mage-flow-turbo.json`, `ernie-image-turbo.json`,
`qwen-image-2-1-turbo.json`, `z-image-turbo.json`, `moss-image-sft-4-step.json`,
`moss-image-base-dmd-8-step.json`,
`ltx-2-3-image-to-video.json`, `ltx-2-3-distilled-fp8-image-to-video.json`,
`ltx-2-3-distilled-fp8-single-stage-image-to-video.json`, and
`qwen-image-2-1-360-panorama.json`, plus
`ltx-video-2b-0-9-8-distilled-image-to-video.json` and `krea-2-realism-fp8.json`.
Full app-to-provision sync includes pruning. `--all` selects these fourteen workflows:
**36 unique model files**, about **272.43 GB**, including disabled prompt-enhancement
branches, and one pinned custom-node package for the native panorama viewer.
**Krea 2 Realism FP8** adds RudySen's original 13.14 GB FP8 checkpoint and shares
the existing Krea encoder/VAE and disabled optional Darkbrush LoRA. It defaults
to six Euler/simple steps, CFG 1 and 1152 × 1792. Install with
`--workflow krea-2-realism-fp8`. Its original Krea 2 Turbo counterpart remains
available; GPU execution and memory use have not been verified here.
Mage requires core support for `TextEncodeMageFlowEdit`, `SaveImageAdvanced`, and
the `mage` encoder family; source ownership is verified, live execution is not.
Ernie, Qwen Image 2.1 and Z Image also need matching core model/encoder support;
the reviewed core nodes include `EmptyFlux2LatentImage`, `TextEncodeQwenImage21`,
`QwenImage21Cache`, `ManualSigmas`, and `StringReplace`. Live node/model checks
and GPU smoke generation are still required for the chosen Pod template.
MOSS uses the Comfy-Org SFT BF16 checkpoint and Qwen3.5 9B INT8 ConvRot encoder,
akhaliq's frozen four-step v2.0 LoRA, and the shared FLUX.2 VAE. Its template must
support the `moss_image` encoder family; live MOSS execution remains unverified.
The additional **MOSS Image Base DMD 8 Step** workflow loads Comfy-Org's Base
BF16 checkpoint and lodestones' recommended `lora.safetensors` at strength 1,
using eight Euler/simple steps, CFG 1 and native MOSS shift 5. It shares the
encoder and VAE with SFT; its two new pinned files add about 11.35 GB. The
adapter is installed as `moss_image_base_dmd_8step.safetensors`. Select it with
`--workflow moss-image-base-dmd-8-step`. Source and graph checks passed; live
LoRA application, GPU memory and output quality remain unverified.
**LTX Video 2B 0.9.8 Distilled Image to Video** is a separate, silent eight-step
single-pass option for quick animation tests. It uses the regular 2B checkpoint
(bundled VAE) and scaled FP8 T5XXL encoder: two pinned downloads totaling about
11.50 GB, with no additional custom nodes. Defaults are 768 × 512, approximately
3 seconds and 24 FPS. Install with
`--workflow ltx-video-2b-0-9-8-distilled-image-to-video`. GPU speed and output
quality are not yet verified; existing LTX 2.3 entries are retained.
LTX 2.3 uses its full FP8 checkpoint (shared by the video/audio VAEs and AV text
encoder), Gemma FP4 text encoder, x2 latent upscaler, distilled LoRA and optional
Gemma prompt-enhancement LoRA. All five files are pinned with SHA-256 and exact
sizes. The dependency scanner recognizes the LTX loader fields and checks the
upsampler's model connection against its loader instead of treating it as a
filename. Use the updated local helper app to select/upload the starting image
and display/download the video; the extension bridge currently stores images only.
Provisioning does not supply an example image or substitute `API_INPUT_IMAGE`.
The separate **LTX 2.3 Distilled FP8 Image to Video** workflow uses the official
v1.0 distilled FP8 checkpoint directly, with no distillation LoRA, eight base
steps and three x2-upscale refinement steps at CFG 1. Its 29.532 GB checkpoint is
pinned with SHA-256 and exact size; the encoder, upscaler and optional Gemma LoRA
are shared with the existing LTX workflow. The original LTX workflow is retained. The additional
**LTX 2.3 Distilled FP8 Single Stage Image to Video** workflow samples directly
at output resolution in eight steps, defaulting to 512 square / 2 seconds /
25 FPS. It shares the distilled checkpoint, encoder and optional Gemma LoRA;
its three model dependencies exclude the latent upscaler. Install it with
`--workflow ltx-2-3-distilled-fp8-single-stage-image-to-video`.
Select just this workflow for installation/verification:

```bash
python3 provision.py --install --workflow ltx-2-3-distilled-fp8-image-to-video
python3 provision.py --verify --workflow ltx-2-3-distilled-fp8-image-to-video
```

The Qwen 360 workflow defaults to a 2880 × 1440 equirectangular image; keep its
2:1 output ratio when editing dimensions. It shares the Qwen 2.1 encoder/VAE but
uses the base INT8 ConvRot diffusion model plus the separate Turbo LoRA.
`ComfyUI-Panorama-Stickers` is explicitly included for this workflow at commit
`ef900eb1a0e5b4b104a562ba91ae744d5f22608c`. Its bundled frontend is installed with
the checkout; no Node build or additional pip requirements are declared upstream.
Future install/verify checks require its four registered node classes even though
the app's API graph contains only the saved-image path. For an interactive native
ComfyUI view, load the generated PNG with **Load Image**, connect it to
**Panorama Preview**, and select coverage **360**. This does not add an interactive
viewer to the separate local app, which displays the flat panorama.
There is no `flux-klein` export.
See [the dependency report](DEPENDENCIES.md) and [shared manifest](dependencies.json).

The bundled workflow snapshots make this repository usable on its own. To inspect
the original app's current library instead (from this repository's directory):

```bash
python3 provision.py --list --workflows-dir ../comfyui-api-poc/workflows
python3 provision.py --inspect --workflows-dir ../comfyui-api-poc/workflows
```

The same option works with `--install`, `--verify`, and `--dry-run`. Paths are
relative to your current working directory; the default bundled `workflows/` is
resolved relative to the script. Newly added dependencies need review in this
repository's manifest. The app is the testing area and source of truth; it owns
workflow syncing and dependency updates. This repository receives the saved
workflow snapshots and reviewed `dependencies.json`, then installs/verifies them
on Pods. See the app's README for the sync command and the shared `runpod`
folder's `skills/update-comfy-provisioning/SKILL.md` for the agent workflow.

Full app-authoritative sync uses `sync_provision.py --all --prune` (preview), then
`--apply` and `--check` with the same flags. It removes snapshots deleted from the
app and dependency declarations no remaining graph/override references, preserving
shared models and node packages. Selective sync and sync without `--prune` retain
other snapshots. A Pod receives the cleaned selection after this repository is published and
its checkout is pulled during session startup. Repository pruning
does not delete existing model files, custom-node directories or packages on a Pod.


## Fresh Pod: deploy, clone, provision

1. Deploy an RTX A5000 24 GB Pod with your existing ComfyUI template and SSH key.
   Choose ephemeral container disk, no network volume, and zero volume disk if
   the template allows it. Budget **at least 50 GB free beyond the template** for
   Qwen or **30 GB** for one Krea workflow, plus outputs; all workflows need about
   237 GB of unique models, so allow at least 260 GB free. Ephemeral disk can still
   have a charge while the Pod exists. Record the template image digest and
   ComfyUI commit for a setup that you have actually smoke-tested.
2. Connect using the Pod's **direct SSH TCP** command from Runpod's Connect panel.
   The template must already have SSH available. This tool does not change ports,
   networking, security settings, or the installed ComfyUI version.
3. On the Pod, clone this provisioning repository. Replace `YOUR_PROVISION_REPOSITORY_URL`
   with the remote URL after you publish this repository. No remote is configured yet.

```bash
git clone YOUR_PROVISION_REPOSITORY_URL provision
cd provision
# Use the same Python/activated environment as the template's ComfyUI process.
python3 provision.py --install --workflow qwen-2512.json
python3 provision.py --verify --workflow qwen-2512.json
```

Keep the template's ComfyUI server running on the Pod during provisioning and
verification. Its local `/object_info` is checked before large downloads for core
node/model-family support, then again afterward for model choices. No inference
is submitted. If auto-detection cannot identify one installation, add
`--comfy-dir /actual/path/ComfyUI` (or set `COMFYUI_DIR`). Common locations include
`/workspace/ComfyUI` and `/opt/ComfyUI`. An alternate local API location can be
specified with `--comfy-url http://127.0.0.1:8188`.

After installation, the tool automatically restarts the running ComfyUI process
for the selected installation, then waits for its node/model checks to pass.
It sends `SIGTERM`, allows up to 30 seconds for shutdown, and relaunches with the
same Python command, arguments, working directory and environment. Existing
listen/port settings are preserved; for SSH tunnels, use `--listen 127.0.0.1
--port 8188` when initially starting ComfyUI. The replacement runs detached from
SSH with output appended to `<ComfyUI>/.provision-comfyui.log`. Startup checks
retry for about two minutes. Installation requires one identifiable running
Python `main.py` process for that directory; unrelated Python processes are left
alone. For templates managed by a service or supervisor, use `--no-restart`,
restart through that manager after installation, then run `--verify`.
`--verify` and `--dry-run` never restart ComfyUI.

Use `--all` instead of `--workflow NAME` to provision every discovered export.
Models are shared by destination path. Existing files are SHA-256 checked and
skipped; reruns do not fetch them again. Interrupted downloads resume from
`filename.part`; a final filename appears only after validation. Checksumming
large existing files takes some disk-read time. Sizes shown in GB are rounded
publisher estimates, never used as exact validation sizes. SHA-256 is authoritative.
Only run one installer per ComfyUI installation; a Pod file lock enforces this.

The installer downloads up to three different models concurrently. Use
`--download-jobs 1` to run sequentially, or set a value up to 16 to tune for
available bandwidth and disk throughput. Download and checksum times are reported
separately. Concurrent progress output may interleave.

For multi-connection transfers of individual large files, install `aria2c` on
the Pod and add `--downloader aria2 --connections 4`. Connections can be set
from 1 to 16; the total potential connections are jobs multiplied by connections.
The default remains curl, which requires no extra package. aria2 and curl use
separate partial files, so resume with the same downloader after interruption.
Both paths verify the complete file before publishing it. Performance depends on
the source, Pod network and disk; more connections do not always help.


## Open ComfyUI and generate

On your **local Linux/Chromebook terminal**, adapt the direct TCP SSH command
from Runpod, preserving its host, port and username:

```bash
ssh -i ~/.ssh/id_ed25519 -p POD_SSH_PORT \
  -N -L 127.0.0.1:8188:127.0.0.1:8188 \
  -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 root@POD_IP
```

Leave it running and open **http://localhost:8188**. Use direct TCP SSH;
Runpod's basic SSH proxy does not support tunnelling/SCP in the same way.
See [Runpod SSH documentation](https://docs.runpod.io/pods/configuration/use-ssh).
No public ComfyUI HTTP port is needed for this access method.

These files are **API graphs inside app library wrappers**, not editable UI
graph exports. For the simplest generation flow, keep this repository locally,
install the existing app's `requirements.txt`, run `python app.py`, open
http://localhost:8000, select a saved workflow, fill the form and Generate. See the README in the separate `comfyui-api-poc` repository for app setup. The app replaces `API_*` markers before
submission; provisioning never replaces them.

To load an API graph through a ComfyUI frontend that supports API-format imports,
extract only the `workflow` member to a **new local file** and import that file:

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path('workflows/qwen-2512.json')
Path('/tmp/qwen-2512-api.json').write_text(json.dumps(json.loads(p.read_text())['workflow']))
PY
```

Replace markers with actual inputs before queueing it directly. API import support
varies by frontend; API exports do not retain UI layout. If your frontend cannot
reconstruct the graph, use the existing local app, or obtain the original UI
workflow from its author. Do not overwrite the library files. Run one small smoke
generation before relying on a new template/version combination.

## Save outputs, then terminate

Download images from ComfyUI or the app. To copy every saved output over SSH,
run locally (replace the ComfyUI path with the one printed by the installer):

```bash
scp -i ~/.ssh/id_ed25519 -P POD_SSH_PORT -r \
  root@POD_IP:/workspace/ComfyUI/output ./pod-output
```

Confirm the images open locally, then **Terminate** the Pod in the Runpod console.
Stopping can retain billable storage; termination deletes ephemeral files. See
[Runpod Pod management](https://docs.runpod.io/pods/manage-pods). Nothing in this
repository creates, stops, or terminates Pods.

## Troubleshooting and manifest maintenance

- **Missing/invalid models:** run `--inspect`, then `--verify`. Check the exact
  filename and destination printed. A corrupt final file is reported and kept;
  move/remove it deliberately and rerun `--install`. Interrupted partials are kept
  for retry; checksum-failing partials are removed. Curl failures report their
  exit code. Check network access, free disk space, and the linked model card
  for access/license requirements. The current manifest uses public sources.
- **Missing nodes / incompatible versions:** examine ComfyUI startup logs and
  `/object_info`. The panorama workflow includes the pinned Panorama Stickers
  repository for its native viewer. Other referenced nodes, including switches,
  primitives, resolution and text generation nodes are built into recent ComfyUI.
  An old template can still lack them or the `krea2` encoder type. Choose a
  compatible template/version and its matching Python requirements deliberately;
  the tool never upgrades ComfyUI, Torch or CUDA automatically. Registered nodes
  and files do not prove kernels, VRAM offload, or inference compatibility on A5000.
- **Custom nodes added later:** add a `custom_nodes` entry keyed by checkout
  directory with `repo`, full 40-character `commit`, `nodes` (class-type list), and
  optional `review`. The tool installs `requirements.txt` with its own Python,
  records commit/requirements/interpreter identity, and skips repeat pip installs.
  Existing mismatched or modified checkouts are rejected. Installation restarts
  ComfyUI before checking registered nodes; a folder alone does not prove it loaded.
- **New or ambiguous dependencies:** add the exact `models/<directory>/<filename>`
  key under `models`, with publisher `source`, pinned `url`, `revision`, and
  `sha256` or exact `size_bytes`. Use `url: null` and `review: "reason"` when
  unresolved; installation fails before downloading anything. A matching filename
  alone is insufficient evidence of a variant. For assets hidden in custom node
  settings, use workflow `extra_models` and document the mapping after review.
  Unknown nodes, dynamic model choices, and unclassified asset inputs block
  installation. UI exports are inspectable, but require API re-export for reliable
  input-to-file mapping. Static inspection cannot discover files fetched internally
  by arbitrary custom code; review such nodes before marking them resolved.
- **Server unreachable:** `--verify` is strict and returns failure when live checks
  cannot run. After downloads, this failure does not remove installed models.
  Check `.provision-comfyui.log` if the automatic restart fails, start/restart the
  server manually as indicated, then verify again. `--dry-run`
  needs neither ComfyUI nor network and makes no filesystem changes.

## Local checks

```bash
python3 -m unittest discover -s tests -v
```

Tests use tiny fixtures and mocked HTTP/curl/git/pip. No real model payload
downloads, Pod provisioning, or GPU inference were executed for this tool.
