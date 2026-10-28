# System overview and unattended access

[日本語](system-overview.ja.md) · [Status](status.md) · [Runtime setup](jetson-runtime.md)

## Verified external Jetson

Inspection on 2026-10-27 identifies a Jetson AGX Orin Developer Kit, 64 GB class.

| Item | Configuration and evidence |
|---|---|
| CPU | 12 Arm CPU cores online; maximum reported clock 2.2016 GHz; the AGX Orin specification identifies Cortex-A78AE |
| GPU | NVIDIA Ampere; 16 streaming multiprocessors, corresponding to 2048 CUDA cores and 64 Tensor cores; compute capability 8.7; reported maximum GPU clock 1.3 GHz |
| Memory | 64 GB class; Linux reports approximately 61.3 GiB. CPU and GPU share this memory; there is no additional dedicated 64 GB VRAM |
| Published capability | Up to 275 sparse INT8 TOPS and 204.8 GB/s LPDDR5 bandwidth for this class; manufacturer limits, not a TIC-VLA measurement |
| Current power mode | MAXN, already configured before this project; not a measured power consumption |
| OS storage | Approximately 64 GB eMMC, device `mmcblk0`; root filesystem approximately 60.8 GB, approximately 20.3 GB available |
| Research storage | Samsung SSD 990 PRO 2 TB NVMe, PCIe 4.0 x4 link observed; approximately 933 GB available after initial setup, changing during builds |
| Wi-Fi | Realtek RTL8822CE 802.11ac PCIe adapter; currently used for management |
| Robot Ethernet | No carrier observed; B2 remains disconnected |
| Software | Ubuntu 20.04.6, L4T 35.4.1 / JetPack 5.1.2 family, CUDA 11.4, TensorRT 8.5.2; existing ROS Foxy directory and ZED SDK 4.1.2 headers |

See [NVIDIA's specifications](https://developer.nvidia.com/embedded/jetson-developer-kits)
and [AGX Orin technical brief](https://www.nvidia.com/content/dam/en-zz/Solutions/gtcf21/jetson-orin/nvidia-jetson-agx-orin-technical-brief.pdf).
No storage-speed, sustained power, or TIC-VLA frame-rate benchmark has been run.
Native CUDA arithmetic, arithmetic in the matching base container, and the Python
container's CUDA visibility passed; the full model runtime is a separate stage.

## Storage and changes made

There is one eMMC device and one NVMe SSD, rather than two SSDs. The eMMC holds
Ubuntu, drivers, account files, source and the small host Python environment.
Large Docker layers, builds and the standard model cache use the SSD.

The SSD initially contained about 1 TB of allocated data and reported
`needs_recovery`. This is a journal-recovery indication, not evidence by itself
of a failed SSD. Initial inspection used `ro,noload` to avoid replay writes.
After explicit operator permission, normal mounting replayed the journal;
no ext4 error was observed. It is now writable and in use. No format or deletion
of previous data occurred. See [storage procedure](jetson-runtime.md#storage-prerequisite).

| Location | Created or configured for this project |
|---|---|
| `~/Developer/Projects/Robotics/b2/VLN_B2` | Reviewed source archive; `.venv` for the project, ignored `local/` for logs and native checks |
| `~/Developer/External/pyenv` | Pinned interpreter-management source |
| `~/Developer/External/TIC-VLA` | Pinned, restricted upstream source-only checkout; outside the public project |
| `~/Developer/Environments/pyenv/versions/3.11.18` | Per-user Python, separate from system Python 3.8 |
| `/mnt/b2-research/VLN_B2/docker` | New shared Docker-daemon data root on the SSD |
| `/mnt/b2-research/VLN_B2/build-logs` | Image-build logs and model-free check results |
| `/mnt/b2-research/VLN_B2/huggingface` | Empty model-cache directory; `~/.cache/huggingface` points here |

Only three development-header packages were added to the host:
`libbz2-dev`, `libncurses-dev`, and `libreadline-dev`; none was upgraded or removed.
The project is installed editable in its own venv. NVIDIA's base image and a
separate Python image were acquired/built in Docker; Torch/vision compilation
occurs there. CUDA, TensorRT, Docker, ROS and ZED already existed on the host.
No model weights have been acquired.

System-wide changes are explicit: the SSD mount entry in `/etc/fstab`, Docker's
data root, and its mount guard under `docker.service.d`. Backups and the old
Docker store remain. The Wi-Fi profile now retries autoconnection indefinitely;
its old profile is backed up. Research-login automatic AC suspend is disabled.
GUI boot remains enabled. No reboot or network disconnection was requested.

## What is isolated

- **Linux login:** separates home files, credentials and ordinary permissions.
  The research login has sudo and can change the entire host. It is not a strong sandbox.
- **Python venv:** separates this project's Python packages. It does not restrict
  filesystem, network or GPU access by Python code.
- **Docker:** supplies a separate application filesystem and dependencies.
  Containers still share the host kernel and use its NVIDIA driver. The Docker
  daemon is shared, and sudo Docker access is powerful. Tests mount only their
  required inputs; model-free runs have no network and send no robot commands.

See the [Docker security model](https://docs.docker.com/engine/security/).

An image is the application environment template; a container is a running
instance. Building a Torch image does not install Torch into every host user's
Python. The host venv is for project tools, while the GPU image is for the
candidate model runtime. Existing SDK permissions and binding compatibility
still need checking before camera/state acquisition.

## GUI and unattended boot

Keep `graphical.target` and the desktop for local recovery. The inspected main
GUI processes had a combined RSS of about 0.7 GiB; this is not a controlled
measurement of the desktop's extra cost and may count shared pages more than
once. On this 64 GB system, CLI-only boot is not currently required.

The desired sequence is power-on → Ubuntu → system Wi-Fi → Tailscale → SSH.
GUI automatic login is optional for network services, though useful for local
operation. NetworkManager, tailscaled and SSH are already enabled and active.
Tailscale retains login state; it does not normally require `tailscale up` on
every boot. Its node-key expiry must still be checked in the
[Tailscale admin console](https://tailscale.com/docs/features/access-control/key-expiry).

The active enterprise Wi-Fi profile currently uses a user secret agent
(`password-flags=1`) and is restricted to a login. Its password is unavailable
through NetworkManager's settings cache. A login-independent configuration needs
one local password entry, in either a physical terminal or the operator's own
interactive SSH terminal. Do not send the password to a chat or put it in a command.

```sh
cd ~/Developer/Projects/Robotics/b2/VLN_B2
sudo /usr/bin/python3 tools/configure_unattended_wifi.py --apply --autologin RESEARCH_USER
```

Replace `RESEARCH_USER` with the actual research login. The helper shows the
configured enterprise account and asks for the password twice without echo. It preserves identity,
CA, EAP method and server-check settings, saves the password in NetworkManager's
root-protected system profile, enables system-wide automatic connection, and
selects the requested regular GDM login. It backs up settings and does not restart
Wi-Fi, GDM, Tailscale or the host. Root administrators can read system-stored
credentials; this is not storage isolated from the device administrators.
The automatic-login change is deliberately coupled to successful credential saving.
Read-only inspection is available without `--apply`.

After saving, perform a controlled reconnect and cold-boot test with someone
present and local console recovery available. Do not interrupt the active source
build. Until this test passes, unattended access is configured, not proven.
Network coverage, campus authentication and expired credentials remain external
dependencies. Preserve the university's [official Wi-Fi setup](https://kb.wisc.edu/ns/page.php?id=25020)
and [NetworkManager's credential/trust settings](https://networkmanager.dev/docs/api/latest/settings-802-1x.html).

The stock developer kit [normally powers on when power is applied](https://docs.nvidia.com/jetson/agx-orin-devkit/user-guide/latest/howto.html).
Actual J42 jumper state, power supply, polarity, voltage and capacity must be
checked physically. B2 battery/output specifications are still unknown; do not
infer compatibility from a connector or connect an unverified robot supply.
Automatic login does not make motors or this project start automatically.

## Four computer roles and the next steps

```text
Mac -- Wi-Fi/internet + Tailscale/SSH --> External AGX Orin
                                                |
                                    planned robot Ethernet
                                                |
                                   B2 internal network (unknown)
                                      /                 \
                           reported onboard Jetson   motion-control system
                           sensor/localization?       existing walking/balance
```

Only the Mac–external-Jetson connection is verified. Internal identities,
services and cable endpoints remain unverified. Unitree's
[B2 specifications](https://www.unitree.com/b2/) list Intel platform/development
computers and optional Orin NX configurations; they do not identify this lab's
installed configuration. The [published B2 SDK](https://github.com/unitreerobotics/unitree_sdk2/blob/main/include/unitree/robot/b2/sport/sport_client.hpp)
supports the proposed high-level command path, not a claim of successful control.

The goal is external perception/planning with the existing B2 walking controller.
This may require modifying only the external Jetson if state, sensor and motion
services are accessible. It does not grant access to every robot function.
The robot Ethernet link is local wiring, separate from a campus wired network.
Campus Ethernet availability is not a prerequisite for that link. SDK2 uses DDS;
ROS 2 is optional on the external host. See [network design](network-topology.md).

Finish the GPU runtime checks and unattended-access test, then agree on model
assets/loading, map the actual onboard computers and sensor connections, receive
images/state without commands, and validate command ownership and independent
stopping before controlled motion. Keep the onboard software intact until its
role and interfaces are understood.
