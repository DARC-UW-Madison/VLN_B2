# Remote desktop from Mac

[日本語](remote-desktop.ja.md) · [Documentation](README.md) · [System overview](system-overview.md) · [Field procedure](field-network.md)

Use SSH for ordinary terminal work. Prepare RDP as the preferred option for the
occasional graphical settings task, with Microsoft's Windows App on Mac and an
xrdp server on Jetson. The pinned server is installed, running and enabled at
boot. Authentication and desktop display passed on 2026-10-28; the operator
subsequently confirmed basic interaction. Settings permission, extended input
checks, reconnect and cold-boot acceptance remain separate checks. RDP has not
been measured against VNC on this Jetson, so the preference is not a claim that
it is more stable. Remote desktop is a management tool; inference and future
robot control must run locally without requiring a desktop connection.

## What is currently known

Read-only inspection on **2026-10-27** found Ubuntu 20.04 / L4T 35.4.1, Vino
3.22 installed, no running `vino-server`, and no TCP listener on 5900 or 3389.
xrdp, xorgxrdp and gnome-remote-desktop were absent. The graphical boot target
and an existing GUI autologin for a different account were retained. No new
remote-desktop service, authentication setting or GUI login target was enabled.
These are historical observations, not a fresh service-health check.

A management SSH attempt on **2026-10-28** timed out. Its cause has not been
established; a timeout alone does not identify a Wi-Fi, authentication, power or
host failure. The configuration below was prepared without reaching the target.
Do not assume that installing an RDP client on Mac will restore host connectivity.

A later **2026-10-28** inspection succeeded after the operator restored Tailscale
and completed its SSH identity check. Direct LAN OpenSSH was also verified with
the host key obtained through the trusted session. This independent path stayed
connected while only Tailscale was upgraded to **1.104.4**; both client and running
daemon report that version. A new Tailscale SSH connection and a temporary
loopback TCP forward to host OpenSSH passed; the test tunnel was then stopped.
These checks establish terminal/forwarding access, not a working RDP desktop.

The inventory also found existing **NoMachine 8.20.1-5**, enabled and listening
on TCP 4000 on IPv4/IPv6 interfaces. It was already present and was not installed,
reconfigured or disabled here. It is a separate remote-desktop protocol, not
xrdp or proof of Windows App compatibility. Its Mac client/session was not tested.
The research console GUI was normally logged out after the operator's response;
GNOME reported no logout inhibitors. The subsequent RDP authentication and
desktop display passed. The GDM autologin target was not changed.

The local package metadata offers xrdp `0.9.12-1ubuntu0.1`, xorgxrdp
`1:0.2.12-1` and new dependency ssl-cert `1.0.39`; simulation would install three
packages with no upgrades/removals. However, the xrdp candidate lacks the ESM
revision identified by [Ubuntu USN-8476-1](https://ubuntu.com/security/notices/USN-8476-1).
Do not install that old candidate as the prepared solution. No Ubuntu Pro
entitlement or ESM repository has been enabled. A separately pinned source-build
candidate can be evaluated without replacing the host graphics stack; its build
and installation evidence must be recorded separately.

The [source-build guide](rdp-build.md) explains the isolated bundle and required
host configuration; do not install or start the default configuration blindly.

## Client, server, protocol and session

| Term | Meaning in this setup |
| --- | --- |
| Client | Windows App on Mac displays the remote desktop and sends input |
| Server | xrdp on Jetson authenticates the connection and carries the desktop traffic |
| RDP | Remote Desktop Protocol, the rules both sides use for graphics and input |
| xorgxrdp | Modules connecting an Xorg display server to xrdp |
| Graphical session | Running desktop, windows and user services on Jetson |
| SSH tunnel | An authenticated connection carrying a local TCP port to Jetson |
| Loopback | A computer's own local address, such as `127.0.0.1` |

Microsoft Remote Desktop for Mac has been replaced by **Windows App**. Adding a
direct remote PC does not require signing into Windows App with a Microsoft
account. The remote Linux login is a separate account, not an eduroam identity.
See Microsoft's [replacement notice](https://learn.microsoft.com/en-us/previous-versions/remote-desktop-client/remote-desktop-macos),
[connection steps](https://learn.microsoft.com/en-us/windows-app/get-started-connect-devices-desktops-apps)
and [account guidance](https://learn.microsoft.com/en-us/windows-app/user-account-settings-add-remove-manage).

The [xrdp project](https://github.com/neutrinolabs/xrdp) provides a Linux RDP
server and supports ARM. With the Xorg backend, xrdp-sesman starts an Xorg
server using [xorgxrdp](https://github.com/neutrinolabs/xorgxrdp) modules, then
starts the user's desktop. A remote virtual session can provide a desktop
without first logging into the physical display. This is the architecture's
purpose, not proof that this Jetson already supports headless login.

Typically this creates a separate desktop rather than mirroring the HDMI
desktop. A browser or settings window already open on the console need not
appear in the RDP session. Both sessions still use the same host and, for the
same account, the same home files; a new display is not a separate sandbox.
RDP sends screen updates and keyboard/mouse events. Applications and any
computation they start execute on Jetson, not on Mac.

## Session and graphics constraints

The [xrdp FAQ](https://github.com/neutrinolabs/xrdp/wiki/Tips-and-FAQ) describes
conflicts when the same user logs into the console and xrdp concurrently on
systemd systems. Plan to log the research account out of its physical GUI
session before its RDP login. An SSH session is not a second graphical desktop.
Do not automatically change the other account's existing autologin or create
another account merely to hide an unexplained session conflict.

Keep the existing Jetson graphics stack. Xorg startup, software desktop
rendering, GPU compute and GPU-accelerated desktop rendering are different
questions. An ordinary settings desktop may use software rendering; this does
not establish whether CUDA computation works or fails. Check both separately.
Do not install desktop-PC NVIDIA drivers, replace GDM, upgrade JetPack or copy a
recent Ubuntu GNOME Remote Desktop recipe to solve an unexamined xrdp issue.

The available [NVIDIA VNC guide](https://developer.nvidia.com/embedded/learn/tutorials/vnc-setup)
does not validate this xrdp configuration. NVIDIA's
[AGX Orin / Ubuntu 20.04 support discussion](https://forums.developer.nvidia.com/t/the-orin-module-ubuntu20-04-system-is-controlled-remotely-from-a-pc/269195)
also does not establish a universal RDP stability advantage. Test the selected
versions on the actual Jetson before relying on them for recovery.

## Read-only preflight before an installation plan

Once SSH or console access works, run these commands on Jetson. They inspect
candidate packages, simulate dependency changes and list current services; they
do not install software, change Wi-Fi or restart the display manager.

```sh
apt-cache policy xrdp xorgxrdp xserver-xorg-core
apt-get -s install xrdp xorgxrdp
systemctl is-active gdm3 xrdp xrdp-sesman
loginctl list-sessions
ss -ltn
```

`apt-cache policy` shows installed and candidate versions from the host's local
package metadata. `apt-get -s` simulates installation: inspect every proposed
install, upgrade and removal. The metadata can be stale; this is not a package
security audit or confirmation that every download is available. `systemctl`
may report `inactive`, `failed` or unknown services when packages are absent;
interpret the output rather than treating absence as a passed RDP check.
Session and listener output can contain private identifiers; keep it outside Git.

The resulting installation plan must name the actual ARM64 package versions,
dependencies, startup behavior, backup locations and rollback. Check the
installed version's `man xrdp.ini` and `man sesman.ini`; current upstream
documentation can describe options absent from Ubuntu 20.04 packages. Ubuntu's
[Focal xrdp.ini manual](https://manpages.ubuntu.com/manpages/focal/man5/xrdp.ini.5.html)
is a reference, not evidence of the target's current package candidate.

Install a management server on the **host**, outside the inference container.
Wi-Fi settings belong to host NetworkManager. Giving a model container the
desktop, session bus and network-administration permissions is unnecessary for
this purpose. Package installation may start services automatically: arrange
restricted initial startup before installing, then verify actual listeners.
Do not expose a default all-interface listener while assuming it is loopback.
No installation command is prescribed here until this plan is resolved.

## Proposed protected RDP connection

Use a loopback-only xrdp listener on Jetson and reach it through authenticated
SSH. This avoids exposing TCP 3389 to the campus network or the robot network.
Verify the selected version's binding syntax, server authentication, TLS
certificate access and actual socket addresses. Do not disable authentication,
TLS checks or the firewall to make an initial connection work. Only enable
clipboard, folder and device redirection when needed for the task.

Before a Tailscale SSH forwarding test, review
[Tailscale's security bulletins](https://tailscale.com/security-bulletins).
The inspected client/daemon was 1.104.2; the 2026-10-26 SSH bulletins
TS-2026-014/015 are fixed in 1.104.4 or newer. Verify the current running version
and policy, arrange console or alternate recovery, then update to an appropriate
supported release before forwarding. Do not restart the sole remote path or
weaken a reauthentication policy to regain access. The controlled update and
forwarding verification recorded above completed on 2026-10-28.

After xrdp is configured and verified to listen only on Jetson loopback port
3389, run this **example on Mac**, with real values supplied locally:

```sh
ssh -N -L 127.0.0.1:13389:127.0.0.1:3389 RESEARCH_USER@JETSON_MANAGEMENT_ADDRESS
```

`-N` opens no remote shell. `-L` opens Mac's loopback port 13389 and forwards
traffic through SSH to Jetson's loopback port 3389. These identical-looking
loopback addresses refer to different computers. Port 13389 is an example local
port chosen to avoid a collision with a local RDP server. Keep the tunnel alive
while using RDP; closing it removes this transport path.

In Windows App, choose **Add PC**, set **PC name** to `127.0.0.1:13389`, and
use the research Linux account when asked for the remote login. No RDP gateway
is required for this SSH-tunnel example. Confirm the expected server certificate
through the independently trusted host; do not blindly accept a changed identity.
Do not put passwords in command arguments, the repository or shared screenshots.
The tunnel, Linux authentication and visible GNOME desktop passed on this
Jetson. A Mac profile named `B2 Jetson (SSH tunnel)` was created with credentials
set to Ask when required; no password was saved. Client folder, clipboard,
printer, smartcard, microphone, camera and audio redirection are disabled.
An inherited Chrome crash notification was visible; no crash report was sent.
The operator confirmed basic desktop interaction. Settings permission, extended
input checks and reconnect acceptance still need their own evidence.

## Using the installed server

The service is enabled at boot. On Jetson, its current state can be checked and
it can be started manually if needed:

```sh
sudo systemctl start b2-rdp.service
systemctl is-active b2-rdp.service b2-rdp-sesman.service
```

After the operator confirmed basic interaction, `b2-rdp.service` was enabled
with `systemctl enable`; its required `b2-rdp-sesman.service` starts through that
dependency, without a separate boot enablement. The enablement and active state
were verified without restarting either service or the host. This configures
startup but does not prove cold-boot access. It requires neither GUI autologin
nor robot motion. Start the SSH tunnel from Mac,
then open the saved `B2 Jetson (SSH tunnel)` profile. A self-signed certificate
requires checking the expected server identity; do not ignore changed
certificates or save a permanent bypass. The independently verified TLS probe
used the actual public certificate as a trust anchor.

## eduroam settings through RDP

Opening a remote settings window does not grant permission to change a system
connection. Desktop authorization uses **polkit**, which can treat a remote
session differently from a physical console. Existing connection permissions,
secret storage and the available password agent also matter. A successful RDP
desktop is therefore not proof that the existing eduroam profile can be edited.

Test the specific NetworkManager settings operation. If the graphical path is
blocked or ambiguous, use the reviewed terminal helper with explicit sudo
authorization after checking university CA/server settings and the active
profile. Its default mode is read-only:

```sh
/usr/bin/python3 tools/configure_unattended_wifi.py
```

Run from the project root on Jetson, using the host's system Python and existing
system D-Bus binding. The credential-saving operation is deliberately separate;
see [boot networking and credential handling](system-overview.md). Never grant
all remote polkit actions just to make a settings dialog work.

System-stored Wi-Fi credentials let NetworkManager connect before GUI login;
they do not require automatic desktop login or RDP. Credential entry belongs to
the account owner in an interactive terminal or trusted settings dialog, without
recording the secret. The owner has deferred the credential change until a
recovery-capable session; RDP has not removed that prerequisite. Writing a
profile and testing reconnection are separate steps. Reconnecting the Wi-Fi
used by RDP/SSH can terminate both connections, so plan recovery first.

## Vino fallback for sharing the console

Vino remains an alternative when the requirement is to view the existing GNOME
desktop. Its installed version shares a **logged-in** desktop; NVIDIA's VNC
guide documents that requirement. It does not turn an unlogged-in boot into a
working remote session. Whether the framebuffer works with HDMI unplugged also
requires a test. Do not assume the Vino and xrdp sessions have identical behavior.

If a reviewed Vino setup later listens only on Jetson loopback port 5900, the
alternative Mac commands are:

```sh
ssh -N -L 127.0.0.1:5901:127.0.0.1:5900 RESEARCH_USER@JETSON_MANAGEMENT_ADDRESS
```

Open the viewer in a second Mac terminal after the tunnel is established:

```sh
open vnc://127.0.0.1:5901
```

These are unrun alternatives, not a request to enable both servers. Review
authentication and client compatibility rather than copying a legacy guide's
password-in-command or encryption-disabled configuration.

## Acceptance and recovery tests

| Check | Evidence required |
| --- | --- |
| Transport and login | Restricted listener, expected server identity, authenticated tunnel and successful Linux login from Windows App |
| Settings use | Terminal and NetworkManager settings open; the specific required system operation is authorized without blanket polkit changes |
| Input and usability | Keyboard layout, Japanese input when needed, mouse, resolution and reconnect behave correctly |
| Session ownership | The intended remote session is identified; no conflicting console login for the same account; other accounts' sessions are preserved |
| Lock, logout and reconnect | Locking or disconnecting is distinguished from logging out; subsequent login works with the selected policy |
| Headless boot | With recovery available, HDMI-disconnected cold boot reaches Wi-Fi/SSH and permits remote login without a console GUI login |
| Existing software | Local display, normal SSH and the established model-free CUDA checks still work after setup |
| No Internet | On a separately verified Jetson hotspot, ordinary local OpenSSH plus the same tunnel works without Tailscale coordination or campus Wi-Fi |
| Recovery | A failed Wi-Fi reconnect or remote server has a tested console/alternate-access procedure |

The hotspot and its ordinary local OpenSSH access are not yet configured or
validated. Tailscale SSH on a Tailscale address and OpenSSH on a local LAN
address are separate access paths; verify credentials and host keys for the
latter before taking the system offline. No external AP is assumed.

A working RDP session can remove routine HDMI use after these tests. It cannot
repair a fully unreachable Wi-Fi link through that same failed link. Keep
physical recovery for initial boot and network tests. A robot experiment must
have its own local process lifetime, stop policy and physical operator override;
closing Windows App must not implicitly define what the robot does.
