# Project status

[日本語](status.ja.md) · [Home](../README.md)

## Current stage

Repository preparation with the main hardware identified. No target inspection
or B2 measurements have been performed. The repository is local; lab GitHub
hosting is authorized, but its destination and visibility are not yet specified.
The rights holder and public-release license remain undecided.

## Target setup

| Component | Confirmed information | Still to inspect |
| --- | --- | --- |
| Robot | Unitree B2, without wheels | Firmware, working state/control interface, stop procedure |
| Compute | NVIDIA Jetson AGX Orin | Memory capacity, storage, installed OS/JetPack, access method |
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
| Upstream permissions and dependency revisions | Open | Research use and sharing conditions resolved; exact revisions recorded |
| Offline inference | Not started | Reproducible prediction and failure-handling report |
| Live observation without commands | Not started | Time/frame alignment and command rejection demonstrated |
| Command interface and stop behavior | Not started | Reviewed test results from the actual robot |
| B2 navigation evaluation | Not started | Predefined tasks, complete trial counts, results and limitations |

## Decisions in effect

- The target is B2 with Jetson AGX Orin, ZED 2i and Livox Mid-360; software and connections still need inspection.
- Use the existing B2 walking controller; investigate a high-level navigation adapter.
- Keep proposed behavior separate from verified implementation and experiment results.
- Maintain English and Japanese documentation, with English code and configuration.
- Keep public-facing files free of personal labels, assistant instruction files,
  chat transcripts, machine addresses, and private research data.
- Keep upstream software and weights outside this repository. Do not assume that
  code, weights, and datasets share one license.
- Use the lab GitHub destination once specified and accessible; resolve rights and the project license before public release.

## Next deliverable

Obtain the lab repository URL and a way to inspect the Jetson. Record its current
OS/JetPack, existing sensor software and working B2 control procedure, following
the [deployment information guide](deployment-intake.md). Verify an RGB frame
from the ZED 2i and timestamped robot state before model integration. Select the
container from the measured platform, then define an offline inference task.

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
