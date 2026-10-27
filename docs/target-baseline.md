# External Jetson baseline

[日本語](target-baseline.ja.md) · [Status](status.md) · [Network design](network-topology.md)

This is the initial survey snapshot. Subsequent interpreter, venv, native GPU
and storage-inspection work is recorded in [runtime setup](jetson-runtime.md).

Read-only inspection on **2026-10-27** established the external compute baseline
below. SSH from Mac over the Tailscale network worked. The prepared inspector
ran from standard input in the target's Python 3.8 environment; no project,
package, model, disk mount, or network configuration was created by this inspection.
A privileged Docker metadata query was also performed. Actual usernames, device
names, addresses, MACs, serials, filesystem identifiers, and authentication data
are omitted from this public-facing record.

## Observed compute and software

| Item | Observation | Evidence boundary |
|---|---|---|
| Module | Jetson AGX Orin Developer Kit, 64 GB class | Device-tree model; Linux-visible total RAM is about 61.3 GiB |
| Architecture | aarch64 | Target kernel/platform |
| OS | Ubuntu 20.04.6 LTS | Installed OS metadata |
| Kernel / L4T | 5.10.120-tegra / 35.4.1 | Kernel and installed `nvidia-l4t-core` |
| JetPack family | Corresponds to JetPack 5.1.2 | Version association, not a present `nvidia-jetpack` meta-package |
| CUDA | 11.4 runtime; compiler 11.4.315 | Installed packages and compiler version |
| CUDA device query | `cuInit` succeeded; one Orin GPU; driver API reports 11.4 | Driver initialization/query only, not a PyTorch or inference benchmark |
| TensorRT | 8.5.2 packages | Runtime execution not tested |
| Default Python | CPython 3.8.10 | Current research login's interpreter |
| Python packages | No Torch/Transformers distribution metadata in this interpreter | Other environments and existing containers were not searched |
| pyenv | Not present at the new login's conventional location | No interpreter installed by this inspection |
| ROS | Existing `/opt/ros/foxy` directory | No ROS graph, node operation, or DDS connectivity tested |
| ZED | Existing `/usr/local/zed` directory | Version, binding import, and camera capture not tested |
| Execution context | Host systemd environment; container detection reports none | Container-marker and virtualization checks |

NVIDIA associates [L4T 35.4.1](https://developer.nvidia.com/embedded/jetson-linux-r3541)
with [JetPack 5.1.2](https://developer.nvidia.com/embedded/jetpack-sdk-512).
Preserve the distinction between installed package metadata, a working GPU-driver
query, and a validated model runtime.

## Docker and storage

Docker client and server **26.1.3** are present. A privileged query confirmed
registered `nvidia`, `runc`, and `io.containerd.runc.v2` runtimes, with `runc` the
default. This does not establish GPU access inside a container. No image was
pulled, container started, daemon setting changed, or group membership modified.

The research login has sudo/video/render membership but lacks access to the
standard Docker socket. A nonprivileged `docker info --format` returned exit 0
with empty server fields while reporting a permission error. The inspector now
recognizes Debian build suffixes and reports the local socket permission issue
explicitly rather than presenting Docker as absent. Administrator invocation
works; the future container workflow must choose appropriate access explicitly.

The root filesystem is roughly **61 GB total with 20 GB free** at inspection.
A separate **2 TB NVMe SSD with an ext4 partition is present but unmounted**.
Read-only filesystem metadata reports approximately **1.05 TB free** and
**0.95 TB allocated**, including filesystem overhead. It is not an empty disk.
The superblock reports `clean` together with the `needs_recovery` feature;
these values do not establish filesystem health or permission to reuse its data.
Contents and ownership remain uninspected. No matching persistent-mount entry
was found. No formatting, mounting, relocation or shared Docker-storage changes
occurred. Establish model-cache, image/build, and project storage before large
downloads; a new home alone does not create more space or a separate disk.

Docker reports zero images and zero running containers, with its data root on
the small root filesystem. Stopped containers and volumes have not been audited.
The research login has no project workspace or Hugging Face cache yet. Preserve
existing data and inspect storage before creating large caches or changing the
shared Docker daemon.

## Observed management network

| Interface role | Observation |
|---|---|
| Wi-Fi | `wlan0` active; supplies the default route |
| Tailscale | `tailscale0` present; SSH management verified |
| Robot-facing wired port | `eth0` administratively up but without carrier or IP address |
| Existing USB bridge | `l4tbr0` with `rndis0` / `usb0`; inactive in this inspection |
| Docker virtual bridge | `docker0` present; no active carrier observed |

This is not a Wi-Fi-to-robot bridge configuration. No B2 state, robot address,
service domain, internal switch layout, or onboard computer role has been
verified. DDS/ROS environment variables were not set in this login session;
that does not describe every service or another user's environment.

## Runtime selection implications

The project package currently requires Python 3.10+, whereas the host default is
3.8.10. Select a compatible application interpreter/container while preserving
system Python and vendor software. The standalone inspector supports Python 3.8
and has now executed on the target.

The inspected [upstream training requirements](https://github.com/ucla-mobility/TIC-VLA/blob/main/requirements-train.txt)
pin Torch 2.8.0 with CUDA 12.8. They are not a deployment recipe for this CUDA
11.4 Jetson. Training pins do not establish the minimum required inference
versions or prove that a host upgrade is mandatory. An inference-only compatible
combination still needs to be tested; the [compatibility review](runtime-compatibility.md)
records a candidate and its limitations. Containerization alone does
not resolve the mismatch.

## Next implementation sequence

1. Establish storage preserving the existing ext4 contents and other accounts.
   Identify the intended SSD use before creating dedicated research directories;
   no formatting is part of this plan. Keep model acquisition in official caches.
2. Choose a Jetson-compatible GPU/Python/PyTorch candidate. Preserve the current
   OS, ROS and ZED installation while evaluating it. Any major host/boot-stack
   upgrade needs a separate concrete migration and recovery plan.
3. Test the selected container's Python version, GPU initialization, tensor
   operations and resource use before model loading. Keep command output separate
   from robot operation; no model file has been downloaded yet.
4. Resolve asset terms/revisions, size and cache location before downloading the
   base model and checkpoint. Then run synchronous inference on approved inputs.
5. Later connect B2 over its documented Ethernet interface, establish its actual
   service/domain, and validate state/camera timing before control integration.

The local suite now contains **85 passing tests**, including Docker parsing and
permission regressions. The revised inspector was exercised on the target's
Python 3.8. Model inference, container GPU execution, ZED capture, and B2 control
remain unverified.
