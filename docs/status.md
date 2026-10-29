# Project status

[日本語](status.ja.md) · [Home](../README.md)

## Current stage

Initial read-only inspection of the external Jetson is complete. Mac-to-Jetson
SSH over Tailscale, target-side inventory and native CUDA arithmetic worked.
The host is an AGX Orin 64 GB class system running Ubuntu 20.04 / L4T 35.4.1.
CPython 3.11.18, a dedicated project venv and the CLI are installed; all 93
tests and synthetic replay passed on the target. A separate 2 TB ext4 partition
was inspected with `ro,noload`, then mounted writable with explicit operator
permission. Journal recovery succeeded without observed ext4 errors. Docker
storage and an empty standard Hugging Face cache are now on a dedicated SSD area.
See [runtime setup](jetson-runtime.md) and the [initial baseline](target-baseline.md).
The [system overview](system-overview.md) records exact storage types, hardware
specifications and account/container boundaries. GUI boot is retained and
research-login AC suspend is disabled. Wi-Fi automatic retry and Tailscale boot
services are enabled. A controlled software reboot with HDMI disconnected
restored the current non-enterprise Wi-Fi, Tailscale, SSH, RDP and Docker; the
SSD mounted correctly. The operator confirmed post-reboot RDP display and input.
This does not verify eduroam or a physical power cycle. The eduroam profile still
needs owner-entered system credential saving and a controlled connection test.
GUI autologin is optional for local use, not required for boot networking; leave
it protected for shared use. The existing GDM login target is retained.
B2 is not connected through the wired port; no model inference, camera capture,
or robot control has been validated. All project CLI commands remain
observation-only or offline. A reviewed source archive is on the Jetson; the
source has not been published. The public lab destination
is [DARC-UW-Madison/VLN_B2](https://github.com/DARC-UW-Madison/VLN_B2); access
allows pushing, but no push has been made. Original code and documentation use
the [MIT License](../LICENSE), with contributors retaining their respective rights.

## Target setup

| Component | Confirmed information | Still to inspect |
| --- | --- | --- |
| Robot | Unitree B2, without wheels | Firmware, working state/control interface, stop procedure |
| External compute | AGX Orin 64 GB class; SSH, native CUDA, Python 3.11.18/venv and 93 tests verified | Reviewed model loading and inference |
| Onboard compute | Separate Jetson reported by the operator | Model, services, sensor ownership and network reachability |
| Motion-control computer | Separate computer suspected by the operator | Actual device, published service host, control ownership and connection path |
| Camera | ZED 2i reported; existing SDK headers report 4.1.2 | Research-login SDK access, physical connection, bindings, RGB stream and timestamps |
| LiDAR | Livox Mid-360 | Existing connection/driver and intended role in this project |
| Containers | Docker on SSD; runtime built, dependency check, FP32/BF16 and full imports pass | Checkpoint security and actual inference |
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

Development-host and target verification (93 tests and the stated limitations) is documented in
[the development guide](development.md#preparation-verification). Synthetic
replay and mocked tests exercise software behavior, not real drivers, model
quality, or hardware performance. Example limits are not approved operating limits.

The boot-network helper adds eight non-network tests; all **93 tests** pass on
both development host and target. Its live read-only inspection succeeded under
the target's system Python. Credential entry and reconnect/boot validation are
not part of these mocked tests.

The [runtime flow guide](runtime-flow.md) explains source synchronization,
separate upstream/weight inputs, actual container contents and each communication
layer. The [credential lifecycle](system-overview.md#personal-credentials-sharing-and-return)
records onsite boot checks and the required review before sharing/return. Neither
personal credential saving nor a new GUI login target has been applied.

The [documentation index](README.md) now separates the manual from the project
README. [Deployment choices](deployment-design.md), [terminology](glossary.md),
[offline operation](offline-operation.md) and [licensing](licensing.md) explain
the mechanisms and decision boundaries in both languages. No separate AP is
available; a Jetson-hosted local AP is a candidate, Mac is optional for the core
loop, and B2's existing remote requires priority/stop verification. RDP/Windows
App is the preferred remote-GUI candidate, not a proven stability result.
On 2026-10-28 management access was restored with operator authentication.
Direct LAN OpenSSH was verified before upgrading only Tailscale to 1.104.4;
the running daemon and a new SSH/TCP-forward test passed. The preceding
82-file source revision was hash-verified on Jetson. The current final source
revision must be checked again after any subsequent documentation update.

The pinned RDP source bundle built after resolving test-library/feature
requirements; all 213 upstream test cases passed with no skips. The
approximately 20 MB bundle was installed in `/opt/b2-remote`, with dedicated
service identity, allow group, PAM entry and units. Both units are active.
Following operator confirmation of basic interaction, `b2-rdp.service` was
enabled at boot; sesman starts as its required dependency. Loopback-only
listening, service privileges, verified TLS 1.3, Xorg/X11 query, Windows App
authentication/desktop display and the post-install eight FP32/BF16 GPU checks
passed. Basic interaction is operator-confirmed; settings permission, extended
input checks and a physical power cycle remain pending. A later headless
software reboot and operator-confirmed RDP reconnection passed. A dedicated
background SSH tunnel helper now keeps the Mac forward independent of a chat
or terminal. Its 12 tests and four saved-profile tests bring the local suite
to **109 passing tests**.
Existing NoMachine/GDM
remain in place. See [RDP build and commissioning](rdp-build.md).

The [model-artifact plan](model-artifacts.md) identifies pinned candidates totaling
3,827,163,803 bytes and a separate CPU conversion proposal. It is metadata-only;
terms, acquisition approval, converter implementation and real inference remain
open. No model files were acquired.

## Decisions in effect

Learning and field preparation now include [build fundamentals](build-fundamentals.md),
[the Ethernet/onboard runbook](field-network.md) and [remote desktop](remote-desktop.md).
The visit agenda covers route/DDS verification, onboard service inventory,
external-USB versus built-in network sensor paths, boot/headless access and
operation without campus Wi-Fi. The notes template includes evidence fields.
Vino remains stopped; existing NoMachine was discovered and preserved.
Tailscale client/daemon 1.104.4 and the controlled RDP milestones are recorded
above. AP support was reported by NetworkManager and iw, but no hotspot or
Wi-Fi credential/GDM autologin change was applied. The active Wi-Fi profile is
not the earlier inspected enterprise profile; verify the intended connection
before using the credential helper. The future local robot service and link-loss
policy remain unimplemented.

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

The model-free runtime milestone is complete. `vln-b2-runtime:jp5` built,
`pip check` passed, and both offline Torch and full-import reports passed.
Python 3.11.18 / Torch 2.2.2 / torchvision 0.17.2 / CUDA 11.4 executed eight
FP32/BF16 GPU operations; Transformers, Lightning, timm and the pinned upstream
TIC-VLA module imported without constructing a model. Build and verification
exit codes are both `0`. No model weights were acquired or loaded.

The artifact/loading plan is prepared. Next implement and test the reviewed
CPU conversion and safetensors-only path with synthetic tensors, resolve
artifact-specific terms, then obtain separate approval for exact model files,
revisions, sizes and official-cache location before acquisition.
Run recorded-observation inference only after that review. The
[runtime compatibility review](runtime-compatibility.md) preserves these constraints.
In parallel, complete the deferred onsite boot/credential checks and map B2's
actual computers, cables and service/domain. Verify receive-only camera/state,
frames/timestamps, control authority and stopping before motion integration.

Reports stay under `/mnt/b2-research/VLN_B2/build-logs`:
`runtime-build.exit`, `runtime-verify.exit`, `torch-smoke.json` and
`full-smoke.json`. The completed one-shot verifier has exited; no model download
or robot service follows automatically. Initial and retry logs, source-derived
resume recipes and image provenance are preserved. The local RPC guard and
build-only wheel cleanup are documented in [build recovery](jetson-runtime.md#torch-import-guard-and-build-recovery).
The [setup guide](jetson-runtime.md#storage-prerequisite) records storage/recovery.

Stereolabs provides an [official Jetson Docker guide](https://docs.stereolabs.com/docs/integrations/docker/install-on-nvidia-jetson)
with platform-specific image selection. NVIDIA documents the [Jetson container runtime](https://developer.nvidia.com/embedded/jetson-cloud-native/).
Start with ZED RGB input, model inference, path tracking and the B2 SDK. Decide
ROS 2 and Mid-360 integration from existing services and a defined need; the
[Livox ROS driver](https://github.com/Livox-SDK/livox_ros_driver2) is one available
integration path, not an adopted dependency. The host venv contains this project; no model weight has been acquired.

## Continuing the work

A new task starts by reading this page, the relevant guide, and the current Git
diff. Use a branch for a bounded deliverable. On completion, update this page
and its Japanese counterpart with evidence, unresolved questions, and the next
action. Keep detailed experiment methods and results in reviewed reports rather
than expanding this page into a session log.
