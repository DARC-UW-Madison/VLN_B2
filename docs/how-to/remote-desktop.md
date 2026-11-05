# Remote desktop from Mac

[日本語](remote-desktop.ja.md) · [Documentation](../README.md) · [System overview](../reference/system-overview.md) · [Field procedure](field-network.md)

> Document type: **Procedure**.

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

See the separate [record](../records/desktop-history.md) for the result and history.

## VS Code installed on Jetson

See the separate [record](../records/desktop-history.md) for the result and history.

## Applied direct-listener configuration

See the separate [record](../records/desktop-history.md) for the result and history.

## What is currently known

See the separate [record](../records/desktop-history.md) for the result and history.

## Client, server, protocol and session

See the [remote-access explanation](../explanations/remote-access.md).

## NoMachine, RDP and VNC

See the [remote-access explanation](../explanations/remote-access.md).

## Retired loopback RDP setup

See the separate [record](../records/desktop-history.md) for the result and history.

## Session and graphics constraints

See the [remote-access explanation](../explanations/remote-access.md).

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

See the separate [record](../records/desktop-history.md) for the result and history.

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
see [boot networking and credential handling](../reference/system-overview.md). Never grant
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

See the separate [record](../records/desktop-history.md) for the result and history.

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
