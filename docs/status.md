# Project status

[日本語](status.ja.md) · [Home](../README.md)

## Current stage

Preparation tools are implemented. The operator now has access to the external
Jetson through its directly connected display and keyboard, operating separately
from the robot. No robot-network link has been demonstrated. They report a separate onboard Jetson and a possible dedicated motion-control
computer. Their service roles and physical network are not yet verified. No target
inspection report, real GPU inference, or B2 measurements have been received. All CLI
commands are observation-only or offline; none sends motor commands. The
repository is local; lab GitHub hosting is authorized, but its destination and
visibility are not yet specified. The rights holder and public-release license
remain undecided.

## Target setup

| Component | Confirmed information | Still to inspect |
| --- | --- | --- |
| Robot | Unitree B2, without wheels | Firmware, working state/control interface, stop procedure |
| External compute | Jetson, previously reported as AGX Orin; standalone with directly connected display/keyboard | Exact module, memory, storage, OS/JetPack, interfaces and cabling |
| Onboard compute | Separate Jetson reported by the operator | Model, services, sensor ownership and network reachability |
| Motion-control computer | Separate computer suspected by the operator | Actual device, published service host, control ownership and connection path |
| Camera | Stereolabs ZED 2i | Physical connection, installed ZED SDK or wrapper, working RGB stream and timestamps |
| LiDAR | Livox Mid-360 | Existing connection/driver and intended role in this project |
| Containers | Docker installation and use permitted | Current installation, GPU runtime and compatible image |
| Collaboration | Push to lab GitHub permitted | Organization/repository URL, access and visibility |

Component availability does not establish successful sensor or model operation.
Use the existing Jetson installation as the starting point; inspect it before
choosing an image or proposing a host upgrade.

| Deliverable | State | Evidence or completion condition |
| --- | --- | --- |
| Shared documentation and development rules | Prepared | README, Contributing, architecture, development guide, and third-party review |
| Hardware and software specification | Main hardware confirmed; software inventory pending | Target setup above; no target-side inspection yet |
| Standalone target inventory | Implemented; target run pending | `tools/inspect_target.py`; Python standard library only |
| Synthetic replay and candidate tracking | Implemented | `replay`, example trajectories, freshness checks, and velocity limits; no motor output |
| Upstream permissions and dependency revisions | Open | Research use and sharing conditions resolved; exact revisions recorded |
| Offline inference | Synchronous local-file adapter implemented; real-model run pending | Strict checkpoint validation and recorded-observation input; no async cache |
| Live observation without commands | Acquisition adapters implemented; target validation pending | ZED image capture, Unitree state subscription, and observation manifests; clocks and frames unverified |
| Asynchronous inference and motion integration | Not implemented | Consistent cache metadata, live watchdog, validated tracking, and B2 command path |
| Robot stop behavior | Not verified | Reviewed tests of the actual firmware, command loss, and operator override |
| B2 navigation evaluation | Not started | Predefined tasks, complete trial counts, results and limitations |

Local verification (83 tests and the stated limitations) is documented in
[the development guide](development.md#preparation-verification). Synthetic
replay and mocked tests exercise software behavior, not real drivers, model
quality, or hardware performance. Example limits are not approved operating limits.

## Decisions in effect

- The target is B2 with an external Jetson (AGX Orin previously reported), ZED 2i and Livox Mid-360. Inventory onboard computers separately; do not infer their service roles or wiring.
- Use the existing B2 walking controller; investigate a high-level navigation adapter.
- Prefer Mac-to-external-Jetson Tailscale SSH for management. A new host login and per-project dependency isolation are selected; target setup is not yet verified. Prepare the host account and GPU/application environment standalone; the proposed Wi-Fi/Ethernet paths remain unverified.
- Keep proposed behavior separate from verified implementation and experiment results.
- Maintain English and Japanese documentation, with English code and configuration.
- Keep public-facing files free of personal labels, assistant instruction files,
  chat transcripts, machine addresses, and private research data.
- Keep upstream software and weights outside this repository. Do not assume that
  code, weights, and datasets share one license.
- Keep the current tools free of motor output. Verify observations and the
  synchronous model adapter before implementing asynchronous motion integration.
- Use the lab GitHub destination once specified and accessible; resolve rights and the project license before public release.

## Next deliverable

Start with [standalone setup and network discovery](network-topology.md): collect
the external Jetson inventory, establish the host account and Mac SSH access,
and check a compatible GPU/application runtime on the desk. VPN is optional;
none of these target setup steps is verified yet. Identify cable endpoints and
distinguish management from the robot-facing interface. Once B2 is available,
map routes and the documented SDK service/domain before a state-only host probe. Follow [onsite preparation](onsite.md)
for existing sensor software and the working B2 control procedure. Then use the observation
commands to verify an RGB frame from the ZED 2i and received robot state;
establish clock and frame conventions before marking either verified. Select
the container from the measured platform and test the synchronous adapter with
approved local model files. Obtain the lab repository URL separately.

Stereolabs provides an [official Jetson Docker guide](https://docs.stereolabs.com/docs/integrations/docker/install-on-nvidia-jetson)
with platform-specific image selection. NVIDIA documents the [Jetson container runtime](https://developer.nvidia.com/embedded/jetson-cloud-native/).
Start with ZED RGB input, model inference, path tracking and the B2 SDK. Decide
ROS 2 and Mid-360 integration from existing services and a defined need; the
[Livox ROS driver](https://github.com/Livox-SDK/livox_ros_driver2) is one available
integration path, not an adopted dependency. No package or model has been downloaded.

## Continuing the work

A new task starts by reading this page, the relevant guide, and the current Git
diff. Use a branch for a bounded deliverable. On completion, update this page
and its Japanese counterpart with evidence, unresolved questions, and the next
action. Keep detailed experiment methods and results in reviewed reports rather
than expanding this page into a session log.
