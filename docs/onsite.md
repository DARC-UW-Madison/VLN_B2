# Onsite quick start

[日本語](onsite.ja.md) · [Home](../README.md)

Use this guide at the Jetson itself. SSH and a GitHub URL are not required.
Reported hardware is **B2 (without wheels), Jetson AGX Orin, ZED 2i, and Livox
Mid-360**. The external-host inventory and management SSH are verified in the
[baseline](target-baseline.md). Sensor/runtime operation, B2 wiring, and control
behavior remain unverified.
All commands in this guide are observation or offline commands; this repository
currently has **no motor-output command**.


For the external Jetson and the separate onboard computers, start with
[computer roles and network discovery](network-topology.md) to identify wiring
and routes before probing SDK services.

For this visit, start with [the Ethernet/onboard procedure](field-network.md)
and [the field card](field-card.md). The external ZED 2i can use USB; built-in
sensors need their existing network export. Replace `IFACE` and `DOMAIN_ID`
with verified lab values, not assumed defaults. Model-free GPU checks passed;
the real sensor/robot probes below have not been completed.

## 1. Bring the project and inspect the Jetson

Copy this repository to the Jetson using a USB drive or another laboratory-approved
method. A source-only archive exported with `git archive` can be transferred
without Git history, local records, or virtual environments. Extract it on the
Jetson and open a terminal in its project root folder. Do not copy another machine's virtual
environment. If the Jetson has no usable OS yet, record its module/carrier-board
identification and installed storage first; the existing installation must be
identified before choosing a matching JetPack image or flashing it.

```sh
python3 tools/inspect_target.py --output local/target-inventory.json
```

The standalone inspector needs Python 3.8+ and no extra packages. It checks OS,
architecture, memory, free space, L4T/JetPack package metadata, CUDA/TensorRT package
metadata, Python package versions, Docker's standard local socket, and USB IDs.
It installs nothing, imports no vendor SDK, sends no robot commands, and does not
use sudo. `unknown` or `not_checked` is a result to investigate, not a failed robot.
No network request is made by this inspector; the Docker probe addresses only the
standard local Unix socket. Commands have individual timeouts, so the whole run
can take several timeout intervals.

Default output omits host/user names, IP/MAC addresses, serial numbers, and raw
command diagnostics. Keep even this report under ignored `local/` and review it
before sharing. Optional network inventory reveals interface names, IP addresses,
and MAC addresses and should stay local:

```sh
python3 tools/inspect_target.py --include-network --output local/target-network.json
```

If an existing SDK checkout is found, inspect its revision without copying it:

```sh
python3 tools/inspect_target.py --sdk-path /path/to/unitree_sdk2_python --output local/target-sdk.json
```

Replace `/path/to/...` with its actual location. This option records revision and
clean/dirty state, not its local path or changed filenames.

## 2. Confirm dependencies, then run two separate probes

The project package needs Python **3.10+**. Run `python3 --version` first. Do not
replace the Jetson's system Python or upgrade JetPack just to satisfy this package.
Use a compatible environment that can load the installed vendor bindings. The
inspector works even when this package cannot run yet.

Required only for the corresponding probe:

| Probe | Existing runtime required | Successful observation |
|---|---|---|
| Camera | Official ZED SDK and `pyzed.sl`, USB connection | Nonempty JPEG showing the left rectified view |
| B2 state | Official `unitree_sdk2py`, CycloneDDS runtime, actual B2 network interface | Finite state samples and active topic in JSON |
| Model | Compatible Jetson PyTorch/CUDA, upstream TIC-VLA environment, local base model and checkpoint | Finite future XY points from offline inference |

Use the laboratory's existing setup first. If dependencies are missing, select
their versions from the inventory and official instructions, then rerun the
relevant probe. `pyenv` alone does not supply NVIDIA libraries or vendor bindings.
There is no generic dependency installer: the host inventory does not establish
compatible application packages or working sensor bindings.

Run the camera probe on Jetson Linux with a process deadline. A native driver can
hang beyond a Python retry limit; `timeout` provides an outer process bound.

```sh
PYTHONPATH=src timeout -k 5s 30s python3 -m b2_tic_vla camera --output local/camera-01/frame.jpg
```

Open `local/camera-01/frame.jpg` locally. Confirm that the actual forward scene is
visible, in focus, and upright, with a rigid mount. The JSON sidecar preserves
camera-source time separately from host receipt time. **Capture-clock alignment
is not verified**. Depth and positional tracking are disabled; no ZED tracking or
depth model is requested by this probe. Close other camera applications first.

For B2, find the wired interface connected to its network from the optional
inventory or `ip -brief link`. Replace `IFACE` below; do not guess a Go2-W address
or interface. Use the lab's documented cabling and address settings without
changing unrelated network settings.

```sh
PYTHONPATH=src timeout -k 5s 15s python3 -m b2_tic_vla state --interface IFACE --domain-id DOMAIN_ID --seconds 3 --output local/state-01.json
```

`auto` listens to both `rt/sportmodestate` and `rt/lf/sportmodestate`. The JSON lists
sample counts and the active valid topic. This is a DDS subscription; discovery
traffic is expected, but no control client or motion publisher is created.
`velocity_frame` and `frame_id` remain `unknown`. A received sample does not prove
that its axes, units, or controller readiness have been verified. No valid sample
returns exit code 2 and still saves the diagnostic result.

Existing output files are never overwritten. Use a new suffix for each attempt.
A failed capture may leave a partial image or an incomplete observation folder;
keep it for diagnosis and choose a new folder for a retry.

## 3. Record only the facts requiring physical access

Copy [the notes template](../examples/onsite-notes.json) into ignored `local/`.
The inventory supplies software versions automatically. Fill the following from
physical inspection or the lab's existing manual; unresolved fields stay null.

| What to verify | Record | Why it matters |
|---|---|---|
| Compute and cables | Orin memory/storage, camera USB link, robot Ethernet, sensor power | Feasibility and basic connections |
| Existing manual operation | Current app/controller, normal stop, operator override, active services | Preserve an established way to control and stop B2 |
| Control authority and loss | Which process owns control; documented and subsequently observed behavior on command/connection loss | Host-side expiry cannot stop a robot after link loss |
| Frame conventions | SDK velocity frame, x/y signs, yaw sign, position frame, units | A valid message can still be interpreted incorrectly |
| Camera geometry and time | Camera height/orientation relative to B2, forward view, capture clock origin and buffering | Training-view differences and stale-image risk |
| Local inference | GPU memory, latency, thermals, compatible source/weights revisions | Whether the proposed execution rate is realistic |

The first visit does not require a model-driven motion test. Frame and stop tests
involving movement must use the lab's existing manual procedure with its operator.
Do not infer command-loss behavior from an SDK method name or from Go2-W notes.
LiDAR data and ROS 2 are separate follow-up checks; neither is required to capture
an RGB image and read B2 state. See the [intake](deployment-intake.md) for context.

## 4. Save a paired observation

Once the two probes work, capture an image with a nearby state sample:

```sh
PYTHONPATH=src timeout -k 5s 30s python3 -m b2_tic_vla record --interface IFACE --domain-id DOMAIN_ID --output-dir local/observation-01
```

This creates `frame.jpg` and `observation.json`. Receipt-time skew must be at most
0.2 s; this example threshold checks recording consistency, not verified sensor
synchronization. The manifest records unverified source clocks and unknown frames
as such. Only after checking the SDK velocity convention, use a new recording
with `--velocity-frame body` (or `base_link`). `--position-frame` can record the
verified position-frame name. These options label measurements; they do not
transform coordinates. Leave them unknown until verified.

## 5. Run the prepared offline model smoke test

No model weights or upstream source are bundled. Before fetching them, agree on
upstream terms, pinned revisions, download size, storage, and the lab's access
rules. Use official caches and acquisition tools; do not redistribute weights in
this repository. The MIT license for original code and documentation does not
cover these external assets. See [third-party terms](../THIRD_PARTY.md).

When the compatible upstream environment and existing local files are available,
first resolve the [checkpoint-loading constraint](runtime-compatibility.md#bounded-build-candidate).
The old-PyTorch build candidate is for model-free checks only;
`weights_only=True` alone does not resolve its published vulnerabilities.
Do not use that candidate to load external checkpoints before a reviewed fix or
alternative loading path is validated. Then
replace all example paths below. Use a reviewed, pinned upstream checkout. It is
added to the process import path; it is not copied into this project.

```sh
PYTHONPATH=src python3 -m b2_tic_vla infer \
  --observation local/observation-01/observation.json \
  --velocity-frame body \
  --instruction "Walk toward the open doorway." \
  --base-model /path/to/local/InternVL3-1B \
  --checkpoint /path/to/local/TIC-VLA-model.ckpt \
  --upstream-root /path/to/local/TIC-VLA \
  --output local/plan-01.json
```

Use the override only when the velocity convention is verified. The adapter uses
local-only Hugging Face loading and `torch.load(weights_only=True)` with strict
checkpoint checks; incompatibility is reported rather than silently dropping
weights or using unrestricted pickle loading. Local upstream/model Python code
still executes and must be trusted; offline loader flags are not a sandbox.

This is **synchronous offline replay**, not TIC-VLA's asynchronous live system.
It uses zero delay and zero relative displacement, rebases its host timing for
replay, and preserves the original observation metadata separately. The package's
current XY outputs are positions relative to the current body frame; they are
**not cumulatively summed**. Output includes elapsed prediction time, not full
camera-to-actuation latency. Test different instructions and scenes before
interpreting one plausible path as a validated navigation model.

## 6. Decide the next implementation from measured results

- Camera fails: check USB/power and the installed ZED SDK's own diagnostic first.
- State fails: check actual interface, cabling/addressing, SDK revision and runtime;
  keep the probe report. Do not patch SDK internals from another robot blindly.
- Model fails: keep the exact error locally; check source/base/checkpoint pairing,
  architecture, GPU build, memory, and Python binding compatibility separately.
- All pass: implement and validate the asynchronous cache with paired reference
  timestamps/poses, clock/frame alignment, and a live shadow loop before enabling
  a B2 motion adapter. Review stops, override, command-loss behavior, and limits
  against measured latency. These are outstanding integration tasks.

For a container, the supplied [Dockerfile](../deploy/Dockerfile) requires an
explicit `BASE_IMAGE` already containing the required Python runtime. Choose a
Jetson image matched to host L4T; ZED and PyTorch are not assumed to coexist in an
arbitrary image. It installs nothing and defaults to help. The template has not
been built on Jetson. Camera/GPU access and DDS networking require separate
onsite configuration; a successful image build would not verify them. Consult
[Stereolabs' Jetson Docker guide](https://docs.stereolabs.com/docs/integrations/docker/install-on-nvidia-jetson)
and [NVIDIA's container resources](https://developer.nvidia.com/embedded/jetson-cloud-native/).

After selecting an existing compatible base, the build shape is:

```sh
docker build --build-arg BASE_IMAGE=YOUR_MATCHED_IMAGE -t b2-tic-vla:local -f deploy/Dockerfile .
docker run --rm --network none b2-tic-vla:local replay
```

The second command only exercises the synthetic fixture. It needs no robot, GPU,
camera access, or network and does not validate a deployment image for inference.
