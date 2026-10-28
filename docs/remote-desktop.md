# Remote desktop from Mac

[日本語](remote-desktop.ja.md) · [System overview](system-overview.md) · [Field procedure](field-network.md)

Mac can operate a Jetson desktop over the network. On 2026-10-27, read-only
inspection found Vino 3.22 installed, no running `vino-server`, and no TCP
listener on 5900 or 3389. XRDP/xorgxrdp and gnome-remote-desktop were absent.
No remote-desktop service or authentication setting was enabled.

Before enabling forwarding, review [Tailscale's security bulletins](https://tailscale.com/security-bulletins).
The inspected installed version is 1.104.2. The 2026-10-26 SSH bulletins
TS-2026-014/015 require 1.104.4 or newer for their fixes. Confirm the running
version and policy, establish console/alternate access, then update appropriately
before testing a Tailscale SSH tunnel. Do not restart the sole remote path
without recovery access. No update or SSH-policy change was applied here.

## What is transmitted

VNC sends screen updates and keyboard/mouse events; computation stays on Jetson.
SSH sends terminal interaction. Both need a working network path. Remote desktop
can remove routine HDMI use after validation, but cannot repair an unreachable
Wi-Fi link over that same link.

The installed Vino shares a logged-in GNOME desktop, rather than the login screen.
NVIDIA's [VNC guide](https://developer.nvidia.com/embedded/learn/tutorials/vnc-setup)
states this login requirement. Wi-Fi/SSH working before GUI login does not make
this user-session VNC server available before login. A separate login/session
solution needs selection and Jetson-specific testing if that is required;
it has not been installed. Do not assume a recent Ubuntu RDP settings screen
exists on this Ubuntu 20.04 installation.

## Proposed connection, not enabled configuration

Prefer a localhost-restricted VNC server reached through an authenticated SSH
tunnel. Verify server binding/authentication and Mac-client compatibility before
activation. Use this example only after the server is configured and verified
to listen on Jetson loopback port 5900:

```sh
ssh -N -L 127.0.0.1:5901:127.0.0.1:5900 RESEARCH_USER@JETSON_MANAGEMENT_ADDRESS
```

In a second Mac terminal, after establishing the tunnel:

```sh
open vnc://127.0.0.1:5901
```

The first address is Mac's listener; SSH reaches the second loopback address on
Jetson. `-N` opens no remote shell; `-L` forwards that local TCP port. Keep the
tunnel alive while using Screen Sharing. This does not publish VNC on campus.
Do not put a VNC password in a command, disable authentication or copy legacy
encryption settings without reviewing the protected transport. The server is
not currently listening and these example commands have not been run.

## Acceptance at the visit

1. Confirm which desktop/session is shared and how that user logs in.
2. Set authentication locally and verify restricted listener/transport access.
3. Test Mac display, keyboard/mouse, resolution, lock/logout behavior and GPU
   compatibility. Do not expose personal credential dialogs in shared recordings.
4. Test reboot and HDMI-disconnected operation. GUI enabled does not prove a
   usable headless framebuffer; a supported display/virtual-session setup may
   be needed. Do not change graphics configuration blindly during remote access.
5. Retain console recovery for the first boot/network tests. Later test the same
   desktop connection on the approved mobile LAN without campus Wi-Fi.

Remote desktop remains a management tool. The robot's future local inference and
control loop must have its own lifecycle and stop policy, independent of a Mac
desktop window or SSH terminal.
