# Milestone: external Jetson preparation through 2026-11-03

[日本語](milestone-2026-11-03.ja.md) · [Documentation](README.md) · [Current status](status.md)

## 1. Decision at this milestone

**Ready for the first B2 Ethernet and receive-only state inspection. Not ready
for model-driven walking.** The external Jetson can acquire the external ZED's
RGB image, load the approved local TIC-VLA model on GPU, predict 30 future XY
positions and display the input/path in a standalone HTML file. A separate
bounded asynchronous experiment also ran without motor output.

B2 is still disconnected. Its actual internal computers, Ethernet topology,
state topics, coordinate conventions, control ownership and stop behavior have
not been measured. No implemented module constructs `SportClient`, invokes
`Move` or publishes motor commands. A zero candidate from the offline tracker
is not a physical stop. Connecting the cable will not start walking.

This is a frozen, reviewed account of the preparation, decisions, failures and
limits through this date. The operating instructions are [initial setup](setup-from-scratch.md)
and [camera-to-path demonstration](run-camera-demo.md); use those for execution
rather than replaying this chronology. Detailed mechanism/provenance pages are
linked below. Private raw evidence remains in ignored local storage on the
appropriate machine. Earlier host clock corrections make a phase-based account
more reliable than assigning a precise wall-clock time to every old log line.

## 2. Research scope, repository and collaboration

The target is **Unitree B2, without wheels**, not B2-W or Go2-W. The research
question concerns language-conditioned navigation and delayed semantic inference;
the design retains the manufacturer's existing walking/joint controller.
Go2-W setup difficulties informed inspection checklists, not assumptions that
its IP addresses, firmware behavior or SDK patches apply to B2.

The intended lab repository is [DARC-UW-Madison/VLN_B2](https://github.com/DARC-UW-Madison/VLN_B2).
Reviewed source is committed locally and hash-synchronized to the Jetson source
archive, but has **not been pushed**. GitHub is not an inference dependency.
Changes use bounded branches and reviews; test evidence is kept distinct from
physical validation. English is the public base with paired Japanese guides,
Japanese punctuation `，`/`．`, and a separate documentation index. The root README
only describes the project. Public source contains no personal agent files,
private labels, account credentials, raw room images, model weights or vendor code.
AI-assisted work must be checked; generated prose is not experimental evidence.
See [contribution rules](../CONTRIBUTING.md) and [development](development.md).

Original code/documents use MIT with collective contributor attribution. This
**does not relicense TIC-VLA**. Its reviewed custom academic terms remain relevant
to upstream source, weights and derived artifacts. The operator approved this
private academic trial, not onward release of combined images/weights. InternVL,
SDK and dependency notices are tracked separately. Future original research can
use this integration, but publications, modified upstream artifacts, datasets,
images and trained weights each need a release/rights review. We did not invent
a replacement license or claim MIT grants rights in others' materials.
[Licensing](licensing.md) and [third-party inventory](../THIRD_PARTY.md) give details.

## 3. Measured external computer and storage

| Component | Inspected or established fact |
|---|---|
| Module | Jetson AGX Orin 64 GB class, ARM64 |
| CPU | 12 Arm Cortex-A78AE cores |
| GPU | Ampere, 2,048 CUDA cores, 64 Tensor cores, compute capability 8.7 |
| Memory | About 61.3 GiB visible Linux unified RAM; GPU shares it, no separate additional 64 GB VRAM |
| OS stack | Ubuntu 20.04.6, L4T 35.4.1 / JetPack 5.1.2, CUDA 11.4, TensorRT 8.5.2 |
| OS storage | Approximately 64 GB eMMC |
| Large storage | One 2 TB Samsung 990 PRO NVMe SSD; about 1 TB pre-existing lab data preserved |
| Existing software | ROS 2 Foxy, ZED SDK and previous desktop/remote tools retained |
| External sensors | ZED 2i actually captured; Livox Mid-360 reported available but not integrated/tested |

These are hardware/stack facts, not measured TOPS, inference throughput,
network availability or battery runtime. [Target baseline](target-baseline.md)
contains the original inspection context.

The SSD was first inspected using `ro,noload` because ext4 reported
`needs_recovery`. Ordinary read-only mounting can still replay a journal;
`noload` avoided that write before authorization. After the operator explicitly
accepted recovery risk, a writable mount replayed the journal without observed
ext4 errors. It was not a second SSD or a formatting operation; no old data was
deleted. New research areas were placed under `/mnt/b2-research/VLN_B2`.

Docker data moved into its dedicated SSD subdirectory after confirming the old
store was empty. Its original configuration/store were retained. A service
mount dependency/check prevents Docker silently consuming OS space if the SSD
is absent. Standard `~/.cache/huggingface` points to the dedicated SSD cache;
its `hub` child is the official Hub store. Project `models` points to private
SSD-derived artifacts. Source, `.venv` and ignored `local/` remain separately
under `~/Developer/Projects/Robotics/b2/VLN_B2`.

## 4. Accounts, isolation and changes on the host

A separate research login keeps its home, files and Python settings distinct
from the existing lab account. It is **not** full machine isolation: kernel,
devices, system services, root administration, disk and unified memory remain
shared. Administrator/Docker access can affect the host. Do not describe a new
Unix user, pyenv or Docker as an absolute sandbox.

| Layer | What was installed or configured |
|---|---|
| Research user | Pinned pyenv source/interpreters under `~/Developer`; Python 3.11.18 project venv; project source/private records |
| Host services/storage | Dedicated SSD mounts/links, Docker data-root and mount guard; management networking/access settings |
| GPU image | Separate Python/Torch/vision/model dependency environment; source compilation and metadata retained |
| CPU converter image | Newer CPU Torch and format-conversion tools only; no host or GPU Torch replacement |
| Camera prefix | Private pyzed/Cython, matching calibration; existing native SDK/library mounted read-only |
| Unitree image | Separate CycloneDDS/native library and state-only Python source environment |
| RDP host prefix | Separately built xrdp/xorgxrdp under `/opt/b2-remote`; existing GNOME/GDM/NVIDIA preserved |

The host Python 3.8, ROS Foxy, CUDA/JetPack and existing SDK ownership were not
replaced for model installation. The venv does not provide GPU Torch or camera
bindings; inference/capture use the selected container. Docker images are
prepared filesystems; starting a container creates the actual process. Stopping
a `--rm` container removes its transient writable layer, while explicit bind
mount outputs persist. Software builds and model acquisition are separate from
running the model. [Build fundamentals](build-fundamentals.md), [runtime flow](runtime-flow.md)
and [system overview](system-overview.md) explain these boundaries and rollback.

## 5. Remote access, boot networking and observed incidents

Eduroam is configured as a system-available NetworkManager profile with automatic
connection and root-protected saved credentials, without requiring a GUI login.
The identity owner is the operator. Software reboot checks previously recovered
Wi-Fi, Tailscale, SSH and then RDP; the operator confirmed desktop interaction.
That demonstrates those tested boots, not guaranteed recovery from every AP,
identity expiry, power loss or campus outage.

Tailscale supplies an authenticated overlay route when the underlying network
works. Its SSH identity check can require operator reauthorization. It cannot
repair failed Wi-Fi. Direct xrdp listens only on the Jetson's Tailscale address,
port 3389, with a narrow non-tailnet ingress restriction and a startup readiness
check/retry. Windows App connects directly there. The earlier Mac-side SSH
forward/profile and persistent helper were removed; no Mac tunnel or background
job is required now. Mac still acts as the RDP/SSH client when used.

RDP uses a separate virtual Xorg/GNOME session, explaining a different dock or
session appearance from the physical display. Concurrent physical and RDP GUI
sessions under the same user caused desktop conflicts. On request, only the
identified physical GUI session was logged out; SSH/RDP were retained, and the
operator confirmed reconnection. Physical autologin originally remained on the
legacy lab login; the operator changed it to the research login. That setting
can recreate a session overlap on reboot; GUI autologin is not needed for
headless networking. NoMachine was pre-existing and retained, not benchmarked
against the independently commissioned RDP service. No VNC setup was added.

A later loss of remote reachability was investigated using persistent syslog
and current services. Logs showed repeated Wi-Fi association/EAP timeouts and
subsequent secret requests despite saved credentials. The successful boot used
the saved system profile before GUI login. The evidence does not establish that
a password disappeared, Tailscale itself crashed or the AP cause was fixed.
Journal persistence was insufficient for a full previous-boot reconstruction;
wall-clock correction also prevents treating a reported long sleep interval as
proof of suspend. Preserve these uncertainties for recurrence investigation.

The actual generic "System program problem detected" prompt belonged to
`update-notifier`; the remaining saved crash was an earlier Chrome SIGTRAP.
Its exact cause is unresolved. An earlier deliberate readiness-helper failure
had also generated an Apport report; the helper was corrected to return a
normal failure code and only its own obsolete report was archived. Neither is
evidence that TIC-VLA or GPU inference crashed. No report was submitted by the
agent, and external reporting is unnecessary for this trial.

The operator authorized disabling both GUI update and crash-report prompts.
A research-user autostart override now sets `Hidden=true` for `update-notifier`,
and that user's notifier process was stopped. System desktop entries, other
users, local crash collection and manual APT remain. We did not disable all crash
services or delete diagnostic records. Owner Wi-Fi secrets and the previous lab
login's UWNet portal/browser cookies will be reviewed when sharing/returning the
machine; no blanket cleanup or credential sharing has been performed.
See [remote desktop](remote-desktop.md) and [system overview](system-overview.md).

## 6. Maintenance applied on 2026-11-03

APT indexes refreshed successfully. A simulated and reviewed transaction then
upgraded exactly four existing packages; no package was added/removed:

| Packages | Before | After |
|---|---|---|
| `openssh-client`, `openssh-server`, `openssh-sftp-server` | `1:8.2p1-4ubuntu0.12` | `1:8.2p1-4ubuntu0.13` |
| `google-chrome-stable` | `156.0.8078.47-1` | `156.0.8078.79-1` |

SSH configuration was preserved/backed up, `sshd -t` passed, `dpkg --audit`
reported no inconsistency, and SSH/Tailscale/RDP services remained active.
Package inventories verified that all other installed versions were unchanged.
No L4T, kernel, CUDA, TensorRT, Docker or model image was upgraded/rebuilt in
this maintenance transaction. An already running Chrome needs an ordinary
relaunch to use its updated executable; no browser session was forcibly closed.
[Chrome's release channel](https://chromereleases.googleblog.com/2026/?amp=1)
was reviewed for the stable update.

Existing Tailscale 1.104.4 and xrdp 0.10.6.1 were retained after reviewing their
[security bulletins](https://tailscale.com/security-bulletins) and
[xrdp advisories](https://github.com/neutrinolabs/xrdp/security/advisories).
This bounded review is not a claim that every available package was updated
or that Ubuntu 20.04 has complete current security coverage. Some additional
fixes require the lab's Ubuntu Pro/ESM entitlement; for example,
[USN-8804-1](https://ubuntu.com/security/notices/USN-8804-1) lists an ESM OpenSSH
revision beyond the public package applied here. No subscription was attached
or purchased. Further OS lifecycle maintenance requires a separate lab decision
that also accounts for [Jetson's upgrade constraints](https://docs.nvidia.com/jetson/archives/r35.4.1/DeveloperGuide/text/SD/SoftwarePackagesAndTheUpdateMechanism.html).

## 7. GPU runtime build and compatibility work

Native CUDA first passed a small FP32 numerical check with zero maximum error.
The matching-L4T NVIDIA base was pinned by digest. CPython 3.11.18 was built in
its own image stage; Torch 2.2.2 and torchvision 0.17.2 were compiled against
CUDA 11.4 for sm_87. This avoided replacing the shared host stack merely to
satisfy upstream training versions. PyTorch/vision, FP32/BF16 operations,
Transformers 4.44.2, Lightning, timm and upstream imports passed, with `pip check`.

A Torch RPC availability mismatch caused an import failure in the initial build;
a hash-checked patch disables unused RPC while retaining Gloo. Build-tool wheel
metadata also needed handling: build-only CMake/Ninja were removed before final
runtime dependency validation. These fixes concern software compatibility, not
model quality or checkpoint-deserializer security. Direct pins are not a full
transitive/APT lock, so rebuilds need new inventory/checks.

Reference GPU image: `vln-b2-runtime:jp5`, ID
`sha256:7f83ebeee829a67ed80fce0a4a738026fce84be6c025203ff24d28a62d43a44a`.
The smaller Python stage is separately retained. Build commands, limits,
inventories and failed attempts are in [runtime setup](jetson-runtime.md) and
[compatibility](runtime-compatibility.md). Building the environment alone did not
fetch model weights or prove model loading.

## 8. Approved acquisition, separate conversion and strict loading

Reviewed upstream source is outside the project at revision
`9fa6f8b66b9e121d5df5df071297bba8e5353ebb`. The operator approved exactly
3,827,163,803 bytes across 17 Hub files. The official client verified pinned
metadata, byte sizes and digests without passing personal credentials. Inference
uses the local cache only; no automatic startup downloads were introduced.

| Asset | Pinned identity/result |
|---|---|
| Original TIC checkpoint | Dataset `handsomeYun/TIC-VLA`, revision `671de608f39ccae41b66cbb24ab923c0275f8fb4`; 1,938,501,547 bytes |
| InternVL3-1B | `OpenGVLab/InternVL3-1B`, revision `4415a3b810e636d11dfa86b0e9ba40bb00535aa8`; 16 selected files, 1,888,662,256 bytes |
| Derived TIC safetensors | 3,773,492,276 bytes; SHA256 `2d2cab167ef723cf6644729128016ccbb0ab5b131a3aa561c7418a3318ea51e4` |

Old GPU Torch 2.2.2 is prohibited from decoding the original pickle checkpoint.
A separate CPU-only Torch 2.15.0+cpu image uses 12 hash-pinned software artifacts.
Generated fixtures checked BF16, aliases, transposed/scalar/empty tensors,
NaN payloads and signed-zero bytes; unsupported metadata must fail. Old GPU
runtime tensor-only readback also passed. A first BuildKit attempt failed because
buildx was absent; the existing legacy builder succeeded without adding it.

The actual conversion preserved all 1,324 tensor names, shapes, dtypes and bytes.
Aliases materialized in safetensors account for its larger file size. Original
and converted hashes/provenance remain private. The GPU adapter then strictly
loaded 1,324 keys, 948,462,978 unique parameters, a 30-point horizon and three
action layers. No missing/unexpected key was silently ignored. Local upstream
and snapshot Python still execute; file-only loading is not a code sandbox.
See [assets](model-artifacts.md), [conversion](checkpoint-conversion.md) and
[GPU checks](model-runtime.md).

## 9. External ZED camera and synchronous predictions

Existing native ZED SDK 4.1.2 initially could not be read by the research login.
Rather than changing host ownership/groups, the container receives the SDK
read-only with its numeric group, and a private prefix supplies official pyzed
4.1 (CPython 3.11 ARM64) plus Cython 3.0.12. A separately mounted turbojpeg
library supplies the missing native dependency. NumPy 1.26.4 remains in the GPU
image; the host Python and research venv were not modified for pyzed.

A directly connected ZED 2i negotiated a 5 Gbps video link. Only identified
video/USB endpoints were passed, with matching factory calibration copied into
private writable settings. Depth was disabled and no AI model was downloaded.
The first 1280×720 left rectified JPEG was nonblank/upright on visual inspection.
Source timestamp and host receipt remain separate; mounted B2 view/geometry and
clock synchronization are unverified. On reconnect, USB endpoint numbers changed;
old bus/device assignments cannot be copied blindly.

| Check | Measured result | Limit of the result |
|---|---|---|
| First synthetic-image inference | 13.64 s, 30 finite XY points | No camera, fixed real state or navigation quality |
| Two calls on one recorded ZED image | 12.0005 / 9.9308 s | Assumed stationary state; not a live controller |
| Semantic generation in those calls | 11.5729 / 9.5657 s | Stage synchronization adds diagnostic overhead |
| Cache-building forward | 0.2248 / 0.2165 s | Not a full semantic refresh |
| Current-image visual features | 0.0893 / 0.0892 s | Same recorded image |
| Action decoder | 0.00582 / 0.00569 s | Excludes semantic generation and capture |
| Short SDK stream | 90/90 successful grabs, 29.99 grabs/s | No per-frame JPEG write, long-run or inference-rate claim |
| New camera-to-HTML demo | Load 13.109 s; inference 13.290 s; 30 points | New desk image, assumed state, no route-quality evaluation |

The two recorded-image timings used seeds 0 for Python/NumPy/Torch, upstream
sampling at temperature 0.7 with a 200-token maximum, not a measured token count
or forced deterministic execution. The earliest synthetic run had no recorded
seed. A profiling script initially named `profile.py` shadowed the standard
library; renaming fixed that tool failure before inference. Allocator peaks
reported in profiling are Torch allocations, not total unified-memory use.

The new demo, source `6900bfc`, completed capture, prediction and rendering with
exit 0. Private outputs: `local/camera-demo-01/frame.jpg` (218,278 bytes),
`frame.jpg.json`, `prediction.json` (5,081 bytes) and `prediction.html` (299,580 bytes).
The HTML was rendered/visually checked. It embeds the original photo, a separate
SVG top-view path and a coordinate table, with explicit assumed-state/no-command
labels. The matching-image digest prevents accidentally displaying another frame.
It requires no server or external assets and can be viewed on Jetson or Mac.
The room image contains private lab content and is not included in public docs.

## 10. Asynchronous cache and live shadow experiment

The synchronous demo uses one image for both current and semantic reference
inputs. It does not reproduce the paper's asynchronous system. Independent
`semantic_cache.py` instead maintains atomic semantic payload/reference pairs,
request identities, supersession/reset handling, separate capture/receipt clocks
and frame/age gates. Planar body displacement is expressed relative to reference
yaw; physical coordinate agreement and full SE(3) are not established. The cache
module alone starts no threads.

A numerical reuse test retained a 24-layer, 6,721,536-byte cache, matched the
zero-delay result exactly (0 maximum difference; tolerance 0.001 m), and ran
three same-image/assumed-state actions in 0.1186/0.1183/0.1181 s without changing
cache bytes. This was not live concurrency or a navigation evaluation.

Here "shadow" means computing and recording predictions without sending them
to actuators. Separate tools then ran a bounded two-container camera/semantic/action experiment:

| Quantity | Actual observation |
|---|---|
| Camera producer | 55 seconds, target 5 fps, 275 JPEGs, 39,668,458 bytes |
| Observer | 25 seconds after a 9.354-second load; 126 distinct latest observations |
| Semantic work | Two requests completed; first cache published at 12.659 s |
| Second semantic request | 12.815 s; finished after observer shutdown and was discarded |
| Shadow action outputs | 35, all while next semantic work was in flight |
| Action latency | Minimum 0.1308 s, median 0.15594 s, maximum 0.28275 s |
| Gaps | 65 no-cache skips; 26 skips after the diagnostic 20-second cache age limit |
| Accepted semantic ages | 13.05–19.98 s using receipt-time lower bounds |
| Errors / late discard | Zero reported errors; one late completion discarded |

Producer publication uses immutable JPEGs plus an atomic latest manifest; the
observer separates a bounded semantic worker and current-action execution with
CUDA streams. All state was assumed stationary. A short action time does **not**
establish an uninterrupted 6 Hz controller: long semantic startup/refresh gaps
and stale-cache rejection were observed. The 20-second limit was diagnostic,
not approval to navigate using 20-second-old semantics. Actual clock/frame/state
integration and robust degraded behavior remain. This is not full DynaNav,
training parity or a reproduction of paper-level robot results.
[Asynchronous runtime](asynchronous-runtime.md) gives the contracts and evidence.

## 11. SDK preparation and four-computer architecture

A separate `vln-b2-unitree:jp5` image was built using reviewed Unitree SDK2
source and CycloneDDS 0.10.2 native/Python components. An initial build failed
because build-tool metadata polluted runtime `pip check`; a separate build venv
resolved it. The offline verifier checks pinned source hashes, native mappings,
license/build metadata and exact 516-byte synthetic `SportModeState`
serialization/deserialization. It initializes **no DDS entity**, network or robot
client. The receive-only CLI help passed in that image.

The full SDK dependency declaration is **not** satisfied by that small image;
its state/IDL path only needs CycloneDDS and the standard library. This is
explicitly reported, not hidden by installing every camera/array package.
Synthetic serialization is not proof of B2 topic/type/domain/QoS compatibility.
See [Unitree runtime](unitree-runtime.md) for exact source/image pins.

| Computer/link | Current evidence and intended responsibility |
|---|---|
| Mac → external Jetson | SSH/RDP management over available network/Tailscale; optional development/results display |
| ZED → external Jetson | Direct USB; SDK/native binding → RGB → GPU model → local plan/report verified |
| External Jetson → B2 | Intended direct Ethernet/IP/DDS using SDK2; no actual link/state yet |
| Robot's onboard user Jetson | Reported separate computer; actual hardware, sensors, services and forwarding routes unknown |
| Black-box motion computer | Reported existing walking controller; exact hardware/API/ownership/command-loss behavior unknown |

ROS 2 can provide topics, tooling and sensor integration but is not necessary
merely because an SDK is used. SDK2 uses DDS in the planned state path; ROS 2
also commonly uses DDS, but matching middleware alone does not make types,
domains or topics compatible. Containers can communicate using explicitly chosen
network/IPC/files, not automatically. Current model tests use `--network none`;
future state reception requires a separate reviewed robot-facing configuration.
Never bridge campus traffic into B2 or replace the management default route
just to reach its Ethernet subnet. [Network topology](network-topology.md),
[field procedure](field-network.md) and [deployment choices](deployment-design.md)
explain the layers and pending inspection.

Direct external USB was selected for the first independently testable input,
not a permanent decision to discard B2 cameras/onboard compute. Internal sensors
may require a service/stream on the onboard Jetson and Ethernet delivery; they
cannot be treated as USB devices on the external Jetson. Livox and onboard
camera pipelines remain unconfigured. Their eventual use depends on measured
availability, timestamps, geometry, bandwidth and research needs.

The core loop is intended to run locally without Mac, eduroam or Internet.
A Jetson-provided local hotspot could later provide optional Mac monitoring
without an AP/Internet, but is not configured or tested. Robot remote control
is intended as an independent operator path; its priority/stop behavior must be
observed with the lab procedure, not assumed from the word "remote".

## 12. Validation and evidence boundaries

At this milestone **170 tests passed on both Mac and Jetson**. They exercise
validation, fake vendor interfaces, replay/tracking, time/cache contracts,
conversion/tool behavior and report rendering. Unit tests do not certify physical
navigation, camera lifetime reliability or stop performance. Source was checked
for syntax/diff issues, paired manuals/links and private material before local
commit/synchronization. No model weights, raw camera images, native SDK or
third-party model code are tracked. The new tools and docs do not introduce a
Mac service or an automatic model/control startup job.

Reference IDs retained for reproducibility include source revisions, immutable
image IDs, asset hashes and per-run local invocation/provenance. A valid model
output means finite numbers with the expected structure, not a successful
navigation instruction. Past reboots/captures are bounded observations; no
remaining failure mode is declared impossible.

## 13. Remaining milestones and first-connection acceptance

| Next milestone | Required evidence before advancing |
|---|---|
| M1: Ethernet/state only | Identify cable endpoints/onboard hosts; preserve management route; receive actual finite B2 state with explicit interface/domain/topic; zero motor commands |
| M2: physical observations | Mount camera; verify image direction, robot axes, units, velocity/position frames, timestamps and state/image alignment |
| M3: real-state shadow | Repeated live predictions using real aligned state; characterize startup/refresh gaps, stalls, stale/missing input and compute/thermal behavior |
| M4: control/stop integration | Confirm authority, remote priority, receiver expiry/connection-loss behavior; implement bounded sender, independent stop/expiry and operator intervention |
| M5: controlled motion/research | Supervised low-speed trials under lab procedure, stopping-distance/obstacle checks and predefined repeated evaluation |

The first onsite session should stop at M1 if identity, services or state mapping
remain unresolved. Use [the field card](field-card.md), prepared SDK image and
private visit-notes template; do not run an SDK motion example as a discovery
probe. Connecting Ethernet changes connectivity, not the implemented control
boundary. Camera inference can be demonstrated independently with
[the operating guide](run-camera-demo.md) while M1–M4 are completed.
