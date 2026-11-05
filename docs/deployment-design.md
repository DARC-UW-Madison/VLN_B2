# Deployment choices: computers, containers, ROS and sensors

[日本語](deployment-design.ja.md) · [Documentation](README.md) · [Terminology](glossary.md)

This guide explains the proposed division of work and the choices behind the
prepared environment. The external Jetson now runs the model with ZED images;
onboard i7 state/video reception and one already-damped request also passed.
Direct external DDS and model-driven control remain unfinished. First read
[the measured computers and communication sequence](network-topology.md) for the
current hardware and software, then use this page for design choices.

## 1. Where computation happens

Think of a program as instructions executed by the CPU/GPU of the machine where
its process runs. Editing a file on Mac does not mean Mac executes that file.
A Mac terminal connected by SSH sends keyboard input to a shell on Jetson; a
Python command in that shell uses Jetson's CPU, memory, disk and available GPU.
Mac receives terminal output. Remote desktop similarly transfers screen/input;
it does not move the model's GPU computation to Mac.

| Machine | Intended work | Required during a completed local run? |
|---|---|---|
| Mac | Edit/review code and documents, initiate remote work, view selected results | No; optional monitoring must follow the experiment's supervision policy |
| External AGX Orin | Acquire observations, run TIC-VLA, track plans, supervise one future command sender, save logs | Yes |
| Onboard Intel i7 development PC | Existing internal state/video access; possible application relay | Required for the measured SSH/i7 path; an additional onboard Jetson is unconfirmed |
| Existing motion-control system | Walking, balance and actuator control behind B2's supported interface | Yes; physical host/internal implementation still unknown |
| GitHub | Reviewable source history and collaboration | No internet dependency during a prepared local run |
| Hugging Face or another approved artifact source | Acquire approved model assets before trials | No dependency during a fully prepared offline run |

The external Jetson is a navigation computer, not a replacement for B2's balance
controller. Predicting a path, tracking that path as velocity, and controlling
leg joints are different computations. Our future high-level velocity requests
must pass through B2's existing controller. The controller's actual service host,
control ownership, operating mode and stop behavior still need inspection.

## 2. Does Mac need every file or Docker?

No. The intended low-burden arrangement is a small source checkout on Mac for
editing/review and the actual runtime on Jetson. Alternatively, an SSH-capable
editor can edit Jetson files directly while Mac keeps only selected documents or
results. A local checkout is convenient for offline editing and recovery; it is
not a requirement of TIC-VLA. Keep changes in explicit commits so a remote-only
working copy is not the sole copy of unfinished research.

| Material | Mac | External Jetson | Public source repository |
|---|---|---|---|
| Original Python, tests, Dockerfiles, documentation | Convenient, optional with remote editing | Needed when those tools run, or included in an approved application image | Yes, after review |
| Restricted upstream TIC-VLA implementation | Not needed for ordinary editing | Separately approved/pinned runtime input | No |
| Model weights, tokenizer/configuration assets | Not needed | Local approved assets before offline inference | No |
| Linux ARM64 CUDA runtime image and build cache | Not needed | Prepared image/layers on SSD | Recipe and permitted metadata only |
| Personal credentials, SSH/Tailscale state | Only each machine's own access state | Host-managed, outside project/images | No |
| Raw camera/video and experiment logs | Selected authorized results only | Local approved research storage | No automatic publication |

Docker on Mac is optional for a specific development need. The Jetson image uses
Linux ARM64 and NVIDIA's Jetson driver stack; matching an Apple Silicon CPU's
ARM64 instruction family does not give a Mac the Jetson GPU/driver. Running an
emulated image is not validation of Orin CUDA. Lightweight standard-library tests
and documentation work can run on Mac without Docker or model weights.

Git is version control on each machine. GitHub hosts a remote Git repository;
it neither runs the robot nor synchronizes live directories. After the user
announces GitHub operation, publish reviewed source and choose a Jetson clone
or an identified source release. `git pull` updates source only: it does not
install dependencies, copy model assets, migrate private configuration, rebuild
an image or restart an application. Record the source revision, image ID,
asset revisions and experiment configuration separately for every trial.

Currently Jetson has a transferred source archive, not a Git clone. Do not run
`git pull` there or overwrite its ignored `.venv`/`local/` to simulate a clone.
Preserve that local state when changing the delivery method. No source has been
pushed and no change to this arrangement is performed by this document.

## 3. Why use Docker if native execution is possible?

Docker is optional packaging, not a mathematical requirement of the model.
A compatible native installation can execute the same computation. We selected
a separate inference environment to preserve the existing Ubuntu 20.04,
system Python 3.8, ROS Foxy, ZED installation and other users' work while testing
a different Python/PyTorch stack. The user also asked to separate dependencies.

| Approach | What it separates | Cost or limitation |
|---|---|---|
| Native Python plus venv | Project Python packages | Native libraries/SDKs still depend on host compatibility; venv is not a filesystem/network sandbox |
| Docker on Jetson | Application filesystem, Python and most userspace libraries | Requires image/build/storage management and explicit device, mount and network access; shares host kernel/driver |
| GPU virtual machine | A separate OS with suitable virtualization/device assignment | Not the selected setup and not supplied by Docker |

The host owns boot, networking, device drivers and Docker's daemon. An image is
a stored filesystem template; a container is a process environment created from
it. The NVIDIA container runtime exposes compatible GPU support to that process.
The container still executes on the real Jetson; there is no separate physical
computer inside Docker. Building installs libraries into image layers, not into
the host venv. Stopping a container frees its running process memory but retains
the image, mounted logs and model files unless explicitly removed.

The prepared `vln-b2-runtime:jp5` image contains Python 3.11.18, locally built
Torch 2.2.2/torchvision 0.17.2, dependencies and model-free check scripts. Its
default command is a check, not a navigation application. It does not contain
weights or a complete installed live B2 application. No ROS distribution or ZED
SDK was added to that runtime recipe; an existing host SDK is not automatically
available inside it. The older Torch candidate has a checkpoint-loading blocker;
passing arithmetic/import checks is not permission to load a model. See
[runtime compatibility](runtime-compatibility.md).

Native execution remains an option if a concrete driver or maintenance need
outweighs container separation. That decision would require an equally explicit
Python/native-library/driver plan; removing Docker does not resolve CUDA ABI,
checkpoint security, sensor permissions or upstream license restrictions.

## 4. Does ROS run inside Docker?

ROS 2 is a framework/library set for robotics programs. A node is a process using
ROS APIs; a topic connects typed publishers and subscribers. ROS can be installed
on the host, in one container, in several containers, or on the onboard computer.
Docker does not decide which of these is correct, and an entire robot does not
need to live in one ROS installation.

For the first external B2 state path, our code can call Unitree SDK2 directly:

```text
External application -> Unitree SDK2 -> CycloneDDS / RTPS -> IP / Ethernet
                    -> reachable B2 service -> existing locomotion system
```

There is no required SDK -> ROS -> robot chain. ROS 2 becomes useful if a chosen
sensor, localization, recorder or visualization already provides a suitable ROS
interface. Preserve those existing services. The official
[Unitree ROS 2 integration](https://github.com/unitreerobotics/unitree_ros2)
documents DDS interoperability; both sides still need compatible types,
discovery, domain, QoS and reachable interfaces. An arbitrary ROS topic name or
matching domain alone does not establish compatibility.

The host's existing Foxy installation does not make every process a ROS node.
Our current CLI uses Python adapters; the inference image has no added ROS
installation. We have not selected a new ROS distribution, created a live ROS
graph, or moved onboard services into containers.

## 5. Can different containers communicate?

Yes. Containers can exchange application messages; they do not automatically
share Python variables, filesystem changes, devices or clocks across computers.
The producer and consumer need an explicit contract: message fields, coordinate
frame, source/receipt time, units, image format, schema version, freshness and
what happens when data stops.

| Mechanism | What it carries | Relevant boundary |
|---|---|---|
| User-defined Docker bridge | TCP/UDP services addressed by container name on one host | `localhost` refers to the current container, not a different container or the host |
| Host networking on Linux | Container uses host interfaces/ports directly | Simpler physical DDS reachability, but network isolation is removed; bind robot traffic deliberately |
| Unix-domain socket with an explicit mount | Local structured messages between processes | Permissions, serialization, limits and ownership still required |
| Shared-memory image buffer | Large image data without repeated full copies | Requires a defined protocol, synchronization, size/lifetime control and freshness checks |
| Read-only input/output mount | Files for offline recorded-data work | Sharing a directory alone is not a robust real-time message protocol |

These are choices, not all implemented components. Docker's official
[bridge](https://docs.docker.com/engine/network/drivers/bridge/) and
[host-network](https://docs.docker.com/engine/network/drivers/host/) guides
explain the network distinction. Port publication maps explicit ports; it is not
a general solution for DDS discovery/multicast or dynamic endpoint addresses.
A Docker bridge is also not a requirement to bridge campus Wi-Fi into B2.

For clarity, first validate a driver and SDK receiver as individual processes,
then a single inference process with recorded input. Add a live boundary only
when needed. One candidate is host-side camera/state acquisition and a local
inference container with a narrow IPC interface; another is an explicitly
configured robot-facing container. Neither is implemented or selected as final.
Do not create several services simply because Docker can run them.

## 6. Which cameras will be used, and what does the onboard PC do?

The first test candidate is the external ZED 2i directly connected by USB to the
external Jetson. This reduces the first image path to one cable, one host and one
SDK. It allows desk testing before robot attachment and avoids first solving an
unknown onboard image exporter. This is a staged engineering choice, not a
conclusion that B2's cameras are unsuitable or will never be used.

```text
Candidate A: external ZED -> USB -> external host ZED SDK -> RGB observation
Candidate B: built-in camera -> attached onboard host/driver -> defined network
             stream -> Ethernet -> external receiver -> RGB observation
Mid-360: power + Ethernet -> its actual receiving host/driver -> possible
         point cloud/localization/obstacle pipeline, not currently implemented
```

An Ethernet cable carries only the data its endpoints publish. It does not make
an onboard USB device appear as a local USB device. For candidate B, identify
the camera/driver, exported ROS topic or other transport, permissions, encoding,
rate, buffering, frame and timestamp semantics. Check whether an existing
consumer owns the camera and avoid disrupting it.

The current ZED adapter requests the left rectified color image with depth
**disabled**. ZED's RGB-D capability and an available LiDAR do not mean the model
already consumes depth or point clouds. The first TIC-VLA input is RGB plus the
instruction and expected robot-state features. Depth or LiDAR may later supply
localization/obstacle checks, which require a separate validated pipeline.
Neither predicted paths nor velocity clipping constitute obstacle avoidance.

The accessible onboard PC is Intel i7. It provided access to existing state
and camera streams without running TIC-VLA. Additional onboard compute and
localization ownership remain unconfirmed. If a built-in stream is suitable, it may replace or complement the
external camera after view/mount/time compatibility is evaluated. Replacing a
camera changes learned visual input and camera-to-body geometry; merely seeing
a JPEG is not model suitability evidence. The internal motion controller also
remains responsible for the existing walking system.

## 7. A complete future run, step by step

1. On Jetson, verify local approved code/assets/configuration, storage, sensor
   availability and a working B2 state path. No GitHub/cloud request is needed.
2. Start an observation/disarmed local application under a defined supervisor.
   It must report health and accept a local stop; reboot/restart cannot arm it.
3. The camera process obtains an image, identifying its source/frame/time.
   A state receiver obtains corresponding pose/velocity with known conventions.
4. The local model converts image/instruction/state into a predicted path.
   The planned asynchronous cache must retain its reference pose/time so the
   controller does not interpret an old path as a fresh current-body path.
5. After explicit arming, one tracking/authority component may produce bounded,
   fresh high-level velocity requests. B2's controller performs walking/balance.
6. Local expiry/watchdogs and the independently verified operator remote-control
   procedure handle stale data, process/link failure and operator takeover.
7. Stop/disarm, retain results locally and export only reviewed summaries to Mac
   or an approved repository. Record successful and failed trials alike.

Steps describing the live service, cache, arming and command sending are future
work. Current probes and offline inference tools do not implement this loop.
Read [offline operation](offline-operation.md), [runtime flow](runtime-flow.md)
and [the field procedure](field-network.md) for the next validation stages.
