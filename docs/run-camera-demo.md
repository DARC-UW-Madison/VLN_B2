# Run a ZED image through TIC-VLA and inspect the path

[日本語](run-camera-demo.ja.md) · [Documentation](README.md) · [Initial setup](setup-from-scratch.md)

For an operator-driven updating camera/path demonstration, use
[the short demo tutorial](live-camera-demo.md). This page keeps the single-image
steps for isolating capture, prediction and rendering.

## 1. What this exercise does

Connect a ZED 2i to the **external Jetson's USB 3 port**. Capture one image,
run the existing local model once, then open a report containing the input image,
a separate top-view path and all predicted coordinates. B2 stays disconnected.
The commands below run on Jetson in one Bash terminal from the project root.
Mac can provide SSH or a browser, but performs no inference and needs no Docker.
No Internet is needed after installation and acquisition.

This is a recorded-image test with explicitly **assumed stationary robot state**.
It is not a walking application, a camera-to-ground calibrated overlay or proof
that the path is traversable. The program creates no robot client or commands.
For the real-state workflow later, see [onsite observation](onsite.md).

The procedure requires the prepared GPU image, reviewed upstream source, approved
local model files, native ZED SDK 4.1.2, private Python binding and matching camera
calibration. A host venv alone does not contain these. Start with [initial setup](setup-from-scratch.md)
if any input is absent. Do not run a generic pip install or replace system CUDA.

## 2. Select existing inputs and a new output directory

Use Bash (`bash` if the current shell is different). Adapt only source locations
when using another reviewed deployment. `camera-demo-02` must not exist; choose a
new name for each experiment. Earlier measurements remain in `camera-demo-01`.
`sudo -v` asks in the terminal, never in a chat or saved command.

```bash
set -euo pipefail
umask 077
cd ~/Developer/Projects/Robotics/b2/VLN_B2
PROJECT="$PWD"
IMAGE="$(sudo docker image inspect vln-b2-runtime:jp5 --format '{{.Id}}')"
CAMERA_API="$PROJECT/local/camera-runtime/attempt-01/python"
CAMERA_SETTINGS="$PROJECT/local/camera-runtime/attempt-01/settings"
HUB="$(readlink -f "$HOME/.cache/huggingface")/hub"
BASE_REPO="$HUB/models--OpenGVLab--InternVL3-1B"
BASE_REV=4415a3b810e636d11dfa86b0e9ba40bb00535aa8
UPSTREAM="$HOME/Developer/External/TIC-VLA"
CHECKPOINT="$(readlink -f "$PROJECT/models/tic-vla-671de608-01/model.safetensors")"
CHECKPOINT_SHA=2d2cab167ef723cf6644729128016ccbb0ab5b131a3aa561c7418a3318ea51e4
RUN_DIR="$PROJECT/local/camera-demo-02"
sudo -v
mkdir -m 700 "$RUN_DIR"
test -d "$CAMERA_API/pyzed"
test -d "$CAMERA_SETTINGS"
test -f "$BASE_REPO/snapshots/$BASE_REV/config.json"
test -f "$CHECKPOINT"
test -d "$UPSTREAM/ticvla"
printf '%s  %s\n' "$CHECKPOINT_SHA" "$CHECKPOINT" | sha256sum -c -
printf '%s\n' "$IMAGE" > "$RUN_DIR/runtime-image-id.txt"
```

`IMAGE` records the actual local image ID, not a mutable tag for the run.
The prepared reference image is `sha256:7f83ebeee829a67ed80fce0a4a738026fce84be6c025203ff24d28a62d43a44a`.
An independently rebuilt image must pass the setup checks; a different ID is not
itself proof of failure or compatibility. The safetensors hash is mandatory.
Mount the **entire base-model repository** including `blobs` and `snapshots`:
mounting the snapshot alone breaks its relative symlinks.

## 3. Connect and identify the camera

Use a USB 3 data cable and adequate power. Close ZED Explorer or other processes
holding the camera. Do not connect a robot Ethernet cable for this exercise.
Inspect locally; USB serial numbers and room images must not enter Git.

```bash
lsusb
lsusb -t
ls -l /dev/video*
for node in /sys/class/video4linux/video*; do
  printf '%s: ' "$node"
  cat "$node/name"
  readlink -f "$node/device"
done
```

Find vendor/product `2b03:f880` (ZED video) and `2b03:f881` (companion),
then match video nodes to that USB device using sysfs. Two V4L2 nodes do not mean
two independent left/right camera inputs to this program. `lsusb -t` should show
5000M for the video link. Node numbers can change on every reconnect or boot.

The following assignments match the **2026-11-03 test only**. Replace them from
the inspection above before running. If an endpoint is absent or belongs to a
different device, stop and investigate; do not pass all of `/dev` or use privileged mode.

```bash
VIDEO_0=/dev/video0
VIDEO_1=/dev/video1
USB_VIDEO=/dev/bus/usb/002/003
USB_COMPANION=/dev/bus/usb/001/008
for node in "$VIDEO_0" "$VIDEO_1" "$USB_VIDEO" "$USB_COMPANION"; do
  test -c "$node"
done
```

The settings directory must contain the factory calibration for this camera,
not a file renamed from another serial number. This run disables depth and
object-detection models. See [camera setup](camera-runtime.md) if calibration
or bindings are missing. No on-robot camera is accessed through these USB nodes.

## 4. Capture one image

```bash
sudo docker run --rm --pull never --name b2-camera-demo-capture \
  --runtime nvidia --network none --read-only \
  --user "$(id -u):$(id -g)" \
  --group-add "$(stat -c %g /dev/nvmap)" \
  --group-add "$(stat -c %g /usr/local/zed)" \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 4g --cpus 2 --pids-limit 128 \
  --tmpfs /tmp:rw,nosuid,nodev,size=256m \
  --device "$VIDEO_0" --device "$VIDEO_1" \
  --device "$USB_VIDEO" --device "$USB_COMPANION" \
  --mount "type=bind,src=$PROJECT/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$CAMERA_API,dst=/camera-api,readonly" \
  --mount "type=bind,src=/usr/local/zed,dst=/usr/local/zed,readonly" \
  --mount "type=bind,src=$(readlink -f /usr/lib/aarch64-linux-gnu/libturbojpeg.so.0),dst=/camera-libs/libturbojpeg.so.0,readonly" \
  --mount "type=bind,src=$CAMERA_SETTINGS,dst=/camera-settings" \
  --mount "type=bind,src=$RUN_DIR,dst=/run-output" \
  -e HOME=/tmp/home -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/camera-api:/workspace/src \
  -e LD_LIBRARY_PATH=/camera-libs:/usr/local/zed/lib:/usr/local/cuda/lib64:/usr/lib/aarch64-linux-gnu/tegra \
  -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
  --entrypoint timeout "$IMAGE" -k 5s 45s \
  python3.11 -m b2_tic_vla camera \
  --settings-dir /camera-settings --output /run-output/frame.jpg
```

Success creates `frame.jpg` and `frame.jpg.json` in `RUN_DIR`. The sidecar holds
image dimensions and source/host receipt times; it does not establish that the
two clocks are synchronized. Check that the image is upright, nonblank and the
intended view before inference. The camera SDK acquires its rectified left view;
the adapter converts the SDK's BGRA pixels into RGB and saves a 1280×720 JPEG.
Depth is `NONE`: an RGB-D camera can be used as an RGB source without producing depth.

The NVIDIA runtime exposes compatible host GPU libraries/devices to the container.
The native camera SDK and binding are read-only inputs. Only the selected camera
nodes, writable calibration directory, temporary space and output directory are
exposed. Numeric video/SDK groups grant access inside this process; host group
membership and SDK permissions are not changed. Root inside Docker is avoided;
Docker itself is a privileged host service, not a virtual-machine security boundary.
`timeout` is the container entry point, so the capture process is stopped after
45 seconds (five-second forced-stop grace). The GPU uses host unified memory;
the 4 GiB limit is a process-container limit, not dedicated GPU VRAM.

## 5. Predict future XY positions from the saved image

```bash
sudo docker run --rm --pull never --name b2-camera-demo-predict \
  --runtime nvidia --network none --read-only \
  --user "$(id -u):$(id -g)" --group-add "$(stat -c %g /dev/nvmap)" \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 24g --cpus 2 --pids-limit 128 \
  --tmpfs /tmp:rw,nosuid,nodev,size=256m \
  --mount "type=bind,src=$PROJECT/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$PROJECT/tools,dst=/workspace/tools,readonly" \
  --mount "type=bind,src=$BASE_REPO,dst=/input/base-repo,readonly" \
  --mount "type=bind,src=$CHECKPOINT,dst=/input/model.safetensors,readonly" \
  --mount "type=bind,src=$UPSTREAM,dst=/opt/upstream,readonly" \
  --mount "type=bind,src=$RUN_DIR/frame.jpg,dst=/input/frame.jpg,readonly" \
  --mount "type=bind,src=$RUN_DIR,dst=/reports" \
  -e HOME=/tmp/home -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/src:/workspace/tools \
  -e HF_HOME=/tmp/hf -e HF_MODULES_CACHE=/tmp/hf-modules \
  -e XDG_CACHE_HOME=/tmp/cache -e TORCH_HOME=/tmp/torch \
  -e CUDA_CACHE_PATH=/tmp/cuda -e HF_HUB_OFFLINE=1 \
  -e TRANSFORMERS_OFFLINE=1 -e HF_DATASETS_OFFLINE=1 \
  -e HF_HUB_DISABLE_TELEMETRY=1 -e HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
  -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 \
  -e TOKENIZERS_PARALLELISM=false \
  -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
  --entrypoint timeout "$IMAGE" -k 5s 180s \
  python3.11 /workspace/tools/predict_image.py \
  --image /input/frame.jpg \
  --base-model "/input/base-repo/snapshots/$BASE_REV" \
  --checkpoint /input/model.safetensors --expected-sha256 "$CHECKPOINT_SHA" \
  --upstream-root /opt/upstream --instruction "Move straight ahead." \
  --assumed-stationary --output /reports/prediction.json
```

This second container has **no camera nodes and no network**. It receives the
saved JPEG, reviewed Python source, base-model cache and converted weights as
read-only inputs. The run directory is writable for its report. Neither a home
directory, Hugging Face token, SSH key, Docker socket nor B2 interface is mounted.
Temporary module/GPU caches disappear with the container. The deadline is 180
seconds, not a target inference rate; 24 GiB is a container resource ceiling.

`predict_image.py` verifies the checkpoint SHA256, loads local files only and
strictly checks tensor keys. It records the input image digest before/after
inference. The explicit flag supplies zero pose/velocity under an assumed-state
label; it does not pretend to have received B2 telemetry. The synchronous call
uses the same image as current and semantic-reference input, with zero delay and
relative displacement. It is intentionally simpler than the asynchronous experiment.

Success creates `prediction.json` with `passed: true`, 30 XY points, load and
inference durations, model metadata, `motion_sent: false` and `robot_connected: false`.
A reported failure is not a valid plan. Inspect the error and preserve the run;
do not weaken hash/strict-loading checks to make it pass.

## 6. Display the input and the predicted path

```bash
python3 tools/render_prediction.py   --report "$RUN_DIR/prediction.json" --image "$RUN_DIR/frame.jpg"   --output "$RUN_DIR/prediction.html"
python3 -m json.tool "$RUN_DIR/prediction.json"
```

Open **`RUN_DIR/prediction.html`** in a browser on Jetson, for example through
its existing RDP desktop's file manager. Alternatively copy only this HTML to Mac
and open the local file there. The HTML embeds the original JPEG and SVG; no web
server, SSH tunnel, JavaScript service or Internet connection is needed.
The optional JSON pretty-print above can be long; it exposes no motor interface.

| File | Meaning |
|---|---|
| `frame.jpg` | Actual captured rectified left image |
| `frame.jpg.json` | Camera acquisition metadata; clocks remain unverified |
| `prediction.json` | Instruction, image/weight hashes, timing and future XY positions |
| `prediction.html` | Self-contained input-image/path display and coordinate table |
| `runtime-image-id.txt` | Actual software image selected for this run |

The right panel shows model-relative coordinates in metres, with x forward/up
and y left/left. Red is the assumed origin, blue is the predicted sequence.
Each point is already a relative **position**: do not cumulatively sum it.
Hover for coordinates or read the table. `time_from_now` advances by 0.1 seconds
per point as an adapter assumption from the inspected implementation, not a
measured B2 control period. A 30-point/three-second label does not guarantee
freshness when inference itself took longer.

The image panel is **not a path projected onto the floor**. Camera intrinsics,
robot-to-camera geometry, coordinate signs and source-clock alignment have not
been validated on B2. Rendering a line on a floor image without those checks
would make an unsupported claim. The output has no collision/terrain assessment,
valid stop-distance check or goal-completion guarantee.

## 7. How the computation works

1. USB transfers pixels to the host camera stack; `pyzed` calls native ZED SDK.
2. The adapter saves RGB pixels and timestamps. Docker supplies the environment;
   it neither understands images nor controls the robot.
3. PyTorch loads the base VLM and TIC-VLA parameters into Jetson memory. Reviewed
   upstream Python defines the architecture; this repository validates inputs and calls it.
4. The upstream image preprocessing resizes/normalizes for its visual encoder
   (448-pixel input configuration). Language-conditioned semantic computation
   interprets the scene and instruction. The action path uses visual features,
   semantic context and supplied motion/delay inputs to output 30 XY positions.
5. The independent adapter checks the output shape/finite values and saves JSON.
   The standard-library renderer reads that JSON and the matching JPEG and draws
   SVG/HTML. ROS, RViz and DDS are not involved in this exercise.
6. A future controller would track such a path and send bounded high-level
   velocity requests to B2's existing walking controller. That sender is absent;
   the black-box controller would still handle balance and joints.

For semantic/action separation and what this simplified call omits, read
[TIC-VLA explained](ticvla-explained.md) and [the bounded asynchronous experiment](asynchronous-runtime.md).

## 8. Verified result and troubleshooting

On 2026-11-03, source `6900bfc` and the reference image completed the three
stages with exit 0. Input JPEG: 218,278 bytes, output JSON: 5,081 bytes, HTML:
299,580 bytes. Model load took **13.109 s**, prediction **13.290 s** and returned
30 finite points. The HTML was rendered and visually inspected. The desk view
was not a robot navigation scene; instruction "Move straight ahead." did not
establish correct instruction following, free space or route quality.

| Symptom | Next check |
|---|---|
| Existing directory/report | Choose a new run name; preserve earlier evidence |
| Missing `pyzed` / native library | Use this container's private prefix/SDK/library mounts, not the host venv |
| Camera open fails | Device identity, USB 3 link, cable/power, competing process, matching calibration |
| GPU permission error | Actual `/dev/nvmap` numeric group and compatible NVIDIA runtime |
| Snapshot missing / offline cache error | Approved exact revision and repository-root mount including blobs |
| Hash/strict-load failure | Stop; compare approved asset/conversion provenance, do not bypass checks |
| HTML refuses image | Use the exact JPEG whose digest is in the prediction report |
| Slow first result | Separate load from inference; neither proves a steady control rate |

All images, reports and HTML stay in ignored private `local/`. An embedded image
can contain people, screens and laboratory details; the HTML is not automatically
safe to publish. Repeating this test never authorizes motion. Next use
[the field card](field-card.md) for Ethernet/state inspection and
[the milestone](milestone-2026-11-03.md) for the complete readiness boundary.
