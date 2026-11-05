# System overview and unattended access

[日本語](system-overview.ja.md) · [Status](status.md) · [Runtime setup](jetson-runtime.md)

Current Mac policy (2026-11-01): use direct RDP to the Jetson Tailscale IPv4.
The operator creates the Windows App entry; no Mac tunnel, startup task, routing
change or new client is added. Existing Tailscale and foreground setup SSH are
retained; setup SSH closes after use. Jetson now has an address-readiness helper,
a retry drop-in for `b2-rdp.service` and one scoped INPUT rule for TCP 3389.
TLS, credentials, campus Wi-Fi and robot Ethernet are unchanged. Transport/TLS
passed from Mac; the operator confirmed the direct desktop on 2026-11-03.
A whole-device reboot under the latest settings remains a separate check. See [direct desktop setup](remote-desktop.md).

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
container's CUDA visibility passed. The completed runtime also passed eight
FP32/BF16 GPU-operation checks and upstream imports at that model-free stage.
Subsequent model loading, recorded-image timing and bounded camera shadow
inference passed; see [current status](status.md).

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
| `/opt/b2-remote/libexec/rdp-tailnet-ready.py`, `b2-rdp.service.d/tailnet.conf` | Jetson-only direct-RDP readiness/ingress guard and startup retry; private address file in the RDP config directory |
| `/mnt/b2-research/VLN_B2/models` | Private derived safetensors/manifest; ignored project `models` symlink |
| `/mnt/b2-research/VLN_B2/observations` | Private bounded camera experiment images and per-frame manifests |
| `local/camera-runtime/attempt-01` | Private pyzed/Cython prefix, dedicated calibration and camera check records; SDK remains read-only |
| `local/async-shadow`, `local/unitree-build`, `local/unitree-check-01` | Private experiment/build/offline-verification provenance and reports |
| `/mnt/b2-research/VLN_B2/huggingface` | Approved raw model assets; standard `~/.cache/huggingface` points here |

The initial Python setup added three development-header packages to the host:
`libbz2-dev`, `libncurses-dev`, and `libreadline-dev`; none was upgraded or removed in that initial step. On 2026-10-28 Tailscale alone
was upgraded to 1.104.4 after direct LAN SSH was verified. A separately compiled
RDP prefix, non-login `xrdp` service identity, `b2-remote-users` allow group,
`/etc/pam.d/xrdp-sesman` and dedicated `b2-rdp`/`b2-rdp-sesman` units were added.
Host TLS keys are root-owned and not stored in the repository. No xrdp APT
package, replacement Xorg, CUDA driver or new ROS installation was added.
The project is installed editable in its own venv. NVIDIA's base image and a
separate Python image were acquired/built in Docker; Torch/vision compilation
occurs there. CUDA, TensorRT, Docker, ROS and ZED already existed on the host.
Approved raw assets now live in the SSD-backed standard Hub cache; the private
derived safetensors/manifest use the SSD models area through the ignored project
models symlink. These are not host-venv packages or repository source.

System-wide changes are explicit: the SSD mount entry in `/etc/fstab`, Docker's
data root, and its mount guard under `docker.service.d`. Backups and the old
Docker store remain. The Wi-Fi profile now retries autoconnection indefinitely;
its old profile is backed up. Research-login automatic AC suspend is disabled.
GUI boot remains enabled. A later controlled software reboot verified automatic
recovery on the then-active Wi-Fi; see the boot checks below.


On 2026-11-03, the requested ARM64 VS Code editor was added as the single
new host package `code` (1.144.1); no other installed package version changed
in that transaction. The Microsoft APT source was declined. The RDP server
was also changed from clipboard-disabled defaults to text-only bidirectional
transfer, without closing existing sessions. See [the operator procedure](remote-desktop.md).
Private evidence and configuration backups are in `local/editor-setup-01`.

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
candidate model runtime. The camera uses a separately verified private binding
prefix with read-only native SDK and container-only groups. A separate Unitree
state-only image passed offline imports/serialization. Neither installs vendor
packages into the host venv. Actual B2 state acquisition remains unverified; see
[camera setup](camera-runtime.md) and [state environment](unitree-runtime.md).

## GUI and unattended boot

Keep `graphical.target` and the desktop for local recovery. The inspected main
GUI processes had a combined RSS of about 0.7 GiB; this is not a controlled
measurement of the desktop's extra cost and may count shared pages more than
once. On this 64 GB system, CLI-only boot is not currently required.

The desired sequence is power-on → Ubuntu → system Wi-Fi → Tailscale → SSH.
GUI automatic login is optional for network services, though useful for local
operation. NetworkManager, tailscaled and SSH are already enabled and active.
For the earlier Mac screen test, [remote desktop](remote-desktop.md) used
Windows App/RDP with the installed host xrdp server. The server is installed under `/opt/b2-remote`
and running; Windows App authentication/desktop display and operator-reported
basic interaction passed. RDP boot startup is enabled, with sesman as a required
dependency. An HDMI-disconnected software reboot restored Wi-Fi, Tailscale,
SSH and RDP services without manual reconnection; SSD mount and Docker startup
also passed. The active Wi-Fi was non-enterprise, so this is not an eduroam
boot result. A subsequent eduroam switch and second headless software reboot
also passed, with operator-confirmed RDP display/input. A physical power-cycle
test remains pending. Existing Vino is stopped.
Tailscale retains login state; it does not normally require `tailscale up` on
every boot. Its node-key expiry must still be checked in the
[Tailscale admin console](https://tailscale.com/docs/features/access-control/key-expiry).

The enterprise Wi-Fi profile inspected on 2026-10-27 initially used a user secret agent
(`password-flags=1`) and was restricted to a login. Its password was unavailable
through NetworkManager's settings cache. A later 2026-10-28 inspection found
that the then-active Wi-Fi profile had no 802.1X settings. Do not transfer the
earlier enterprise-profile conclusions to a different active connection. The
helper refuses credential changes on a non-PEAP profile. Identify the intended
eduroam profile again before any credential operation. A login-independent enterprise configuration needs
one local password entry, in either a physical terminal or the operator's own
interactive SSH terminal. Do not send the password to a chat or put it in a command.
By default the helper edits the active profile. To select a saved inactive
profile, add `--connection-id SAVED_PROFILE_NAME`; the name must match exactly
one connection. Neither mode activates the connection. Do not switch Wi-Fi just
to select a profile. The remote-desktop guide describes both GUI and terminal
procedures.

```sh
cd ~/Developer/Projects/Robotics/b2/VLN_B2
sudo /usr/bin/python3 tools/configure_unattended_wifi.py --apply
```

The helper shows the configured enterprise account and asks for the password
twice without echo. It preserves identity,
CA, EAP method and server-check settings, saves the password in NetworkManager's
root-protected system profile and enables system-wide automatic connection.
It backs up settings and does not restart
Wi-Fi, GDM, Tailscale or the host. Root administrators can read system-stored
credentials; this is not storage isolated from the device administrators.
Read-only inspection is available without `--apply`. GUI automatic login is a
separate, optional choice: append `--autologin RESEARCH_USER` only if explicitly
desired, replacing the placeholder with the intended regular login. That change
occurs only after credential saving succeeds. Prefer leaving the desktop login
protected on a shared device; boot Wi-Fi/Tailscale/SSH does not need autologin.

For future changes, perform a controlled reconnect with timed or local recovery.
The completed eduroam reconnect and software-reboot evidence is recorded below.
A physical power-cycle test still needs someone present with console recovery.
Do not interrupt running work. Configuration alone does not prove recovery.
Network coverage, campus authentication and expired credentials remain external
dependencies. Preserve the university's [official Wi-Fi setup](https://kb.wisc.edu/ns/page.php?id=25020)
and [NetworkManager's credential/trust settings](https://networkmanager.dev/docs/api/latest/settings-802-1x.html).

The stock developer kit [normally powers on when power is applied](https://docs.nvidia.com/jetson/agx-orin-devkit/user-guide/latest/howto.html).
Actual J42 jumper state, power supply, polarity, voltage and capacity must be
checked physically. B2 battery/output specifications are still unknown; do not
infer compatibility from a connector or connect an unverified robot supply.
Automatic login does not make motors or this project start automatically.

## UWNet portal registration versus eduroam

The first non-enterprise reboot test used UWNet. A later credential save,
network switch and second reboot verified eduroam. These are sequential
observations, not contradictory reports of the same connection. The saved UWNet
profile remains; retaining a profile is not proof of Internet authorization.

| Location | Possible state | What has been established |
|---|---|---|
| Host NetworkManager | UWNet SSID, autoconnect, network parameters; an open network does not need the university password as a Wi-Fi secret | The prior UWNet profile was non-enterprise and remains saved |
| Browser/keyring | Saved passwords, cookies and login history depending on browser choices | Not inspected; entering a portal password does not prove it was or was not saved locally |
| University systems | Device MAC-to-account registration, expiry and authentication/access records | UW documents account-linked device registration; this device's portal record was not inspected |
| eduroam host profile | Enterprise identity, trust configuration and system-stored password | This setup verified system-wide PEAP autoconnect and password retention; root administrators can read the secret |

Using the same university credentials does not make the two authentication paths
the same. UWNet's portal authenticates an account and authorizes the device;
eduroam authenticates during enterprise Wi-Fi connection. According to
[UWNet's browser-registration guide](https://kb.wisc.edu/helpdesk/22915), campus
affiliate registration lasts through the current semester and associates the
MAC address with the NetID. This is distinct from the
[manual device-registration procedure](https://kb.wisc.edu/ns/79140), whose
renewal sets a six-month expiry. Do not apply either interval to every guest or
assume this device's exact expiry without checking its registration.

The university [describes UWNet as unencrypted and eduroam as encrypted](https://chemconnect.wisc.edu/comphelp/chemistry-network/).
HTTPS and SSH can still encrypt their application connections on UWNet; an
open Wi-Fi link does not by itself prove portal credentials were exposed.
Conversely, browser logout, deleting a Wi-Fi profile and deleting a university
registration are different operations. None proves that all institutional logs
were erased. Actual server-side password representation and retention are not
observable here; do not claim that the university stores plaintext passwords
or that entering a password leaves no record. For an approved shared identity,
usage remains associated with that identity; verify institutional authorization
rather than assuming sharing is allowed. Review saved browser credentials and
device registration at handover, preserving approved research files and avoiding
unapproved removal of another account's registrations.

Automatic reconnection still requires power, valid credentials, network coverage
and working Tailscale authorization. Mounting Jetson on B2 supplies no new Wi-Fi
coverage. Future inference/control must operate locally without a persistent Mac
connection; the robot Ethernet link and local stopping behavior are separate
field tests.

## Personal credentials, sharing and return

UW's [official eduroam instructions](https://kb.wisc.edu/ns/page.php?id=25020)
use the individual's NetID email and NetID password. System saving puts that
password in a root-protected NetworkManager profile; it is not encryption against
administrators. The [keyfile documentation](https://networkmanager.dev/docs/api/latest/nm-settings-keyfile.html)
explicitly allows plaintext secrets in files that must be protected from other
users. A sudo user or a privileged container with access to those files can read
them. A separate Linux login, venv, or ordinary container does not protect a
personal university password from the host's administrators. Do not put the
profile in this repository, an image, a general backup or a support log.

The saved eduroam profile initially used a user secret agent and a login
restriction. The owner later entered the password in their own SSH terminal;
the helper made the profile system-wide with autoconnect, indefinite retries
and password flags 0. A privileged check confirmed a stored non-empty secret
without displaying it. The existing user keyring was not inspected or cleared.
The CAT CA bundle includes USERTrust RSA Certification Authority and retains
its explicit DNS alternative-subject match. Earlier reporting based only on
empty domain-match fields missed that alternative server-name check. No CA or
server check was disabled or replaced. The helper preserves trust settings;
it does not independently certify that an arbitrary profile is correct.

A 180-second NetworkManager rollback protected the initial switch from the
working Wi-Fi to eduroam. Fresh Tailscale SSH, full connectivity and management
services passed, so the checkpoint was canceled. A second HDMI-disconnected
software reboot connected to eduroam automatically; fresh SSH returned at about
24 seconds of target uptime. A changed boot ID, all enabled/active management
services, SSD mount, SSD Docker data root and loopback-only RDP were verified.
The owner confirmed RDP display and input again. GUI autologin was not changed.
This is an observed software-reboot result, not a physical power-cycle result
or a guarantee of campus coverage, credential validity or Tailscale policy.

For later reconfiguration, finish running jobs and arrange console or timed network recovery:

1. Use the operator's own approved eduroam identity during dedicated use; do not
   reuse another researcher's password. Verify the actual profile, official
   CA/server checks and sudo access before system saving. Enter secrets only
   in the operator's terminal, never in a chat.
2. If accepted, save boot Wi-Fi credentials using the helper. Decide GUI login
   separately; its existing target belongs to another login and is unchanged.
3. Reconnect and then test a planned cold boot without anyone logging into the
   desktop. Verify Wi-Fi and Mac-to-Jetson Tailscale SSH. This proves the actual
   sequence; a boot message or current connection does not.

Before shared use, ask campus/lab IT for an approved shared-device connection or
device authentication; do not assume a shared eduroam account is available or
share a personal NetID password. Give researchers individual logins, reconsider
sudo membership and replace temporary weak login passwords. Keep GUI autologin
off for shared access. These policy/credential changes have not been applied.

The accepted return review covers both the research login and the pre-existing
lab login: UWNet portal authentication happened in the latter before the research
login was created. Browser cookies/passwords, web sessions and keyrings may
therefore belong to that earlier home directory. A new login does not relocate
or clear them. Review that account with its owner/administrator, remove only
identified personal access when return/sharing is requested, and preserve lab
files and unrelated users' secrets. No browser/keyring cleanup has been done.

At handover or return, arrange console access and replacement networking first.
The following is a review plan, **not an automated cleanup already performed**.
When sharing/return is requested, preserve approved research files, installed
runtimes and useful environments. Inventory personal access and credential
copies, identify the exact removal/revocation targets and clarify ambiguous
ownership or retention before acting. A full disk wipe is not the default.
Browser logout and deleting an SSH key alone do not remove Wi-Fi secrets,
root-only backups or server-side access registrations:

- Disconnect and remove the personal Wi-Fi profile; review user keyrings,
  NetworkManager/wpa_supplicant settings, root-protected profile backups including
  `/etc/NetworkManager/vln-b2-backups`, and any system backups for credential copies.
  Do not restore an old profile backup containing that identity.
- Log out of the personal Tailscale enrollment and remove/reassign the node in
  the [admin console](https://tailscale.com/docs/features/access-control/device-management/how-to/remove).
  Merely stopping Tailscale or deleting a Linux account does not complete this.
- Review SSH keys/authorized access, Git credentials, tokens, browser/keyring
  sessions and autologin. Transfer research files under their applicable terms;
  remove personal access with the owner/administrator's agreement.
- Verify after reboot that the old university identity and personal tailnet no
  longer reconnect. If credentials may have been copied or backup removal cannot
  be established, rotate them through the university's official process and
  revoke applicable tokens. SSD file deletion alone is not proof of sanitization.

Do not disconnect or remove credentials remotely while they are the only recovery
path. No account deletion, credential rotation or data erasure has been done here.

For source synchronization, the upstream/model boundary and the layer-by-layer
communication path, read [the runtime flow guide](runtime-flow.md).

## Computers and current connection

The working path is Mac → external Jetson → USB Ethernet → onboard Intel i7.
The i7 has a separate internal Ethernet interface, where the temporary ROS 2
program received robot state/video and obtained the single already-damped
response. External direct DDS remains unresolved; model inference runs on the
external Jetson. [The step-by-step explanation](network-topology.md) distinguishes
this measured path from the official i5/i7 standard configuration and the
unconfirmed additional Jetson. That chapter also explains IP addresses,
SDK/ROS 2/DDS, versions and the earlier Docker forwarding problem.

[The field procedure](field-network.md) contains commands for the next visit.
Identify the actual network access point and inspect missing software/firewall
facts before selecting a direct SDK connection or an application relay.

## Diagnosing access loss and desktop failures

The 2026-11-03 inspection separated three observations rather than treating a
popup, lost connectivity and a desktop freeze as one proven fault:

- Before the operator's restart, persistent syslog recorded repeated eduroam
  association/authentication timeouts. NetworkManager explicitly said stored
  secrets existed, requested new secrets and finally failed with `no-secrets`.
  That final reason alone does not prove the saved password was absent or wrong.
  After restart the same stored profile completed PEAP and connected before the
  desktop login. AP/authentication-service/supplicant responsibility remains
  unresolved. No Wi-Fi credentials, CA checks or retry settings were changed.
- The legacy desktop account was the previously retained autologin target.
  The operator changed it to the research account after restarting; the agent
  did not make that change. Before restart Linux login authentication had
  succeeded, followed by a GNOME FIFO warning and XRDP audio environment values
  in the local desktop launch. Session residue/conflict is a hypothesis, not a
  proven freeze cause. Current local and RDP GUI sessions share one account;
  avoid assuming that a disconnected RDP client has logged that session out.
  No session was terminated, GNOME reset or graphics driver replaced.
- One pending crash report belonged to the project's **intentional readiness
  failure test** on 2026-11-01. An unhandled expected exception had invoked the
  host crash-report mechanism. The helper now catches expected address/file/
  subprocess failures, logs a concise diagnostic and exits 1 for systemd retry.
  Its own identified old test report was archived privately; an unrelated older
  browser report was left alone. Which report the operator's popup displayed
  was not independently observed. The helper failure does not explain Wi-Fi loss.

Journal storage was volatile and held only the current boot. Persistent syslog
and authentication logs supplied partial previous-boot evidence; raw excerpts
stay in ignored `local/access-incident-20261103-01`. The boot clock was corrected
by time synchronization. A Tailscale message describing a large apparent sleep
interval during that correction is not independent proof of physical suspend.
Use monotonic time within a boot and verify time corrections before interpreting
cross-boot wall-clock durations. Both inspected desktop accounts currently had
AC suspend action `nothing`; that does not reconstruct earlier settings.

For a recurrence, preserve current/previous boot availability, NetworkManager/
supplicant messages and login/session state before restarting if possible. Read
crash **metadata** first; do not upload reports, collect browser content or print
network passwords. Check the exact active connection and secret-storage flags
without displaying secrets. Distinguish missing credentials, authentication
failure and failure to obtain an IP. Keep peer identities and raw logs private.
The [upstream XRDP discussion](https://github.com/neutrinolabs/xrdp/issues/2027)
is a related GNOME/FIFO case, not proof that this device has the same cause.
The expected-failure handler and installed-helper check passed, with all 164
ordinary tests passing on Mac and Jetson. Recovery after one restart does not
establish automatic recovery from a future eduroam authentication stall.


A later screen inspection on the same day captured the actual generic
`update-notifier` system-program-problem dialog. The sole remaining crash file
was an older Chrome SIGTRAP report dated 2026-10-28. The dialog itself did not
identify a newly failing component or establish Chrome's detailed crash cause.
No report was uploaded and the browser report was not deleted. At the operator's
request, only the physical research GUI session was logged out after saving the
window evidence. The remote GUI and SSH were preserved; GNOME and an EWMH window
manager then became available on the RDP display. The operator subsequently
confirmed client-side desktop access. Persistent GUI autologin was left unchanged, so this one-time
logout does not prevent console/RDP overlap after a future automatic login.


## Manual updates and desktop notifications

After the notification-only change described below, a separate operator-authorized
maintenance transaction on **2026-11-03** refreshed APT indexes and upgraded
OpenSSH client/server/SFTP from `1:8.2p1-4ubuntu0.12` to `1:8.2p1-4ubuntu0.13`,
and Chrome from `156.0.8078.47-1` to `156.0.8078.79-1`. No additions/removals
or other installed version changes occurred; SSH configuration and service
checks passed. GPU images, JetPack/CUDA and kernel were preserved. Additional
Ubuntu 20.04 fixes can require the lab's ESM entitlement; no subscription was
attached. This is not complete security coverage. See [the maintenance record](milestone-2026-11-03.md#6-maintenance-applied-on-2026-11-03).

The external Jetson deliberately retains Ubuntu 20.04, JetPack 5.1.2 / L4T
35.4.1 and CUDA 11.4 for the measured runtime. Host release/kernel/GPU updates
need a compatibility and recovery plan; a container does not isolate them from
host driver changes. NVIDIA documents coupled BSP packages and the release's
supported update paths in its [35.4.1 update guide](https://docs.nvidia.com/jetson/archives/r35.4.1/DeveloperGuide/text/SD/SoftwarePackagesAndTheUpdateMechanism.html).
This is not a claim that all security updates are unnecessary.

Inspection on 2026-11-03 found release prompting already set to `never`, no
installed unattended-upgrades service, daily package-index refreshing enabled
and no package holds. A simulation using the existing local index proposed
143 upgrades, no additions/removals; no package transaction or fresh index
refresh was executed for this notification change. That cached proposal is not
a current vulnerability audit or a compatibility approval. Cache refresh and
notification are different from automatic package installation.

The installed `update-notifier` 3.192.30.19 launches Update Manager before its
`no-show-notifications` branch. Inspection of the matching
[official Ubuntu source archive](https://ports.ubuntu.com/ubuntu-ports/pool/main/u/update-notifier/update-notifier_3.192.30.19.tar.xz)
showed that changing that GSettings key alone would not suppress automatic
updater windows. Its source archive/hash and selected settings were retained
privately, without modifying the packaged executable.

The operator explicitly selected suppression of **both update and crash-report
GUI notifications**. A research-account-only override at
`~/.config/autostart/update-notifier.desktop` copies the system desktop entry
and sets `Hidden=true`. The running research-account notifier was stopped.
The [XDG autostart specification](https://specifications.freedesktop.org/autostart/latest/)
defines this user-level override. The desktop file validated with only its
inherited deprecated-Encoding warning; no updater GUI process remained. Other
accounts and the system autostart file were unchanged. No background monitor,
Mac setting, package removal or replacement update service was added.

Crash collection, `/var/crash`, journal/syslog and manual analysis remain.
New crash reports will no longer automatically prompt through this notifier in
this research GUI. RDP, Tailscale and Wi-Fi notification/authentication services
are separate. This does not prohibit deliberately launching a manual updater or
running APT. Existing cache-refresh timers remain unchanged.

APT can still be used, as described in [Ubuntu's package guide](https://ubuntu.com/server/docs/how-to/software/package-management/).
`apt update` refreshes the index; it does not upgrade installed software. First
inspect candidates, then simulate and review a **selected** package transaction:

```sh
sudo apt update
apt list --upgradable
sudo apt-get -s install --only-upgrade PACKAGE_NAME
```

Only after reviewing versions, dependencies, restarts and recovery, apply the
selected transaction:

```sh
sudo apt install --only-upgrade PACKAGE_NAME
```

`PACKAGE_NAME` is a placeholder, not a literal command target. Do not substitute
an unreviewed bulk `upgrade`, `full-upgrade`, generic desktop NVIDIA driver or
Ubuntu release upgrade for Jetson maintenance. BSP/CUDA/ROS/ZED changes and
security patches require their own reviewed scope and appropriate checks.
Local GPU images and Python model dependencies are separate versioned artifacts;
updating host APT does not update those images or their pinned model inputs.

Private before/applied/verified records are in `local/update-policy-01`. To undo
this GUI policy, restore the prior user override if one existed, or remove only
the newly created user override and log in again. No previous override existed
on this target. Retain the system file and do not alter crash logs to restore
notification behavior.
