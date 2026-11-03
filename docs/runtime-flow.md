# From repository files to robot motion

[日本語](runtime-flow.ja.md) · [System overview](system-overview.md) · [Architecture](architecture.md)

This guide separates what exists from the intended live deployment. The external
Jetson has passing model-free checks, strict actual-model GPU loading and one
synthetic-image inference. Approved weights are privately cached/converted on
SSD. One real ZED RGB capture passed; sustained sensing/timing remain
unvalidated, B2 Ethernet is disconnected, and this project
implements no motor command sender.

For why Mac can remain lightweight, why Docker is optional, where ROS may run
and how containers/sensors connect, read [deployment choices](deployment-design.md).
For the full guide list, use [the documentation index](README.md).

## Which files are shared

On the research login, `~/Developer` is the workspace used for this setup.
It belongs to that login, rather than being a system directory used by every
account. The project, external-source and interpreter directories below it were
established for this work. Other users' homes and existing SSD data are separate.
The Mac has its own independent `~/Developer`; matching names do not synchronize
machines.

The Jetson project at `~/Developer/Projects/Robotics/b2/VLN_B2` is a reviewed
source archive transferred from the Mac. Its tracked source files are intended
to match the selected Mac commit. The Jetson currently has no `.git` directory;
`local/source-revision.txt` records the transferred revision. Editing either
machine does not update the other automatically. The lab GitHub repository now
hosts this source, so a clone and explicit commits on both machines can replace
archive transfer. Switching the Jetson to a clone is a separate step and is not
recorded here.

| Shared project material | Purpose |
|---|---|
| `src/b2_tic_vla/` | Independently written camera/state adapters, recording, synchronous model adapter, candidate tracking and CLI |
| `tools/` | Read-only host inventory and operator-run boot Wi-Fi helper |
| `deploy/` | Container recipes, dependency candidate and model-free CUDA/Python/GPU checks |
| `examples/`, `tests/` | Synthetic observations, unvalidated limits, blank field notes and mocked tests |
| `docs/`, README, CONTRIBUTING | Paired English/Japanese explanations, procedures, evidence and current status |
| LICENSE, THIRD_PARTY | Original-work license and separate external-source conditions |

Machine-local `.venv`, `local/`, compiled binaries, Docker layers, caches,
credentials, recordings and models are excluded from Git. Therefore the entire
project directory is not byte-identical across machines even when every tracked
file matches. `git pull` updates source; it does not synchronize these local items
or rebuild an image automatically.

## How TIC-VLA connects to this repository

Running a model requires several different things:

1. **Model code** defines the neural network and preprocessing/inference methods.
   The pinned upstream checkout is outside this project at
   `~/Developer/External/TIC-VLA`.
2. **Weights** contain learned tensor values. TIC-VLA's checkpoint and the
   InternVL base snapshot are now approved, pinned and stored in the standard
   SSD Hub cache. A separate CPU converter produced the private tensor-only
   navigation artifact. Weights are not source files and are not in Git.
3. **Runtime libraries** execute those operations: Python, PyTorch, Transformers,
   CUDA and related packages. Building these libraries does not fetch weights.
4. **Our adapter** supplies images, an instruction and robot state, calls the
   upstream Python API and validates the returned plan.

```text
Our inference.py
    | Python import from separately supplied upstream_root
    v
ticvla.models.ticvla.TICVLA
    | constructs the model from separately supplied local base-model assets
    | receives compatible checkpoint tensors through our strict loader
    v
PyTorch operations -> CUDA -> host NVIDIA driver -> Orin GPU
    |
    v
Future relative XY positions -> our validated Plan object
```

These are Python calls and local file reads in the same inference process, not
requests to GitHub, a cloud model API, or the onboard Jetson. Network access is
not needed once all reviewed code/assets are installed. Upstream and model Python
code executes locally; offline flags do not make that code a security sandbox.

The existing `infer` command is an **offline synchronous adapter**. It takes one
recorded observation, uses zero semantic-cache delay, and writes a result without
sending it to B2. The proposed live asynchronous semantic cache, timing/pose
alignment, watchdog and command sender remain separate implementation work.
The older GPU Torch must not deserialize the original checkpoint. The approved
source was decoded in the reviewed CPU environment and converted to safetensors;
this tensor-only input passed strict GPU loading and a synthetic inference.
`weights_only=True` alone does not resolve old-Torch serialization issues. See [runtime compatibility](runtime-compatibility.md).

### Licensing boundary

This repository's MIT license covers its original adapters, tools and documents.
It does not cover upstream TIC-VLA. The reviewed
[Academic Software License](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/LICENSE.md)
limits use to the specified educational/academic context and prohibits onward
transfer, including derivatives. Keeping a checkout outside Git does not remove
those conditions; it prevents accidentally publishing it with our own source.

Do not copy upstream implementations into MIT files or publish a combined image,
modified upstream source, converted weights or fine-tuned weights under the
assumption that our MIT notice permits it. Resolve permission for the particular
artifact and intended recipients first, including lab handover. This is an
independent integration project, not a relicensed fork. Code, base-model assets,
checkpoint and data each retain their own terms. See [third-party review](../THIRD_PARTY.md).

## What Docker actually runs

Docker is the packaging/execution layer for the inference software. It does not
communicate with B2 on the model's behalf and does not provide a new GPU driver.

```text
External Jetson hardware: CPU / shared RAM / GPU / USB / Ethernet / SSD
  Host Ubuntu + Linux kernel + NVIDIA driver + system services
    Docker daemon -> image layers stored on SSD
      Running container process
        private application filesystem: Python + Torch + dependencies
        NVIDIA runtime: exposes compatible host GPU support
        explicit mounts: selected source, approved assets, outputs
        network mode: selected for this run
```

An **image** is a stored application filesystem/template. A **container** is a
running instance with a writable layer and process/network isolation. It runs
on this Jetson's CPU and GPU and shares its kernel; it is not another physical
computer or a complete independent OS boot. Ending a container ends its process.
An output survives `--rm` only if written to an external mount or captured by
the host, as our test reports are. Images remain until deliberately removed.
See [Docker's run reference](https://docs.docker.com/engine/containers/run/).

The recipe first builds `vln-b2-python:jp5` with Python 3.11, then builds a
candidate `vln-b2-runtime:jp5` with Torch, torchvision and inference dependencies.
Both match the inspected L4T/CUDA generation. The host venv is for the project's
lightweight tools; it is not used as the container's Python environment.
The current runtime recipe contains test scripts and dependencies, **not** our
complete installed CLI, upstream source or weights. The full import test mounts
the upstream checkout read-only. A future application image/launch configuration
must explicitly supply the project and approved assets.

The already built Python image can be checked without B2 or internet:

```sh
sudo docker run --rm --pull=never --runtime=nvidia --network=none vln-b2-python:jp5
```

Here `--rm` removes the finished container, `--pull=never` uses an existing local
image, `--runtime=nvidia` exposes GPU support, and `--network=none` prevents
external network communication. The image's default command checks Python and
CUDA device visibility and prints JSON. This command does not start navigation.
The full runtime's default command is similarly a model-free Torch test,
not an automatically enabled robot application.

Building downloads software and compiles it into image layers; running the
above check does neither. Adding a future model-cache mount makes those files
visible inside that container without copying them into the image. Do not mount
the whole home directory, NetworkManager profiles, Tailscale state or the Docker
socket into the model process. Container root and broad device/network access
weaken isolation; Docker is not a defense against host administrators.

## Communication by layer

### Management path: Mac to external Jetson

```text
Mac terminal
  -> SSH over the Tailscale private network
  -> Wi-Fi/internet transport (direct peer path or relay)
  -> Jetson tailscaled / SSH service
  -> research user's shell
  -> start a host tool or ask the local Docker daemon to run a container
```

The SSH server/shell is on the host, not inside the model container. Tailscale
controls remote reachability/identity; SSH provides the terminal. No campus
Ethernet is required. No robot subnet routing or Wi-Fi/Ethernet bridge has been
configured. A foreground program may stop when its SSH shell exits; the current
build is explicitly detached. Any eventual unattended application needs its own
reviewed service and stop behavior, not dependence on an open Mac terminal.

### Observation and command path: external Jetson to B2

The proposed SDK path, not yet demonstrated on this robot, is:

```text
Robot state publisher
  -> DDS serialization / RTPS transport, normally UDP/IP
  -> B2-side network -> Ethernet -> Jetson eth0
  -> CycloneDDS -> Unitree SDK2 subscription -> our RobotState

Our future live planner/tracker + command authority/watchdog
  -> Unitree SDK2 high-level velocity request
  -> CycloneDDS / RTPS -> IP -> Ethernet -> B2 service
  -> existing walking/balance control -> robot's actuator system
```

An SDK is a library called by an application, rather than another computer.
DDS handles discovery and typed data exchange; Ethernet/IP carries that traffic.
A successful `ping` proves neither DDS discovery nor compatible services. DDS
interface/domain, message definitions, discovery, QoS and firewall behavior
must match the actual lab setup. The server's physical host, internal forwarding
and actuator bus remain unverified. Do not invent their IPs, frequencies or bus
protocol from the published high-level API.

ROS 2 applications can also use DDS through an RMW implementation. Thus the SDK
path does not require a chain of SDK → ROS 2 → robot. We can use SDK2 directly
on the external Jetson. If an onboard ROS 2 node already publishes useful data,
we may subscribe with compatible interfaces or add a narrowly defined adapter.
Existing onboard ROS 2 services stay in place. See
[Unitree's interoperability guide](https://github.com/unitreerobotics/unitree_ros2)
and [network configuration](network-topology.md).

Linux Docker's default bridge network may complicate DDS discovery. A future
robot-facing container may use explicit host networking and bind DDS to the
verified robot interface. [Host networking](https://docs.docker.com/engine/network/drivers/host/)
shares the host network namespace; it also exposes management interfaces, so it
requires deliberate interface/discovery configuration. It is not being enabled
for the current offline tests. Alternatively, a host-side observation/control
process and an isolated inference container need an explicit IPC contract for
images, states, timestamps and plans. Neither live arrangement is implemented;
validate drivers and measured timing before selecting it.

### Sensor path depends on the cable

- ZED 2i connected by USB to the external Jetson: host USB access → compatible
  ZED SDK/Python binding → RGB frames. Inside Docker, the matching SDK and device
  permissions must be provided explicitly; a host installation does not appear
  automatically in the image.
- ZED connected to the onboard Jetson: that machine must expose a usable image
  stream, with a defined transport, compression, timestamp and camera/body
  transform. Plugging Ethernet into B2 does not forward USB automatically.
- Mid-360: Ethernet sensor packets → the actual attached host/driver → optional
  point clouds/localization. This project has no direct LiDAR input adapter;
  depth/obstacle processing is not added merely by attaching the sensor.

The onboard Jetson may supply sensors/localization; the motion-control system
retains walking/balance. Their actual services and mutual connection are unknown.
We can concentrate application changes on the external Jetson only if the
required interfaces are reachable. The next physical survey must identify cable
endpoints, service hosts and a working receive-only path before motion work.
