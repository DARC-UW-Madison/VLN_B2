# Preparing the external ZED camera

[日本語](camera-runtime.ja.md) · [Documentation](README.md) · [Field card](field-card.md)

This page preserves staged camera commissioning evidence. For the current
operating procedure use [camera prediction and display](run-camera-demo.md);
for subsequent live-shadow results and remaining limits see
[the milestone](milestone-2026-11-03.md). Earlier "not validated" statements
describe their specific check, not the absence of later experiments.

## Current acceptance

On 2026-10-29, the existing Jetson SDK headers/library reported ZED SDK 4.1.2.
The SDK directory was owned by an existing lab login and its SDK group, with no
access for the research login. The research venv did not contain `pyzed`.
Those host permissions, group memberships and Python installations were preserved.

A separate private Python prefix now contains official `pyzed` 4.1 for ARM64
CPython 3.11 and Cython 3.0.12. The existing GPU image provides NumPy 1.26.4.
An offline non-root container imported `pyzed.sl`, returned SDK version 4.1.2,
exposed `DEPTH_MODE.NONE` and `optional_settings_path`, and passed `pip check`.
It did not open a camera. No ZED/video device was present at that inspection.
Import success does not validate USB capture, calibration or image quality.

### First physical capture passed

The subsequently connected camera identified as one ZED 2i. Its video interface
negotiated 5 Gbps and exposed two V4L2 nodes; its companion HID/USB endpoint was
mapped separately. Only the identified camera nodes were passed to the container.
The existing matching 1,568-byte calibration file was copied into private settings
storage; the original SDK was unchanged and no calibration/model download was
needed. With depth disabled, the project camera adapter captured a 1280×720 left
rectified JPEG, 196,592 bytes, and exited successfully within the 45-second
supervisor. The saved image was visually inspected and was upright and nonblank.
This is a desk scene, not a mounted robot's navigation view. Source/receipt times
were recorded separately; capture-clock alignment is still unverified.

Raw images, serial numbers and exact device mappings stay in ignored private
records, not in this repository. The CLI now accepts `--settings-dir` for both
`camera` and `record`, so SDK calibration can use the separate writable mount.


A separate short stream check then completed **90/90 SDK grabs**, zero failed
grabs, over 2.968 seconds between first/last receipts (about 29.99 grabs/s).
Source timestamps increased strictly. This loop did not encode/write every
frame, so it is not JPEG throughput or a long-duration reliability test. Clock
alignment, mounted-view calibration and live inference remain unvalidated.
An optional HID node was no longer present at the later preflight; the successful
stream mapped the still-present camera video/USB endpoints without it. Reinspect
actual devices after SDK use/reconnection rather than retaining old node names.

## Files, dependencies and isolation

The SDK is the native camera software. `pyzed` is the Python binding that calls
it; a wheel alone does not replace the native SDK. See the official
[Python API instructions](https://docs.stereolabs.com/docs/development/api-languages/python).

| Component | Verified input |
|---|---|
| Existing image | `vln-b2-runtime:jp5`, ID `sha256:7f83ebeee829a67ed80fce0a4a738026fce84be6c025203ff24d28a62d43a44a` |
| Native SDK | Existing host `/usr/local/zed`, version 4.1.2; read-only mount |
| Python API | Official `pyzed-4.1-cp311-cp311-linux_aarch64.whl`, 762,664 bytes; SHA256 `677d95054027aa1d332e92af5f8228de62f9ab32d1a4a17c9d2cc4a6e309848f` |
| Declared dependency | PyPI Cython 3.0.12 ARM64 CPython 3.11 wheel, 3,444,055 bytes; SHA256 `dfdbea486e702c328338314adb8e80f5f9741f06a0ae83aaec7463bc166d12e8` |
| Private prefix | `local/camera-runtime/attempt-01/python`, used only with an explicit container `PYTHONPATH` |
| Additional native library | Existing host `libturbojpeg.so.0`, individually mounted read-only; absent in this image |

The binding wheel contains an MIT license; Cython declares Apache-2.0. These do
not replace native SDK terms. No SDK, wheel, camera image or vendor model is
distributed in this repository. The [requirements lock](../deploy/zed-camera-requirements.lock)
records the two software pins. No depth/AI model was acquired or enabled.

The executed installation used a network-disabled, CPU-only container and local
verified wheels with `pip --no-deps --target`. The ordinary research UID wrote
only its private prefix. The GPU image, host Python and project venv were not
modified. Cython satisfies the binding's declared dependency; NumPy stays below
2.0 as required by this binding. Provenance, wheel files and import logs remain
under ignored `local/camera-runtime/attempt-01` on Jetson.

## Recreate the private Python prefix

For a clean prefix on a matching Jetson with the inspected image already
present, the following downloads only the two pinned software wheels from
Stereolabs/PyPI. Unlike import/capture, this explicit installation step needs
network access; it exposes no SDK, camera, home or model files. Choose a new
output directory and retain the install report. `mkdir` fails if it exists.

```sh
mkdir -p local/camera-runtime
mkdir -m 700 local/camera-runtime/rebuild-01
sudo docker run --rm --pull never --runtime runc --network bridge --read-only \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --memory 1g --cpus 2 --pids-limit 64 --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  --mount "type=bind,src=$(pwd)/local/camera-runtime/rebuild-01,dst=/camera" \
  --mount "type=bind,src=$(pwd)/deploy/zed-camera-requirements.lock,dst=/spec/requirements.lock,readonly" \
  -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python3.11 \
  vln-b2-runtime:jp5 -m pip install --only-binary=:all: --require-hashes \
  --no-deps --no-compile --target /camera/python \
  --report /camera/install-report.json -r /spec/requirements.lock
```

Use this new prefix instead of `attempt-01/python` in the import command below,
and run `python3.11 -m pip check` in the same container environment. The lock
intentionally does not replace the image's NumPy/Torch. A different SDK, Python
ABI or L4T needs a separate compatibility check, not an in-place upgrade.

## Reproduce the import check

On the prepared Jetson, from this project's root:

```sh
sudo docker run --rm --pull never --runtime nvidia --network none --read-only \
  --user "$(id -u):$(id -g)" \
  --group-add "$(stat -c '%g' /dev/nvmap)" \
  --group-add "$(stat -c '%g' /usr/local/zed)" \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 2g --cpus 2 --pids-limit 64 --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  --mount "type=bind,src=$(pwd)/local/camera-runtime/attempt-01/python,dst=/camera-api,readonly" \
  --mount type=bind,src=/usr/local/zed,dst=/usr/local/zed,readonly \
  --mount "type=bind,src=$(readlink -f /usr/lib/aarch64-linux-gnu/libturbojpeg.so.0),dst=/camera-libs/libturbojpeg.so.0,readonly" \
  -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/camera-api \
  -e LD_LIBRARY_PATH=/camera-libs:/usr/local/zed/lib:/usr/local/cuda/lib64:/usr/lib/aarch64-linux-gnu/tegra \
  --entrypoint python3.11 vln-b2-runtime:jp5 \
  -c 'import pyzed.sl as sl; print(sl.Camera.get_sdk_version())'
```

Both extra numeric groups exist only inside this container. The SDK mount stays
read-only despite its group permissions. The single extra library resolves the
observed `libturbojpeg.so.0` import failure without overlaying the host's entire
library directory. The NVIDIA runtime supplies vendor GPU interfaces. No USB or
video device is explicitly passed in this import check, and it does not capture.

## First physical camera check

1. Connect the external ZED 2i directly to Jetson USB. Inspect `lsusb`, `lsusb -t`
   and the new video nodes; establish the actual link speed and device identity.
2. Grant the capture container only the identified camera nodes and required
   device groups. Do not use `--privileged` or expose unrelated USB devices.
3. Provide private writable camera settings/calibration storage while retaining
   the existing SDK read-only. Check whether the connected camera's calibration
   is already available or needs official retrieval. Do not silently enable AI
   depth or download a neural model to obtain RGB.
4. Capture one left rectified RGB image with a process deadline. Inspect the
   scene, orientation, exposure and source/receipt times. No B2 connection is
   required. Then record real observations for offline model input.

The first recorded device mapping, calibration and capture passed as described
above. Reinspect device nodes after reconnection; these are not stable names. The host venv still lacks the binding: the existing generic
`camera` CLI must run with this prepared container environment, not by assuming
the host command will now work. B2 state reception and motor commands are
separate later checks; USB camera success does not establish robot readiness.
