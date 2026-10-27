# Deployment information to collect

[日本語](deployment-intake.ja.md) · [Home](../README.md)

Use this guide to prepare the environment specification. An unknown is an
acceptable answer: record what would establish it rather than guessing. Start
with the first table; later measurements can be made together during integration.
No inspection or motion command in this guide has been run on the target B2.
The B2, Jetson AGX Orin, ZED 2i and Livox Mid-360 are now identified; Docker and
lab GitHub use are permitted. See [target setup](status.md) before collecting
information, and do not ask for already confirmed facts again. Software details
can be inspected once access is available.

## Why the information must be specific

Previous Unitree integration records exposed separate failures in network
interface selection, bridge forwarding, topic selection, and local SDK changes.
Inspection also found disagreements between notes and current scripts. Treat a
historical workaround as a hypothesis to check, not a B2 setup instruction.

For this project, establish these separately:

- Connectivity to the correct robot.
- Receipt of valid, updating robot state.
- Receipt of current camera images.
- Availability and behavior of the intended motion and stop interfaces.

An SDK import, a successful ping, a discovered topic, or a zero-valued dashboard
cannot stand in for all four. A script's existence is not proof it ran successfully.

## Before selecting the implementation

| Information to obtain | What a useful answer contains | Decision it supports |
| --- | --- | --- |
| Robot and supported development access | B2 confirmed; firmware and application versions; access to the manufacturer development manual; high-level control permission | Correct API and supported operation |
| Current working procedure | Which computer runs which script; SDK commit and local modifications; which state, image, motion, and stop operations have actually worked | Reuse an established baseline |
| Compute on each host | CPU architecture; GPU and memory; system RAM; free disk; OS; Python environment; GPU driver, CUDA or JetPack; installed PyTorch if any | Inference placement and compatible packages |
| Physical network layout | Workstation, onboard computer, motion controller and camera connected by named wired/wireless links; routing, bridge, VPN and container involvement | Where each process should run |
| Image acquisition | Camera model and mount; built-in or added camera; driver or API; whether a decoded image can currently be obtained; supported resolution/rate | Observation reader and preprocessing |
| State acquisition | Topics or APIs that actually deliver position, orientation, velocity and yaw rate; type and observed update rate | State reader and delay compensation |
| Command ownership and stopping | Existing navigation, teleoperation or other command senders; operator priority; documented command expiry/update requirement; independent stop and reset procedure | Exclusive control and failure handling |
| First research task | Example instruction; indoor/outdoor setting; route length and corridor clearance; static/dynamic obstacles; initial success definition | Minimum experiment and evaluation scope |
| Practical access | Availability of the B2 and compute; existing lab procedures and recordings; permission to install packages or use containers; whether remote inspection is possible | Work that can start immediately |

Do not send passwords, private keys, serial numbers, or exact laboratory location.
A schematic using host roles is enough initially. Store actual addresses,
credentials, SSIDs and private network configuration in approved local storage.
Original code and documentation use the [MIT License](../LICENSE). The public
lab destination is [VLN_B2](https://github.com/DARC-UW-Madison/VLN_B2), and push
access is verified. Third-party software, weights and data retain their own terms.

## Follow-up checks during integration

### 1. SDK and environment identity

Record the exact SDK checkout and whether its working tree differs from upstream.
Identify the Python interpreter and the module locations actually used by the
launch command. An editable install may point somewhere other than the expected
checkout. Record the CycloneDDS Python package and native library versions,
`CYCLONEDDS_URI`, interface choice, and ROS/RMW settings if ROS is involved.
For containers, distinguish settings inside the container from those on the host.

The [SDK channel factory](https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/unitree_sdk2py/core/channel.py)
constructs a DDS configuration. A locally patched factory may choose it
differently. Check the actual code before concluding that an environment variable
always overrides a programmatic interface argument. Do not apply an old patch
or unset a configuration globally as the first diagnostic step.

The [upstream TIC-VLA training requirements](https://github.com/ucla-mobility/TIC-VLA/blob/main/requirements-train.txt)
pin a CUDA-specific PyTorch build. They are not a verified Jetson deployment
recipe. Select inference dependencies after identifying the target platform.
Isaac Sim and training dependencies are not established prerequisites for the
first offline inference task.

### 2. Network behavior

Identify the intended robot participant and its DDS domain. Record which
interface reaches each host, whether discovery uses multicast or explicit peers,
and whether access-point isolation or a firewall filters traffic. If ROS is
used, check RMW, message definitions, QoS and domain compatibility. Changing
`ROS_DOMAIN_ID` alone does not reconfigure a robot or a separately initialized SDK.

If a bridge or container is present, inspect its forwarding configuration and
packet counters before proposing a change. Record restart persistence and the
recovery access path for any approved network change. Do not copy blanket
firewall exceptions, disable a firewall, or assume a bridge is necessary.

Measure state and image delivery together over the intended link. Average ping
alone does not describe image age, lost frames, jitter or bursty congestion.
Also check whether multiple robots or existing controllers share the same domain.

### 3. Robot-state meaning

Record the topic/API, message type, publishing service, source timestamp,
receive timestamp, frame, units and expected rate for each required field.
Verify that fields change with approved manual motion and that missing data
cannot be mistaken for a valid zero. Identify localization origin, resets,
drift, and whether position is available without an additional localization stack.

Keep vertical velocity distinct from yaw rate. Specify quaternion component
order and the frames of position, linear velocity and orientation independently.
For ROS odometry, identify the actual publisher, `header.stamp`, `frame_id`,
`child_frame_id`, TF ownership and QoS. A program that only subscribes to `/odom`
does not create an SDK-to-ROS bridge or verify those semantics.

### 4. Camera and time alignment

Confirm the B2-supported acquisition path rather than assuming a Go2 video
client works. Record RGB/BGR order, compression, image rotation, calibration,
field of view, mount height/angle and camera-to-body transform. For multiple
cameras, identify which stream is intended for navigation.

Obtain capture timestamps or document that they are unavailable. A filename
timestamp or the completion time of an image request is not necessarily exposure
time. Measure sustained delivered frame rate, image age and losses; distinguish
queueing, encoding and transport delays where possible. Identify clock domains
and how an image is paired with robot state. Exact calibration and latency
measurements can follow the initial hardware inventory.

### 5. Command and stop behavior

Confirm the active control mode, API version, supported directions, units, limits,
required update rate, return codes and competing command sources. Distinguish
request submission from confirmed physical response. Use the
[B2-specific example](https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/example/b2/high_level/b2_sport_client.py)
as an API reference, not a pre-approved test script.

Obtain manufacturer/laboratory procedures for command loss, sender termination,
process stall, operator override, emergency stop and re-enabling. A sender-side
timeout can send a stop only while that process and communication path work.
It cannot establish the robot's behavior after a disconnected link. Verify the
receiver-side expiry and independent stop path under an approved test procedure;
do not deliberately disconnect a moving robot just to answer this questionnaire.
Do not import another platform's remote button combination or equate `Damp()`
with an independently verified emergency stop.

### 6. Hardware and experiment constraints

If a compute module or camera must be added, obtain permitted payload, mounting
points, power voltage/current/connector, cooling, and cable routing constraints
from the robot documentation and laboratory. These are conditional checks, not
a recommendation to buy hardware before assessing what is already available.

Clarify whether the first task uses only RGB and robot state or also evaluates
LiDAR-based localization or a separate obstacle monitor. LiDAR integration is
not automatically a prerequisite for connecting the model's RGB input.
For research comparisons, choose a baseline, trial definition, success tolerance,
intervention policy and available ground truth before claiming performance.
Agree on recording, storage and sharing rules for data involving people or lab spaces.

## Ways to collect the initial facts

On the target Linux computer, these commands only inspect the environment:

```sh
uname -m
uname -r
cat /etc/os-release
python3 --version
df -h .
free -h
```

If available, use `nvidia-smi` on a supported NVIDIA host. For a Jetson, inspect
`/etc/nv_tegra_release` and `dpkg-query -W nvidia-jetpack nvidia-l4t-core` if the
file and package tools exist. Package absence is a result to record, not a reason
to install or upgrade anything yet.

From the Python environment intended for the application:

```sh
python3 -m pip show torch torchvision transformers cyclonedds unitree_sdk2py
```

For each known SDK source checkout, `git rev-parse HEAD`, `git status --short`
and `git diff HEAD` identify the source revision and staged or unstaged tracked
changes. Inspect relevant untracked files listed by status separately. Review output
locally before sharing: package paths and diffs may contain private details.
Do not use these commands as evidence that a model loaded or a robot connected.

## Initial response template

```text
Robot variant / firmware / development access:
Existing successful procedure and its current limitations:
Onboard compute / GPU / RAM / OS / JetPack or CUDA:
External compute available for inference:
Camera / acquisition method / images currently obtainable:
State currently obtainable / topics or APIs / observed rate:
SDK source revision / local patches / Python environment:
ROS and container use, if any:
Network layout by host roles:
Current command sources / operator stop / documented command-loss behavior:
First navigation task and success criterion:
Lab constraints, existing data, and what remains unknown:
```
