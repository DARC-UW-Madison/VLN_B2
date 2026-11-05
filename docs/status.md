# Project status

[日本語](status.ja.md) · [Home](../README.md)

## Current stage

Updated **2026-11-04**. The operator shut down B2 after the inspection.
Follow-up work accessed only the external Jetson; no further robot requests
were sent. After Tailscale reauthentication, all 141 source files were
hash-verified on Jetson and its 184 ordinary tests passed. Both Mac and Jetson
now pass that suite. The deployed source revision is recorded privately in
`local/source-revision.txt`; captures and the operator observation remain
private on Jetson. GitHub publication remains deferred.

After the earlier version-only check, exactly **one Damp request (API 1001)**
was acknowledged with status 0 while the robot was already damped. Fresh state
was checked before sending; 61 samples before and 61 after stayed at mode 7,
error 0. The operator confirmed **no change; remained damped**, with no
unexpected motion reported. No stand-up, recovery or translation request was
sent. The measured API round trip was **1.34 ms on the i7**, excluding the
Jetson SSH path; it is not physical transition/stopping latency. The request
route was external Jetson → SSH → i7 → native ROS 2/DDS → B2 service. The pinned [B2 API definition](https://github.com/unitreerobotics/unitree_sdk2_python/blob/814556d15970dd2ecf1c9984e845ca02ab07e206/unitree_sdk2py/b2/sport/sport_api.py)
identifies Damp as 1001; the official [ROS 2 state description](https://github.com/unitreerobotics/unitree_ros2)
identifies mode 7 as damping. The temporary
client exited and no persistent motion sender was installed. Evidence remains
private under `local/b2-damping-sensors-01` on Jetson.

Separate passive subscriptions decoded front/back built-in images at 1280×720
and 640×360 in the final attempt, and received IMU/joint and sport/odometry state.
Panorama, wireless-controller and LIO streams produced no messages in that
window; usable point-cloud reception remains unconfirmed. See [sensor results,
saved-image viewing and recapture](built-in-sensors.md). These images have not
been substituted into TIC-VLA. Direct external DDS remains unresolved.

The requested first posture/forward/back trial was deferred because the operator
reported insufficient clearance. No actuator request was sent during that
earlier pre-motion check; the subsequent single Damp check is described above. A new three-second
external SDK state probe received zero samples. On the native i7 path, a
read-only API-version query succeeded (status 0, API `1.0.0.1`) alongside 162
finite state samples. These establish onboard service availability, not physical
control readiness. The i7's IPv4 reply route selects native Ethernet rather than
the attached USB path. The [field card](field-card.md) records the first-motion
stages and the currently linked official remote manual's L2+B damping operation.
Actual unit stopping/override remains unverified. Private evidence is under
`local/b2-pre-motion-01`.

The operator confirmed camera/path display and VS Code use. The first powered
B2 attachment was inspected on **2026-11-03**. The USB-C/Anker Ethernet hub reaches
an onboard **Intel Core i7-1265U user-development PC**, not an identified Jetson
or motion controller. Existing authorized credentials worked over scoped IPv6;
no motion-controller SSH login was attempted. The onboard PC has 12 logical CPUs,
about 15.22 GiB Linux-visible RAM, a 512 GB-class NVMe and Ubuntu 20.04.6 with an
RT kernel. An additional onboard Jetson remains unverified.

On that PC's native robot-facing Ethernet, domain **0** was observed in RTPS
discovery. A 12-second receive-only ROS 2 check then received **5,994**
`/sportmodestate` and **240** `/lf/sportmodestate` samples; all checked position,
velocity, yaw-rate and attitude values were finite. This is **onboard state
reception**, not direct external-Jetson SDK reception or model-state integration.
The USB Ethernet adapter is a separate, unbridged interface with overlapping
IPv4 routes. The external link negotiated 1 Gbps full duplex, but a bounded
direct IPv4 test did not reach the native robot service. A native-network profile
was tested only on the external Jetson, then the original active profile was
restored; Wi-Fi remained the default route. A subsequent review found the new
profile active with autoconnect enabled. At the operator's request, the two old
inactive Ethernet profiles were archived and removed, leaving only
`b2-research-link`; Wi-Fi remains the default route. B2 configuration, packages and firmware were unchanged;
no motor request was sent during that initial inspection. Private evidence is under `local/b2-connection-01`.
See [the measured topology and next connection step](field-network.md).

The [short operator demo](live-camera-demo.md) now provides check/start/view/stop
commands. A real-camera run captured 60 frames and completed five exact-input
predictions after one model load; both containers exited cleanly. It uses
assumed stationary state, no web server and no robot commands.

The [model explanation](ticvla-explained.md) now develops pixels, CoT/KV features,
the two waypoint outputs, metric frames, latency, tracking equations and B2
commissioning requirements. New reports retain the same call's VLM text and
display it with endpoint/path distances. A network-isolated recorded-image
check returned 30 points and 412 response characters: load 11.158 s, inference
11.384 s. Prompts and generation settings were unchanged. No live state or
motion was involved; evidence is private in `local/model-response-validation-01`.

The complete frozen account is [the 2026-11-03 milestone](milestone-2026-11-03.md).
Use [initial setup](setup-from-scratch.md) or [the runnable camera/path tutorial](run-camera-demo.md)
for operations. The new end-to-end demo captured a fresh ZED image, predicted
30 XY points in 13.290 s after a 13.109 s load, and rendered/visually checked
a standalone HTML report. All robot state was explicitly assumed stationary;
B2 was disconnected for that recording. Subsequent onboard state reception is
described above; walking remains unimplemented.

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
The expanded **184-test** suite passed on both Mac and Jetson. See [model inputs and loading](model-artifacts.md)
and [conversion](checkpoint-conversion.md) for methods, evidence and limitations.

A bounded real-camera asynchronous shadow trial completed 35 actions with
assumed stationary state, while exposing startup/cache-expiry gaps. A separate
state-only SDK/DDS image passed offline source/native-library and synthetic
serialization checks. See [the cache experiment](asynchronous-runtime.md) and
[SDK environment](unitree-runtime.md). Neither result validates robot motion.

Onboard state reception passed, but direct external-Jetson state reception,
real-state asynchronous control integration, continuous command sending, physical stopping and
navigation evaluation remain unvalidated or unimplemented. The source is hosted at
[DARC-UW-Madison/VLN_B2](https://github.com/DARC-UW-Madison/VLN_B2);
this connection inspection has not been pushed. The [MIT License](../LICENSE)
covers only original code/docs, not
upstream code, weights or converted derivatives.

The 2026-11-03 onsite restart restored eduroam/Tailscale. Saved logs show
pre-restart Wi-Fi authentication timeouts despite stored credentials; the exact
AP/authenticator/client cause remains unresolved. Desktop initialization warnings
are a separate investigation. The agent fixed an expected RDP-readiness exception
that had left its own crash report and archived only that report; Wi-Fi/GDM
settings were not changed by the agent. See [access incident findings](system-overview.md#diagnosing-access-loss-and-desktop-failures).
That management-recovery check was not evidence of robot readiness.

The operator subsequently confirmed direct Windows App desktop access. At the
operator's explicit choice, the research GUI's update/crash notifier autostart
was suppressed; crash storage and manual APT remain available. That notification-only
step upgraded no packages and introduced no automatic upgrade service. Subsequent
bounded SSH/Chrome maintenance and the editor install are separately recorded. See
[manual updates and notifications](system-overview.md#manual-updates-and-desktop-notifications).

## Target setup

| Component | Confirmed | Remaining work |
|---|---|---|
| Robot | Unitree B2 without wheels, reported by the operator | Firmware, actual computers/services, authority and stopping |
| External Jetson | AGX Orin 64 GB class, native CUDA and container GPU operations; real model load, recorded-image profiling and bounded camera shadow inference | Real B2 state, time/frame alignment, continuous cache availability and longer operation |
| Onboard development PC | Intel i7-1265U x86_64, 12 logical CPUs, about 15.22 GiB visible RAM, 512 GB-class NVMe; native ROS 2 state reception passed | Sensor ownership and a reviewed external DDS path; additional Jetson unverified |
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
| Live camera/state observation | 275 JPEGs in a bounded camera trial; separate onboard B2 state reception passed | Mounted view, longer capture, state, clocks, frames and paired recording need checks |
| Atomic cache and asynchronous observer | Experimental shadow trial passed | 35 actions; assumed stationary state, unverified capture clock, substantial cache gaps |
| External Unitree state-only environment | Build/offline verifier passed | Fixed SDK/DDS, 202 source hashes, 516-byte synthetic round trip; external-container B2 reception remains unvalidated |
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

1. At the next powered visit, choose a supported native-LAN connection or an
   explicitly reviewed i7 relay, using the [field card](field-card.md) and [Ethernet runbook](field-network.md)
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
keep English/Japanese conclusions aligned. Before target use, commit reviewed source and hash-synchronize it to the Jetson
archive. The deployed revision is recorded privately in `local/source-revision.txt`;
GitHub publication remains deferred.
Detailed setup/build/asset/load/inference records stay in ignored `local/` on
Jetson, including failed attempts. Preserve source revisions, image IDs, hashes,
inputs, limits and limitations; do not turn this page into a chat transcript.
