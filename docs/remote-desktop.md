# Remote desktop from Mac

[日本語](remote-desktop.ja.md) · [Documentation](README.md) · [System overview](system-overview.md) · [Field procedure](field-network.md)

Current policy, **2026-11-03**: connect Windows App directly to the Jetson's
Tailscale IPv4 address on TCP 3389. The former Mac tunnel/profile was removed;
no Mac tunnel, startup task, routing change or new client is required. The
operator creates the Windows App entry. Existing Tailscale remains the private
management network. Model inference and future robot control run on Jetson
independently of a remote desktop.

## Connect directly from Windows App

1. Keep the existing Tailscale connection active on Mac and Jetson.
2. In Windows App, choose **Add PC** and enter the values below.
3. Save/open the PC and enter the Jetson Linux account password when prompted.
   If xrdp presents a session chooser, select **Xorg**. Do not use a university
   password or a Microsoft login as the Linux account credential.
4. On a certificate prompt, compare the server certificate with the trusted
   Jetson copy; do not disable certificate verification globally. The first new
   address can prompt even though the existing certificate was retained.

| Setting | Value |
|---|---|
| PC name | `JETSON_TAILSCALE_IP:3389`; use the actual IP privately supplied to the operator |
| User account | Research Linux login, or Ask when required |
| Password | That Linux account's password; keep it out of chat/Git |
| Gateway | No gateway |
| Friendly name | Optional descriptive name such as `B2 Jetson` |

Do not use the old `127.0.0.1:13389` entry or start a tunnel. The account is the
same research account used over SSH. For the client UI, see
[Microsoft's Windows App instructions](https://learn.microsoft.com/en-us/windows-app/get-started-connect-devices-desktops-apps).
The address is the node's Tailscale address, not a changing campus Wi-Fi lease;
see [Tailscale address assignment](https://tailscale.com/docs/concepts/ip-and-dns-addresses).
No university-portal login is performed by RDP itself.

## Text copy and paste between Mac and Jetson

On 2026-11-03 the reported clipboard failure was traced to our earlier server
configuration: `allow_channels=false` plus both clipboard restrictions set to
`all`. This was an explicit setup restriction, not evidence of a client bug.
The server now allows text in both directions. In `xrdp.ini`,
`allow_channels=true` and only the `cliprdr` channel is enabled; other channels
remain disabled. In `sesman.ini`, `RestrictInboundClipboard=file,image` and
`RestrictOutboundClipboard=file,image` block files/images while allowing text.
The exact version's [clipboard settings](https://raw.githubusercontent.com/neutrinolabs/xrdp/v0.10.6.1/sesman/sesman.ini.in)
were checked before applying this change.

To activate and check it yourself:

1. Save work in the Jetson desktop, then **log out of that GUI session**. Merely
   disconnecting can retain its channel server and old restrictions. SSH can stay open.
2. In Windows App, edit this PC, open **Devices & Audio**, enable Clipboard or
   select **Bidirectional**, then Save. These are operator instructions; no Mac
   preference/profile was changed by the agent. See [Microsoft's redirection guide](https://learn.microsoft.com/en-us/windows-app/device-audio-folder-redirection-teams).
3. Connect and sign into a new Jetson RDP session. Copy a harmless test string
   from Mac and paste it into a Jetson text editor, then test the reverse direction.
4. Use Linux shortcuts inside Jetson: normal editors use Ctrl+C / Ctrl+V; a
   terminal normally uses **Ctrl+Shift+C / Ctrl+Shift+V**. Mac uses Command+C / Command+V.

The session manager was reloaded without restarting the listener or terminating
GUI sessions. Settings and service activity were verified, but end-to-end text
transfer awaits the operator's new-session/client test. Current clipboard contents
were not inspected. Original ini files are preserved privately under
`local/editor-setup-01/rdp-config-before`; restoring them requires administrator
access and a new session. TLS, Tailscale-only binding, firewall and login rules
were not changed.

## VS Code installed on Jetson

Microsoft's official **ARM64 Debian package, VS Code 1.144.1** was installed on
2026-11-03. The download matched the official update metadata's SHA256. APT
simulation and before/after inventories showed exactly one new package, `code`,
with no other package upgrades/removals. `code --version` reports the expected
version/commit/ARM64 and `dpkg --audit` is clean. The application was also
started in the existing RDP GUI and its window showed the Japanese camera-demo
manual; this did not require a GUI logout. CUDA, JetPack, Python and the
model containers were not modified. This is a host editor for the GUI, not a
replacement model environment; use the demo commands from its terminal as before.

From a terminal **inside the Jetson desktop**, open the project:

```bash
cd ~/Developer/Projects/Robotics/b2/VLN_B2
code .
```

If the virtual RDP desktop encounters an Electron/GPU rendering problem, start
this one instance with GPU rendering disabled:

```bash
code --disable-gpu .
```

Do not add `--no-sandbox` as a routine workaround. The packaged sandbox remains
enabled. The installer was explicitly told not to add Microsoft's APT source;
no Microsoft repository/key source was added. Later editor updates can use a
reviewed official package via APT. No extension, account sign-in or Settings Sync
was configured. This editor does not require installing VS Code on Mac.
[Microsoft's Linux installation instructions](https://code.visualstudio.com/docs/setup/linux)
and [the binary license](https://code.visualstudio.com/license) apply; the
project's MIT license does not relicense this installed application. Package,
installation and window-check evidence remain in ignored `local/editor-setup-01`.

## Applied direct-listener configuration

The existing host xrdp now binds **only the configured Tailscale IPv4**, not
loopback or a wildcard. TLS settings, certificate/key, PAM, allow group and
Linux credentials were retained. A single labelled IPv4 INPUT rule drops
traffic to that exact address/TCP 3389 arriving outside `tailscale0`. It neither
flushes rules nor changes the default firewall policy, SSH, NoMachine or Wi-Fi.
Existing Tailscale access rules still apply.

The reviewed [readiness helper](../deploy/rdp-tailnet-ready.py) and
[systemd drop-in](../deploy/rdp-tailnet.conf) run on **Jetson only**. The private
`/opt/b2-remote/etc/xrdp/tailnet-address` holds its actual enrolled IPv4. The
helper checks the configured address against `tailscale ip -4`, confirms it is
up on `tailscale0`, then idempotently checks/adds the narrowly scoped rule before
xrdp starts. A mismatch or unavailable interface fails startup; it never falls
back to all interfaces. The service starts after tailscaled and retries failure
every five seconds without a start-rate cutoff. It remains enabled at boot.
Changing enrollment/address requires reviewing that private file, xrdp's bind
address and any old dedicated rule together.

The configuration was backed up under private `local/direct-rdp/attempt-01`.
The listener and session manager were active after two service restarts, and
only one dedicated firewall rule existed. A controlled address-readiness failure
rejected startup; restoring the configuration recovered automatically on retry
without restarting Wi-Fi/SSH or changing Tailscale enrollment. From Mac, a direct TCP/RDP negotiation
selected TLS 1.3 and the server certificate SHA256 matched the copy inspected
through SSH. No password was sent for that transport check. **The operator confirmed the direct-route desktop on 2026-11-03. A new
whole-device reboot test remains a separate acceptance item.** The
same backend previously passed visible desktop/input tests over the old route.
The 164 ordinary tests passed on Mac and Jetson; mocked guard tests do not
replace the actual transport check.

On 2026-11-03 the helper was corrected to handle expected startup failures
without an unhandled exception/desktop crash report. The previous deliberate
test report was archived; normal systemd retry behavior remains. See
[incident evidence and limits](system-overview.md#diagnosing-access-loss-and-desktop-failures).

For diagnosis on Jetson, inspect `systemctl status b2-rdp.service`, its journal,
`tailscale ip -4`, the configured bind and `ss -ltnp`. Do not open 3389 on campus
or robot interfaces to bypass an address/access failure. To roll back, stop the
RDP service, restore the saved original ini, remove only this drop-in and exact
labelled firewall rule, reload systemd and start the original loopback server.
That restores the old server restriction; it does not create a Mac tunnel.
Do not remove unrelated firewall rules or Tailscale enrollment.

The following sections retain earlier inspections and the superseded SSH
transport for explanation. They are historical records, not current connection
instructions. Use the direct steps above for this target.

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
without first logging into the physical display. The operator confirmed that HDMI was
disconnected during the successful desktop test. A physical power-cycle
acceptance test is still pending.

Typically this creates a separate desktop rather than mirroring the HDMI
desktop. A browser or settings window already open on the console need not
appear in the RDP session. Both sessions still use the same host and, for the
same account, the same home files; a new display is not a separate sandbox.
RDP sends screen updates and keyboard/mouse events. Applications and any
computation they start execute on Jetson, not on Mac. Resolution and desktop
session settings can make the dock, scaling or theme differ from HDMI. Such a
difference alone is not a connection failure. Confirm the login and session
before assuming that an appearance difference means files or settings were lost.

## NoMachine, RDP and VNC

| Name | What it is | Relation to this setup |
|---|---|---|
| NoMachine | Remote-access product using its NX protocol; available session types depend on edition and configuration | Pre-existing host installation, retained unchanged; its Mac client has not been validated here |
| RDP | A remote-desktop protocol, implemented here by Windows App and xrdp/xorgxrdp | The selected, tested management path; this backend starts a separate virtual Xorg desktop |
| VNC | Remote-desktop technology using RFB; implementations may share a display or create a virtual desktop | Existing Vino is stopped and was not selected |

See the vendor's [NoMachine FAQ](https://www.nomachine.com/support/faq) and
[RealVNC protocol explanation](https://help.realvnc.com/hc/en-us/articles/360002320638-How-does-VNC-technology-work).
Protocol name alone does not establish session sharing, encryption, performance
or stability. A separately created RDP display can have different dock, theme,
resolution or session settings while using the same user's home files. It is
not a separate Linux account or sandbox.

The former RDP server accepted TCP only on **Jetson's** loopback address.
Windows App connects to **Mac's** loopback port, where SSH forwards the stream:

```text
Windows App -> Mac 127.0.0.1:13389 -> SSH over Tailscale
            -> Jetson 127.0.0.1:3389 -> xrdp -> virtual desktop
```

Tailscale provides private network reachability; SSH authenticates and carries
the TCP forward; RDP handles desktop authentication, graphics and input. The
RDP server's TLS remains enabled. Direct Mac-to-server RDP is possible with a
different listener/access policy. The earlier configuration kept 3389 off
campus/robot interfaces by using the reviewed SSH path; the direct configuration
above now uses an explicit tailnet bind and ingress restriction.
The forwarding master is separate from an interactive SSH terminal. Opening a
terminal session does not create the screen tunnel, and closing the dedicated
tunnel does not stop xrdp or a robot application. This tunnel carries the screen
connection only, not general robot DDS traffic or the model's control loop.

## Why the earlier setup used a tunnel

The operator wants to avoid Mac system/network changes. Do not change macOS
routes, enable its SSH server, or install a persistent forwarding service for
this project. The existing tunnel is an SSH client process that forwards one
local port; it is not a requirement to reconfigure the Mac network.

For NoMachine's direct NX mode, the intended path is:

```text
Mac NoMachine client -> Tailscale private network -> Jetson NoMachine server :4000
```

The Mac needs the client application and a saved connection containing the
Jetson's reachable Tailscale IP, NX protocol, port 4000 and Jetson Linux account.
No separate SSH tunnel is part of that path. Port 4000 is the default, not a
claim that reachability/access has passed on this host. Inspect Jetson listener,
tailnet access and headless desktop behavior before relying on it; no Mac
system change is implied. Existing Tailscale supplies the private network.
See the vendor's [direct connection guide](https://www.nomachine.com/support/documents/getting-started-with-nomachine).
Direct-IP mode is distinct from the vendor's separate NoMachine Network service.

RDP itself does not require SSH. A Windows RDP host commonly accepts connections
on a network interface, with access controlled by its firewall and policy. A
client can then use the reachable IP and account directly. The same architecture
is possible with xrdp. [Tailscale's direct RDP guide](https://tailscale.com/docs/solutions/access-remote-desktops-using-windows-rdp)
illustrates reaching an RDP host using its tailnet address; the guide targets
Windows and does not validate Linux host configuration.

Here the installed xrdp listener was deliberately restricted to loopback, so an
SSH forward is required by that chosen configuration, not by Linux or RDP.
This adds a connection to maintain. A tailnet-only RDP listener with matching
startup order, TLS, authentication and access rules could remove that forward;
changing the host listener/policy is separate from merely changing Windows App's
address. That direct-listener change was subsequently applied on 2026-11-01 as described above. Tailscale already
provides an encrypted private network; SSH forwarding is not a universal extra
requirement for using RDP through it.

Testing the pre-existing NoMachine first could have reduced setup work. We have
not compared NoMachine and xrdp on this host, so the source-build effort does not
prove RDP was necessary or faster. The current xrdp bundle has CPU painting and
RemoteFX enabled, with H.264 encoding disabled; desktop interaction passed, but
video throughput, latency and CPU cost were not benchmarked. NoMachine supports
[compressed/video display encodings](https://kb.nomachine.com/DT07X00332), whose
actual availability depends on version, session and hardware. Sending screen
updates is not evidence that every such protocol is equally expensive. VNC is
excluded from this project's current options per the operator's preference.
The installed NoMachine and working RDP configuration are retained unchanged.

## Session and graphics constraints

On 2026-11-03, simultaneous physical and RDP research-account GUI sessions
were observed. At the operator's request the physical session alone was logged
out, preserving RDP/SSH. GNOME and the window manager then started on the RDP
display; reopen the client connection to inspect it. This is a one-time logout,
not a change to automatic GUI login, and not proof of the earlier freeze cause.

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

## Historical SSH-tunnel configuration

The following records the superseded setup; do not execute it for the current
direct connection. It used a loopback-only Jetson listener and authenticated SSH. This avoids exposing TCP 3389 to the campus network or the robot network.
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

After xrdp is verified to listen only on Jetson loopback port 3389, a foreground
tunnel can be opened with this **example on Mac**, using real values locally:

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
input checks still need their own evidence. A later reconnection following the
headless software reboot was confirmed by the operator.


### Keep the tunnel independent of the terminal

A normal SSH shell and this forwarding connection are separate connections.
SSH can work while Windows App fails because Mac's local port 13389 has no
listener. This was the diagnosed failure after the initial desktop test; the
Jetson RDP services were still active. Installing a server does not create a
permanent Mac-to-Jetson connection.

The helper below remains as a record of the former transport. Do not start it
for current direct RDP or recreate a Mac background connection:

```sh
python3 tools/desktop_tunnel.py start RESEARCH_USER@JETSON_MANAGEMENT_ADDRESS
python3 tools/desktop_tunnel.py status RESEARCH_USER@JETSON_MANAGEMENT_ADDRESS
python3 tools/desktop_tunnel.py stop RESEARCH_USER@JETSON_MANAGEMENT_ADDRESS
```

Run `start` before opening the saved Windows App profile; `status` and `stop`
are separate inspection and cleanup operations, not steps to run immediately
after starting. Use the same target spelling and port options for all operations.
The helper uses an owned private control socket and a dedicated OpenSSH master
started with `-fNT`. It binds only Mac loopback, retains normal SSH host-key and
identity checks, and stores no password. An occupied port or unrelated connection
is not stopped. `status` does not initiate authentication when no master exists.
It checks the SSH master, not RDP login, desktop health or remote reachability
beyond what that connection currently detects.

Closing the invoking terminal or this chat leaves this background master alive.
This is not an automatic reconnect service or a Mac startup agent: after either
computer reboots or a sustained network outage, run `start` again. The helper
keeps a live matching master and starts a new one if the old connection has ended.
If a connected but stalled master remains, use `stop`, then `start`. Opening an
ordinary SSH shell alone does not recreate the RDP forward.

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
were verified initially without restarting. A subsequent HDMI-disconnected
software reboot restored Wi-Fi, Tailscale and SSH without operator intervention;
SSH returned at about 25 seconds of target uptime. NetworkManager, tailscaled,
SSH, both RDP services and Docker were active, the SSD was mounted, Docker used
its SSD data root, and RDP still listened only on loopback. The connected Wi-Fi
was a system-wide non-enterprise profile, not eduroam. This proves recovery for
that connection after a software reboot; it does not establish eduroam login-free
access or a physical power-cycle result. Post-reboot GUI display and input were
subsequently confirmed by the operator. Neither GUI
autologin nor robot motion is required. Start the SSH tunnel from Mac,
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
recording the secret. The owner completed saving through the terminal after
GUI authorization was denied; no broader polkit permission was added. Writing a
profile and testing reconnection are separate steps. Reconnecting the Wi-Fi
used by RDP/SSH can terminate both connections, so plan recovery first.

### Save an inactive eduroam profile through the GUI

The current Wi-Fi can differ from the stored eduroam profile. The terminal
helper selects the active profile by default; `--connection-id` selects one
saved profile explicitly. Switching networks is not a prerequisite for editing it. In a terminal inside the Jetson desktop, run:

```sh
nm-connection-editor
```

Select the existing eduroam connection and edit it. In **General**, enable
automatic connection and **All users may connect to this network**. In
**Wi-Fi Security**, enter the owner's password and choose **Store the password
for all users** from the password storage menu. Preserve the institution-provided
identity, authentication method, CA and server checks. Save; if authorization is
requested, authenticate with the permitted Linux administrator account. That
local administrator password and the university Wi-Fi password have different
purposes. Do not activate a new connection yet, reveal the password in a report,
or remove certificate checks to make saving succeed. If the remote session lacks
permission, stop and use an explicitly authorized terminal operation rather than
broadening polkit rules.

After saving, inspect only whether the profile is system-wide, autoconnect is
enabled, secret flags are zero and a non-empty password exists; never print its
value. Prepare a timed NetworkManager rollback to the known working connection
before switching Wi-Fi, because both RDP and SSH use that link. Confirm a fresh
SSH connection and Internet/Tailscale access on eduroam before canceling the
rollback. Then restore the Mac tunnel and test RDP again. A reboot must be
tested on eduroam separately from the already verified non-enterprise Wi-Fi.
Saving a profile alone does not establish either result.

### Terminal fallback when polkit denies GUI editing

The operator could display and interact with the RDP desktop, but the editor
reported no polkit authorization when saving. This establishes a permission
boundary; it does not diagnose a bad Wi-Fi password. No blanket polkit exception
was added. In the owner's own SSH terminal on Jetson, use the reviewed helper
with explicit sudo authorization and the saved profile's name:

```sh
cd ~/Developer/Projects/Robotics/b2/VLN_B2
sudo /usr/bin/python3 tools/configure_unattended_wifi.py --connection-id SAVED_PROFILE_NAME --apply
```

Replace the placeholder locally. The helper rejects missing/duplicate names and
unsupported authentication methods before asking for the university password.
Enter that password twice at the hidden prompts; it is not a command argument
or chat message. The helper preserves CA, alternative-subject/domain checks,
identity, EAP, IP settings and other profile options, enables system-wide
connection and writes secret flags 0. It backs up each profile separately under
root-protected `/etc/NetworkManager/vln-b2-backups`, retaining the first copy.
The old active-profile backup, if present, remains intact. It verifies secret
retention without displaying the value and does not activate Wi-Fi, restart any
service or change GUI autologin unless the separate option is explicitly used.
The saving test and the controlled network-switch test remain different steps.

### Completed eduroam acceptance

On 2026-10-28, the owner's interactive SSH save succeeded. A privileged check
confirmed system-wide autoconnect, password flags 0, a non-empty stored secret,
and retained CA/server checks, without exposing the value. A 180-second
NetworkManager checkpoint protected activation; a fresh Tailscale SSH connection,
full connectivity and active management services passed before it was canceled.
The next software reboot was again HDMI-disconnected and returned to eduroam
automatically. Fresh SSH worked at about 24 seconds of target uptime. Boot-ID
comparison, enabled/active services, SSD mount, SSD Docker data root and
loopback-only RDP passed. The Mac tunnel was restarted and the operator confirmed
Windows App display and interaction again. GUI autologin was not changed;
physical power-cycle recovery and extended desktop checks remain untested.
Private records and backups remain on the host, outside Git.

## Historical Vino inspection

Vino was already installed and stopped. Earlier planning considered sharing an
existing console desktop with it. VNC is excluded from the current plan per the
operator's preference; no Vino configuration or forwarding command is prescribed.
The successful headless tests concern xrdp, not Vino. Retain the inventory as
historical evidence rather than presenting VNC as an active alternative.

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
