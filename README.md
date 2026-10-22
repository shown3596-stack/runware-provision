# Disposable Runpod ComfyUI setup

Provision only the models needed by an existing workflow, on a Pod that already
has ComfyUI. `provision.py` uses Python 3.10+ standard library and `curl`; `git`
and pip are needed only for custom nodes. This is a standalone provisioning repository. It includes unchanged snapshots of
the four workflows audited from `comfyui-api-poc`; the original app and workflow
library remain in that separate repository.

## Inspect locally before renting a GPU

```bash
python3 provision.py --list
python3 provision.py --inspect
python3 provision.py --inspect --workflow qwen-2512-turbo
python3 provision.py --install --workflow qwen-2512-turbo --dry-run
```

Use `python` instead if that is your Python 3 command. Names are discovered from
`workflows/**/*.json`, including the app's `{name, workflow}` wrapper; exact names,
file stems and generated slugs work. The current workflows are `qwen-2512-turbo`,
`qwen-2512`, `imported-workflow`, and `krea-2-turbo`. There is no `flux-klein` export.
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
on Pods. See the app's README and `update-comfy-provisioning` skill for syncing.

## Fresh Pod: deploy, clone, provision

1. Deploy an RTX A5000 24 GB Pod with your existing ComfyUI template and SSH key.
   Choose ephemeral container disk, no network volume, and zero volume disk if
   the template allows it. Budget **at least 50 GB free beyond the template** for
   Qwen or **30 GB** for one Krea workflow, plus outputs; all workflows need about
   67 GB of unique models, so allow at least 80 GB free. Ephemeral disk can still
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
python3 provision.py --install --workflow qwen-2512-turbo
python3 provision.py --verify --workflow qwen-2512-turbo
```

Keep the template's ComfyUI server running on the Pod during provisioning and
verification. Its local `/object_info` is checked before large downloads for core
node/model-family support, then again afterward for model choices. No inference
is submitted. If auto-detection cannot identify one installation, add
`--comfy-dir /actual/path/ComfyUI` (or set `COMFYUI_DIR`). Common locations include
`/workspace/ComfyUI` and `/opt/ComfyUI`. An alternate local API location can be
specified with `--comfy-url http://127.0.0.1:8188`.

Use `--all` instead of `--workflow NAME` to provision every discovered export.
Models are shared by destination path. Existing files are SHA-256 checked and
skipped; reruns do not fetch them again. Interrupted downloads resume from
`filename.part`; a final filename appears only after validation. Checksumming
large existing files takes some disk-read time. Sizes shown in GB are rounded
publisher estimates, never used as exact validation sizes. SHA-256 is authoritative.
Only run one installer per ComfyUI installation; a Pod file lock enforces this.

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

These four files are **API graphs inside app library wrappers**, not editable UI
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
p = Path('workflows/37625afe54d44ce18d1d448f0cfbd15f.json')
Path('/tmp/qwen-2512-turbo-api.json').write_text(json.dumps(json.loads(p.read_text())['workflow']))
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
  `/object_info`. The current exports require no custom repositories: switches,
  primitives, resolution and text generation nodes are built into recent ComfyUI.
  An old template can still lack them or the `krea2` encoder type. Choose a
  compatible template/version and its matching Python requirements deliberately;
  the tool never upgrades ComfyUI, Torch or CUDA automatically. Registered nodes
  and files do not prove kernels, VRAM offload, or inference compatibility on A5000.
- **Custom nodes added later:** add a `custom_nodes` entry keyed by checkout
  directory with `repo`, full 40-character `commit`, `nodes` (class-type list), and
  optional `review`. The tool installs `requirements.txt` with its own Python,
  records commit/requirements/interpreter identity, and skips repeat pip installs.
  Existing mismatched or modified checkouts are rejected. Restart ComfyUI manually
  after installation and rerun `--verify`; a folder alone does not prove it loaded.
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
  Start/restart the server manually as indicated, then verify again. `--dry-run`
  needs neither ComfyUI nor network and makes no filesystem changes.

## Local checks

```bash
python3 -m unittest discover -s tests -v
```

Tests use tiny fixtures and mocked HTTP/curl/git/pip. No real model payload
downloads, Pod provisioning, or GPU inference were executed for this tool.
