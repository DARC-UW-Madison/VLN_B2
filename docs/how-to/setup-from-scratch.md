# Set up a Jetson for local TIC-VLA inference

[日本語](setup-from-scratch.ja.md) · [Documentation](../README.md) · [Run and display](run-camera-demo.md)

> Document type: **Procedure**.

## 1. Start with the supported platform, not a generic Python install

This is the ordered route from an unprepared Jetson to the camera demo. The
validated target is **Jetson AGX Orin 64 GB, ARM64, JetPack 5.1.2 / L4T 35.4.1,
Ubuntu 20.04 and CUDA 11.4**. It is not a promise that the recipes work unchanged
on another JetPack, a desktop GPU or a Mac. Keep B2 disconnected throughout.

For a genuinely blank device, identify the module/carrier/storage and obtain the
lab-approved OS image first. [NVIDIA's JetPack 5.1.2 page](https://developer.nvidia.com/embedded/jetpack-sdk-512)
provides the matching release and flashing route. Flashing is destructive and
may require a supported Ubuntu x86 host; Mac SSH access is not a flashing method.
Do not flash the current shared Jetson or reuse a generic PC GPU-driver installer.
The actual project reused an existing OS and ZED SDK; it did **not** test a fresh
flash or reinstall native ZED SDK from an archived installer.

Prepare a research account, local recovery access and reliable power. Use SSH
and optional Tailscale/RDP as described in [bootstrap](jetson-bootstrap.md) and
[system overview](../reference/system-overview.md). They are management tools, not dependencies
of inference. GUI autologin is unnecessary for a boot-time network connection.
Do not publish Wi-Fi credentials, addresses, host keys or account configuration.

## 2. Place reviewed source and inspect storage

At this milestone, the newest source is committed locally but **not pushed** to
the lab GitHub repository. Cloning that URL does not yet reproduce this source.
Have the maintainer supply a reviewed `git archive` plus its commit/digest, then
extract it under `~/Developer/Projects/Robotics/b2/VLN_B2`. Once publication is
authorized, clone the exact published commit there instead. Never transfer a
Mac venv, raw lab records, SSH credentials, upstream code or model cache inside
that source archive. Record the source commit privately on the target.

```bash
umask 077
cd ~/Developer/Projects/Robotics/b2/VLN_B2
mkdir -p local
python3 tools/inspect_target.py --output local/initial-inventory.json
cat /etc/nv_tegra_release
findmnt /mnt/b2-research
df -h / /mnt/b2-research
sudo docker info --format '{{.DockerRootDir}} {{json .Runtimes}}'
stat -c '%g' /dev/nvmap
```

The inventory is standard-library Python 3.8+, so it works before a project
venv exists. The core package needs Python 3.10+; the runtime builds 3.11.18
inside Docker. Host pyenv/venv is useful for development/tests, but is not how
CUDA, ZED or model dependencies are supplied to the inference process.

The reference host has 64 GB eMMC for OS and **one 2 TB NVMe SSD** for large
research artifacts. Allow substantial build space beyond the 3.83 GB download
and 3.77 GB derived checkpoint: Torch compilation, wheels, image layers and
logs also consume SSD capacity. Do not assume eMMC has room for a full build.
Use the measured free space and monitor it during builds.

If the dedicated storage paths do not exist, follow the reviewed storage
procedure in [runtime setup](../records/jetson-runtime.md), including existing-data ownership,
mount identity, Docker relocation and mount guards. It deliberately requires a
local decision instead of a generic formatting command. Current dedicated paths:

| Path | Contents and creation responsibility |
|---|---|
| `/mnt/b2-research/VLN_B2/docker` | Docker's data root; host administrator configures daemon and mount guard |
| `/mnt/b2-research/VLN_B2/huggingface` | Research-owned cache root; `~/.cache/huggingface` points here |
| `~/.cache/huggingface/hub` | Standard Hub repository/blob store, created by official client |
| `/mnt/b2-research/VLN_B2/models` | Research-owned derived artifacts; project `models` points here |
| `local/` | Private per-run images, reports, wheels and logs; ignored by Git |

Do not overwrite an existing cache or `models` directory with a symlink. For a
new host, the administrator first creates writable dedicated roots, then creates
the links only after checking their destinations. Keep previous stores intact.
The recorded ext4 journal recovery was explicitly approved for the existing SSD;
it is not blanket authorization to repair or erase another disk.

## 3. Establish Docker and the host GPU boundary

The inspected host already provided Docker and NVIDIA runtime registration;
this project did not install a generic Docker/NVIDIA stack from scratch. A fresh
host must first install the Docker engine and JetPack-matched NVIDIA container
runtime using [NVIDIA's Jetson container documentation](https://developer.nvidia.com/embedded/jetson-cloud-native/).
Preserve existing daemon settings when adding the SSD data root. `docker info`
must show `nvidia`; `/dev/nvmap` and host CUDA must exist. Stop here if those
prerequisites fail. Installing pip Torch cannot repair a missing host GPU driver.

Run [the native CUDA smoke](../records/jetson-runtime.md#native-cuda-check) before the long
build. Then build the two stages below. Build-time Internet downloads software;
model acquisition is a separate explicit step. These operations compile Python,
Torch and torchvision into image layers; they do not run inference or move B2.

```bash
sudo env DOCKER_BUILDKIT=0 docker build --target python   -f deploy/jetson-runtime.Dockerfile -t vln-b2-python:jp5 .
sudo docker run --rm --pull never --runtime nvidia --network none \
  --user "$(id -u):$(id -g)" --group-add "$(stat -c %g /dev/nvmap)" \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 2g --cpus 2 --pids-limit 128 --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m vln-b2-python:jp5
sudo env DOCKER_BUILDKIT=0 docker build --target runtime   -f deploy/jetson-runtime.Dockerfile -t vln-b2-runtime:jp5 .
sudo docker run --rm --pull never --runtime nvidia --network none \
  --user "$(id -u):$(id -g)" --group-add "$(stat -c %g /dev/nvmap)" \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 4g --cpus 2 --pids-limit 128 --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  -e HOME=/tmp -e CUDA_CACHE_PATH=/tmp/cuda vln-b2-runtime:jp5
```

Both smoke containers must exit 0 with passing JSON. The Python stage tests
its interpreter/GPU visibility; the runtime stage tests actual finite FP32/BF16
Torch GPU operations. Keep their output and image IDs in ignored local storage.
The build uses CUDA 11.4, sm_87, Torch 2.2.2, torchvision 0.17.2 and Python 3.11.18.
It retains Gloo but disables unused RPC through a hash-checked compatibility
patch. This patch does not fix old Torch checkpoint-deserialization advisories.

Source/base digests and direct pins are recorded, but transitive Python and APT
packages are not a complete immutable lock. A rebuild may resolve differently
and receive another image ID. Verify its package inventory, `pip check`, smoke
and strict model load; do not describe the recipe as bit-for-bit reproducible.
[Build fundamentals](../explanations/build-fundamentals.md) explains wheels, compilation and layers.

## 4. Add the separately reviewed model implementation

Read [licensing](../reference/licensing.md) and [third-party inventory](../../THIRD_PARTY.md) first.
After the applicable lab approval, obtain the fixed upstream revision outside
this repository. The following creates a **new** external checkout and stops
if that path already exists; inspect an existing checkout instead of replacing it.

```bash
UPSTREAM="$HOME/Developer/External/TIC-VLA"
mkdir -p "$HOME/Developer/External"
mkdir "$UPSTREAM"
git -C "$UPSTREAM" init
git -C "$UPSTREAM" remote add origin https://github.com/ucla-mobility/TIC-VLA.git
git -C "$UPSTREAM" sparse-checkout init --no-cone
git -C "$UPSTREAM" sparse-checkout set /ticvla/ /LICENSE.md /pyproject.toml
git -C "$UPSTREAM" fetch --depth 1 origin 9fa6f8b66b9e121d5df5df071297bba8e5353ebb
git -C "$UPSTREAM" checkout --detach FETCH_HEAD
test "$(git -C "$UPSTREAM" rev-parse HEAD)" = 9fa6f8b66b9e121d5df5df071297bba8e5353ebb
```

Review its license, package metadata and executed model Python. Do not install
all upstream training requirements: this runtime is the separately checked
inference environment. Do not copy upstream source into this project's MIT tree.
Source code defines the architecture; weight files provide learned numbers.
Neither the model name nor a successful import substitutes for both inputs.

## 5. Acquire the exact approved model files

The reference experiment obtained 17 files (3,827,163,803 bytes) using the official
Hugging Face client: one TIC checkpoint from dataset revision
`671de608f39ccae41b66cbb24ab923c0275f8fb4` and 16 InternVL3-1B files from
`4415a3b810e636d11dfa86b0e9ba40bb00535aa8`. Names, hashes, sizes and conditions
are in [model artifacts](../reference/model-artifacts.md). The operator already approved these
for this private academic trial; another deployment must establish its own terms
and storage authorization. Do not run the download block before that review.

The first line only prints the plan. The remaining block explicitly acquires it
and verifies every file. Use a new report directory. `--cache` means the **Hub
subdirectory**, not its parent `HF_HOME`. This is the only model step needing
network access; the container receives no home credentials or GPU.

```bash
python3 tools/acquire_model_assets.py
HUB="$(readlink -f "$HOME/.cache/huggingface")/hub"
mkdir -p "$HUB"
mkdir -m 700 local/model-acquisition-02
sudo docker run --rm --pull never --runtime runc --network bridge --read-only \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --memory 2g --cpus 2 --pids-limit 128 --tmpfs /tmp:rw,nosuid,nodev,size=128m \
  --mount "type=bind,src=$PWD/tools/acquire_model_assets.py,dst=/tools/acquire.py,readonly" \
  --mount "type=bind,src=$HUB,dst=/hub" \
  --mount "type=bind,src=$PWD/local/model-acquisition-02,dst=/reports" \
  -e HOME=/tmp -e HF_HOME=/tmp/hf -e HF_HUB_OFFLINE=0 \
  -e HF_HUB_DISABLE_TELEMETRY=1 -e HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
  -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python3.11 \
  vln-b2-runtime:jp5 /tools/acquire.py --download \
  --cache /hub --report /reports/assets.json
```

A passing `assets.json` verifies all 17 files and exact total size. Do not use
"latest", add unapproved files or trigger hidden downloads during inference.
The base snapshot contains Python code as well as weights/tokenizer/config;
offline loading still executes reviewed local code.

## 6. Convert the old checkpoint in a separate CPU environment

Never decode the original `.ckpt` with GPU Torch 2.2.2, even with
`weights_only=True`. Build the modern CPU-only converter, run the fixture and
old-runtime tensor-readback checks in [checkpoint conversion](../reference/checkpoint-conversion.md),
then convert the approved file. The output directory must not exist; on the
already prepared target, **skip conversion** and verify the existing output hash.

```bash
sudo env DOCKER_BUILDKIT=0 docker build --pull=false \
  --build-arg BASE_IMAGE="$(sudo docker image inspect vln-b2-python:jp5 --format '{{.Id}}')" \
  -f deploy/checkpoint-converter.Dockerfile -t vln-b2-converter:cpu-v1 .
TIC_REV=671de608f39ccae41b66cbb24ab923c0275f8fb4
SOURCE="$(readlink -f "$HUB/datasets--handsomeYun--TIC-VLA/snapshots/$TIC_REV/TIC-VLA-model.ckpt")"
SOURCE_SHA=376263f89fad0f42c267d85655019232edc91d36e214e23424804dd4cd42e036
MODELS="$(readlink -f models)"
test -d "$MODELS"
test ! -e "$MODELS/tic-vla-671de608-01"
sudo docker run --rm --pull never --runtime runc --network none --read-only \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --memory 32g --cpus 2 --pids-limit 128 --tmpfs /tmp:rw,nosuid,nodev,size=256m \
  --mount "type=bind,src=$PWD/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$SOURCE,dst=/input/source.ckpt,readonly" \
  --mount "type=bind,src=$MODELS,dst=/models" \
  -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/workspace/src \
  --entrypoint timeout vln-b2-converter:cpu-v1 -k 5s 1200s \
  python -m b2_tic_vla.checkpoint_conversion \
  /input/source.ckpt /models/tic-vla-671de608-01 \
  --expected-sha256 "$SOURCE_SHA" --repository handsomeYun/TIC-VLA \
  --repository-type dataset --revision "$TIC_REV"
printf '%s  %s\n'   2d2cab167ef723cf6644729128016ccbb0ab5b131a3aa561c7418a3318ea51e4   "$MODELS/tic-vla-671de608-01/model.safetensors" | sha256sum -c -
```

The converter verifies the original SHA256, uses CPU restricted loading,
preserves all 1,324 tensor names and validates byte-for-byte readback. The
safetensors output is 3,773,492,276 bytes; materialized aliases explain why it
is larger than the original checkpoint. This is a format conversion, not a new
trained model or permission to redistribute it. Only safetensors reaches old GPU
Torch. Keep provenance JSON, original file and converted file outside Git.

## 7. Prepare native ZED software, binding and calibration

For a blank host, obtain the **ZED SDK 4.1.2 build matching L4T 35.4.1** from the
vendor's official archive/support. Follow [Stereolabs' Jetson installation](https://docs.stereolabs.com/docs/development/zed-sdk/linux/work-with-nvidia-jetson),
checking its L4T compatibility and license before installation. Do not replace
it with a current SDK for another JetPack or invent an archived installer URL.
If that exact installer is unavailable, stop and resolve availability with the
vendor; the recorded recipe cannot honestly promise an unattended fresh install.
Do not automatically install AI/depth model assets. The actual target reused
`/usr/local/zed` version 4.1.2 and its existing calibration without changing owner
or host group membership.

Install the two hash-pinned Python wheels into a **new private prefix** using
[the exact camera setup commands](../reference/camera-runtime.md#recreate-the-private-python-prefix).
They create `local/camera-runtime/rebuild-01/python`; change `CAMERA_API` in the
run guide accordingly. The inference image supplies compatible NumPy. Do not
install `pyzed` into system Python or assume the project venv has it.

Check the camera with the vendor tools if needed, then locate the matching
factory calibration locally. Copy only that verified file to a new private
directory, keeping its original filename. This is camera calibration, not an AI
model. If it is absent, use the vendor-supported acquisition and verify serial
matching before continuing; do not reuse another camera's file.

```bash
mkdir -m 700 local/camera-settings-01
CALIBRATION_FILE=/path/to/verified/matching-camera-calibration.conf
test -f "$CALIBRATION_FILE"
sudo install -m 600 -o "$(id -u)" -g "$(id -g)"   "$CALIBRATION_FILE" "local/camera-settings-01/$(basename "$CALIBRATION_FILE")"
```

Set `CAMERA_SETTINGS` to this new directory in the run guide. Use the existing
native `libturbojpeg.so.0` when present; if absent on a clean host, have the
administrator install the matching Ubuntu ARM64 `libturbojpeg0` package after
reviewing its simulated APT transaction. Do not bind unrelated library trees.

## 8. Run, inspect, then decide the next stage

Follow [the complete camera demo](run-camera-demo.md): inspect USB nodes,
capture JPEG, strictly load the model, predict XY positions, render HTML and
open it. That guide contains the full runnable Docker commands and explains
every input/output boundary. Success at the model step also verifies the actual
strict GPU load, beyond the earlier model-free smoke tests.

Run host unit tests with Python 3.10+ if developing the package. The reference
host uses its separate 3.11 venv; no host interpreter replacement is necessary.
These tests use fake/synthetic inputs and do not validate navigation.

Only after camera/model checks should B2 Ethernet and state inspection begin,
using [the field card](field-card.md) and the separately prepared
[Unitree runtime](../reference/unitree-runtime.md). The SDK container is independent of model
inference. ROS 2 is optional; this path does not require it. Onboard sensors,
control authority, frame/time alignment, stopping and real-state shadow testing
remain necessary before implementing or enabling a motor-command sender.

For the frozen record of what was actually executed, including gaps in a truly
fresh-machine reproduction, read [the 2026-11-03 milestone](../records/milestone-2026-11-03.md).

After the single-image acceptance, [the short operator demo](live-camera-demo.md)
provides check/start/view/stop commands for repeated camera predictions.
