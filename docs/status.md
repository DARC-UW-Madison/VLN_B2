# Project status

[日本語](status.ja.md) · [Home](../README.md)

## Current stage

Initial read-only inspection of the external Jetson is complete. Mac-to-Jetson
SSH over Tailscale, target-side inventory and a CUDA driver/device query worked.
The host is an AGX Orin 64 GB class system running Ubuntu 20.04 / L4T 35.4.1.
A separate 2 TB ext4 partition is unmounted; research storage and the compatible
application runtime are not set up. See the [measured baseline](target-baseline.md).
B2 is not connected through the wired port; no model inference, camera capture,
or robot control has been validated. All project CLI commands remain
observation-only or offline. The source is still local. The public lab destination
is [DARC-UW-Madison/VLN_B2](https://github.com/DARC-UW-Madison/VLN_B2); access
allows pushing, but no push has been made. Original code and documentation use
the [MIT License](../LICENSE), with contributors retaining their respective rights.

## Target setup

| Component | Confirmed information | Still to inspect |
| --- | --- | --- |
| Robot | Unitree B2, without wheels | Firmware, working state/control interface, stop procedure |
| External compute | AGX Orin Developer Kit, 64 GB class; Ubuntu 20.04.6 / L4T 35.4.1; SSH verified | Dedicated storage, application runtime and model execution |
| Onboard compute | Separate Jetson reported by the operator | Model, services, sensor ownership and network reachability |
| Motion-control computer | Separate computer suspected by the operator | Actual device, published service host, control ownership and connection path |
| Camera | Stereolabs ZED 2i | Physical connection, installed ZED SDK or wrapper, working RGB stream and timestamps |
| LiDAR | Livox Mid-360 | Existing connection/driver and intended role in this project |
| Containers | Docker 26.1.3; NVIDIA runtime registered; administrator query succeeds | Research-login access, compatible image and container GPU execution |
| Collaboration | Public lab repository identified; push access verified; MIT for original work | First reviewed source publication |

Component availability does not establish successful sensor or model operation.
Use the existing Jetson installation as the starting point; inspect it before
choosing an image or proposing a host upgrade.

| Deliverable | State | Evidence or completion condition |
| --- | --- | --- |
| Shared documentation and development rules | Prepared | README, Contributing, architecture, development guide, and third-party review |
| Hardware and software specification | External-host inventory verified; robot/sensors pending | [Measured baseline](target-baseline.md) |
| Standalone target inventory | Executed on target Python 3.8.10 | `tools/inspect_target.py`; no installation or configuration changes |
| Synthetic replay and candidate tracking | Implemented | `replay`, example trajectories, freshness checks, and velocity limits; no motor output |
| Upstream permissions and dependency revisions | Open | Research use and sharing conditions resolved; exact revisions recorded |
| Offline inference | Synchronous local-file adapter implemented; real-model run pending | Strict checkpoint validation and recorded-observation input; no async cache |
| Live observation without commands | Acquisition adapters implemented; target validation pending | ZED image capture, Unitree state subscription, and observation manifests; clocks and frames unverified |
| Asynchronous inference and motion integration | Not implemented | Consistent cache metadata, live watchdog, validated tracking, and B2 command path |
| Robot stop behavior | Not verified | Reviewed tests of the actual firmware, command loss, and operator override |
| B2 navigation evaluation | Not started | Predefined tasks, complete trial counts, results and limitations |

Local verification (85 tests and the stated limitations) is documented in
[the development guide](development.md#preparation-verification). Synthetic
replay and mocked tests exercise software behavior, not real drivers, model
quality, or hardware performance. Example limits are not approved operating limits.

## Decisions in effect

- The external compute is verified as AGX Orin, 64 GB class. B2, ZED 2i and Mid-360 integration remains pending. Inventory onboard computers separately; do not infer their roles or wiring.
- Use the existing B2 walking controller; investigate a high-level navigation adapter.
- Mac-to-external-Jetson SSH over Tailscale is verified. Keep per-project dependency isolation; preserve the existing OS, ROS, ZED, other accounts and data. Robot Ethernet remains unconnected.
- Keep proposed behavior separate from verified implementation and experiment results.
- Maintain English and Japanese documentation, with English code and configuration.
- Keep public-facing files free of personal labels, assistant instruction files,
  chat transcripts, machine addresses, and private research data.
- Keep upstream software and weights outside this repository. Do not assume that
  code, weights, and datasets share one license.
- Keep the current tools free of motor output. Verify observations and the
  synchronous model adapter before implementing asynchronous motion integration.
- Publish original work under MIT to the specified lab repository after reviewing files and history. Keep restricted upstream materials outside Git.

## Next deliverable

Establish research storage on the inspected system before large image/model
acquisition. Inspect the existing SSD's intended use without formatting or
moving other users' data. Select and test an inference-only GPU/Python/PyTorch
combination against the installed L4T; do not apply the upstream training CUDA
pins as a Jetson installer. Resolve Docker access and prove container GPU
execution before model loading. The [baseline](target-baseline.md) defines the
remaining checks and evidence boundaries. B2 wiring, service/domain, sensor
frames/timing and stop behavior follow when the robot is connected. The
[runtime compatibility review](runtime-compatibility.md) records a model-free
build candidate and the unresolved checkpoint-loading issue; it is not a
working-runtime claim.

Stereolabs provides an [official Jetson Docker guide](https://docs.stereolabs.com/docs/integrations/docker/install-on-nvidia-jetson)
with platform-specific image selection. NVIDIA documents the [Jetson container runtime](https://developer.nvidia.com/embedded/jetson-cloud-native/).
Start with ZED RGB input, model inference, path tracking and the B2 SDK. Decide
ROS 2 and Mid-360 integration from existing services and a defined need; the
[Livox ROS driver](https://github.com/Livox-SDK/livox_ros_driver2) is one available
integration path, not an adopted dependency. This inspection installed no application package or model weight.

## Continuing the work

A new task starts by reading this page, the relevant guide, and the current Git
diff. Use a branch for a bounded deliverable. On completion, update this page
and its Japanese counterpart with evidence, unresolved questions, and the next
action. Keep detailed experiment methods and results in reviewed reports rather
than expanding this page into a session log.
