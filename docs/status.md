# Project status

[日本語](status.ja.md) · [Home](../README.md)

## Current stage

The [short operator demo](live-camera-demo.md) now provides check/start/view/stop
commands. A real-camera run captured 60 frames and completed five exact-input
predictions after one model load; both containers exited cleanly. It uses
assumed stationary state, no web server and no robot commands.

The complete frozen account is [the 2026-11-03 milestone](milestone-2026-11-03.md).
Use [initial setup](setup-from-scratch.md) or [the runnable camera/path tutorial](run-camera-demo.md)
for operations. The new end-to-end demo captured a fresh ZED image, predicted
30 XY points in 13.290 s after a 13.109 s load, and rendered/visually checked
a standalone HTML report. All robot state was explicitly assumed stationary;
B2 remains disconnected. Ready for Ethernet/state inspection, not walking.

Updated **2026-11-03**. TIC-VLA now loads on the external Jetson GPU and completes
one synthetic-image inference offline. Strict loading accepted 1,324 tensor keys,
948,462,978 unique parameters, horizon 30 and three action layers. The one
synthetic call returned 30 finite XY points in **13.64 seconds**. Its three-second
prediction horizon does not make this a real-time controller. That synthetic run evaluated no actual camera, B2 state or navigation task,
and no motor command was sent. The subsequent first ZED RGB capture passed;
see [camera preparation](camera-runtime.md).

Two subsequent calls on a recorded 1280×720 ZED image passed with explicitly
assumed stationary state: 12.00 and 9.93 seconds overall. Semantic generation
accounted for 11.57 and 9.57 seconds; the action decoder took about 0.006 seconds.
A separate short stream check passed 90/90 SDK grabs at about 30 grabs/s. These
are bounded compatibility checks, not sustained live control or navigation
quality. [Runtime measurements](model-runtime.md) retain the limits and failures.

The host remains AGX Orin 64 GB class / Ubuntu 20.04 / L4T 35.4.1 / CUDA 11.4.
The existing GPU container uses Python 3.11.18, Torch 2.2.2 and Transformers 4.44.2.
A separate Torch 2.15.0+cpu container converted the approved checkpoint to
safetensors; the older GPU runtime never decoded the original pickle checkpoint.
All **177 tests** pass on Mac and Jetson. See [model inputs and loading](model-artifacts.md)
and [conversion](checkpoint-conversion.md) for methods, evidence and limitations.

A bounded real-camera asynchronous shadow trial completed 35 actions with
assumed stationary state, while exposing startup/cache-expiry gaps. A separate
state-only SDK/DDS image passed offline source/native-library and synthetic
serialization checks. See [the cache experiment](asynchronous-runtime.md) and
[SDK environment](unitree-runtime.md). Neither result validates robot motion.

B2 is still disconnected from the wired interface. Actual B2 state reception,
real-state asynchronous control integration, command sending, physical stopping and
navigation evaluation remain unvalidated or unimplemented. The source is hosted
in the lab repository [DARC-UW-Madison/VLN_B2](https://github.com/DARC-UW-Madison/VLN_B2).
The [MIT License](../LICENSE) covers only original code/docs, not
upstream code, weights or converted derivatives.

The 2026-11-03 onsite restart restored eduroam/Tailscale. Saved logs show
pre-restart Wi-Fi authentication timeouts despite stored credentials; the exact
AP/authenticator/client cause remains unresolved. Desktop initialization warnings
are a separate investigation. The agent fixed an expected RDP-readiness exception
that had left its own crash report and archived only that report; Wi-Fi/GDM
settings were not changed by the agent. See [access incident findings](system-overview.md#diagnosing-access-loss-and-desktop-failures).
B2 remains disconnected; recovery is not evidence of robot readiness.

The operator subsequently confirmed direct Windows App desktop access. At the
operator's explicit choice, the research GUI's update/crash notifier autostart
was suppressed; crash storage and manual APT remain available. No host packages
were upgraded/removed and no automatic upgrade service was introduced. See
[manual updates and notifications](system-overview.md#manual-updates-and-desktop-notifications).

## Target setup

| Component | Confirmed | Remaining work |
|---|---|---|
| Robot | Unitree B2 without wheels, reported by the operator | Firmware, actual computers/services, authority and stopping |
| External Jetson | AGX Orin 64 GB class, native CUDA and container GPU operations; real model load, recorded-image profiling and bounded camera shadow inference | Real B2 state, time/frame alignment, continuous cache availability and longer operation |
| Onboard Jetson | Separate unit reported | Type, services, sensor connections and network reachability |
| Motion controller | Separate computer suspected | Actual device, public control interface and ownership |
| Camera | ZED 2i, USB 5 Gbps; SDK/binding and one 1280×720 left RGB capture passed | Mounted view, sustained capture and source-clock alignment |
| LiDAR | Livox Mid-360 reported | Existing driver/network and defined use outside RGB model input |
| Management | eduroam/Tailscale/SSH/RDP software-reboot recovery passed with HDMI disconnected | Physical power cycle, mobile network recovery and node-key policy |

Hardware availability is not sensor or navigation validation. The
[baseline](target-baseline.md) preserves the initial inventory; the
[system overview](system-overview.md) explains current storage and isolation.

| Deliverable | State | Evidence or completion condition |
|---|---|---|
| Bilingual manual and working rules | Maintained | Documentation index, contributing rules, architecture and experiment procedures |
| Replay and bounded path-following logic | Implemented offline | Synthetic replay, stale-input gates and velocity bounds; no sender |
| Model asset acquisition | Verified | 17 approved files, pinned revisions, 3,827,163,803 bytes and file digests |
| CPU conversion | Verified for the actual checkpoint | 1,324 names retained; 3,773,492,276-byte output and readback manifest |
| GPU model loading | Passed | Exact keys/shapes, parameter/device checks, no original pickle input |
| Offline numerical inference | One generated image and two recorded-camera calls passed | 30 finite points per call; real-image state was assumed, not received from B2 |
| Live camera/state observation | 275 JPEGs in a bounded camera trial; B2 state unverified | Mounted view, longer capture, state, clocks, frames and paired recording need checks |
| Atomic cache and asynchronous observer | Experimental shadow trial passed | 35 actions; assumed stationary state, unverified capture clock, substantial cache gaps |
| Unitree state-only environment | Build/offline verifier passed | Fixed SDK/DDS, 202 source hashes, 516-byte synthetic round trip; no actual B2 traffic |
| Motion sender | Not implemented | Real-state integration, independent command expiry, watchdog and control authority |
| Physical stopping and B2 evaluation | Not validated | Review and execute staged field tests before movement |

## Decisions in effect

- Preserve the host OS, JetPack, ROS and existing lab data. Docker and the standard
  Hub cache use the dedicated writable SSD area. Existing data was not formatted.
- Keep raw Hugging Face assets in the standard SSD-backed cache. Keep the derived
  safetensors and manifest in the private SSD models area, referenced by the
  ignored project `models` symlink. Weights, custom model Python and raw logs are
  not in Git or on Mac. [Runtime flow](runtime-flow.md) explains the separation.
- Raw checkpoint decoding on old Torch stays blocked. The reviewed CPU converter
  uses restricted loading, budgets, checksum verification, complete alias names
  and bitwise readback. Conversion does not remove source terms.
- Actual GPU tests used network isolation, ordinary UID, dropped capabilities,
  read-only source/weights and temporary module caches. Only the GPU device's
  video group was added inside the container; host groups/permissions were not
  changed. Model-only checks requested no robot/USB/profiling mounts. Camera checks
  separately mapped the observed video/USB nodes and read-only SDK with its group
  added inside that container. The NVIDIA runtime supplies GPU interfaces. Home
  and credentials were not mounted.
- The headless eduroam reboot and subsequent RDP interaction passed. Wi-Fi secret
  saving does not require GUI autologin; the existing GDM target is unchanged.
  GUI editing was denied by polkit and saving succeeded via the owner's terminal.
  The return review includes the pre-existing lab login where UWNet portal
  authentication occurred, not only the new research login. No cleanup was run.
- Keep VNC outside the current plan. Existing NoMachine is unchanged; no
  performance comparison proves xrdp is faster. Historical screen-connection
  procedures are in [remote desktop](remote-desktop.md).
- Direct RDP on the Jetson Tailscale IPv4 is prepared at the operator's request.
  Mac TCP/RDP/TLS and certificate matching passed; the operator confirmed the
  direct desktop on 2026-11-03. A whole-device reboot under the latest settings
  remains a separate check. The operator manages the Windows App entry. No Mac tunnel/startup job is added; foreground setup SSH closes
  after use. The host adds only the scoped RDP guard/drop-in described in the
  [desktop guide](remote-desktop.md).
- Camera SDK/binding import and dependency checks passed in a separate private
  prefix/container, without changing host groups or the GPU image. USB capture
  acceptance is tracked in [camera preparation](camera-runtime.md).

## Next deliverable

1. Follow the [field card](field-card.md) and [Ethernet runbook](field-network.md)
   to map the actual B2 network, computers, sensors and receive-only SDK path.
   Preserve management Wi-Fi and keep the robot LAN separate from campus.
   Required images/local model inputs were rechecked, the converted checkpoint
   SHA256 matched, and a fresh offline SDK probe passed. The [visit card](field-card.md)
   lists cable/power/controller preparation and the exact receive-container path.
2. Initial ZED RGB and short-stream checks passed. Validate B2 state without commands. Establish frame axes, units,
   source/receipt timing, odometry and calibration before interpreting live plans.
3. Extend the bounded asynchronous shadow trial with actual verified state and
   clock/frame inputs. Investigate startup/refresh gaps, inference stalls and
   stale/missing observations. A 0.156-second median action calculation does not
   establish continuous control availability or valid navigation with old semantics.
4. Confirm control authority, remote-controller priority and actual stopping.
   Only then prepare guarded, low-speed motion trials and predefined evaluation.

The first synthetic run used upstream sampling (200-token maximum, sampling
with temperature 0.7); no seed was fixed or recorded. Timing is a single trial
under CPU/resource limits, not a benchmark average. The reported PyTorch GPU
allocator peak excludes CPU RAM, driver allocations and total unified memory.
No real-time, navigation-quality or physical-safety claim follows from this smoke.

## Continuing the work

Read this page, the relevant guide and Git diff first. Use a bounded branch and
keep English/Japanese conclusions aligned. Source is committed locally, hosted
in the lab repository and hash-synchronized to the Jetson archive.
Detailed setup/build/asset/load/inference records stay in ignored `local/` on
Jetson, including failed attempts. Preserve source revisions, image IDs, hashes,
inputs, limits and limitations; do not turn this page into a chat transcript.
