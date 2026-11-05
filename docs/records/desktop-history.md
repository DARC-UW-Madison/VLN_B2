# Remote-desktop configuration and checks

[日本語](desktop-history.ja.md) · [Records](README.md)

> Document type: **Record**. Evidence of performed configuration and checks, separate from current operating procedures.

## Text copy and paste between Mac and Jetson

On 2026-11-03 an earlier server restriction was found:
`allow_channels=false` plus both clipboard restrictions set to `all` blocked
text redirection. Removing it did not establish end-to-end success.
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
transfer still fails according to the operator despite Bidirectional being
selected and the client being restarted. A complete GUI logout/new-session test
has not been confirmed. Diagnosis is deferred during B2 network work; the operator
can open the Markdown guides in Jetson VS Code instead. Current clipboard contents
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

The reviewed [readiness helper](../../deploy/rdp-tailnet-ready.py) and
[systemd drop-in](../../deploy/rdp-tailnet.conf) run on **Jetson only**. The private
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
[incident evidence and limits](../reference/system-overview.md#diagnosing-access-loss-and-desktop-failures).

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


## Historical Vino inspection

Vino was already installed and stopped. Earlier planning considered sharing an
existing console desktop with it. VNC is excluded from the current plan per the
operator's preference; no Vino configuration or forwarding command is prescribed.
The successful headless tests concern xrdp, not Vino. Retain the inventory as
historical evidence rather than presenting VNC as an active alternative.
