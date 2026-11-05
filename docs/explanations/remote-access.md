# Remote access: screen, login and transport

[日本語](remote-access.ja.md) · [Documentation](../README.md) · [Desktop procedure](../how-to/remote-desktop.md)

> Document type: **Explanation**. Server settings and performed changes belong to the [desktop record](../records/desktop-history.md).

## Client, server and protocol

The client is the application operated on Mac. The server is software on Jetson
that accepts the connection, checks the login and supplies a desktop session.
The protocol specifies the messages used between them. Windows App is a client;
xrdp is a server; RDP is the protocol. The remote computer still executes the
applications. The client receives screen updates and sends input events.

The IP address identifies the reachable network endpoint. Authentication then
establishes which Linux user may log in. A Windows App or Microsoft account is
not automatically the Jetson Linux login. Reachable IP, working authentication
and a usable desktop are three different conditions.

## RDP, VNC and NoMachine

| Name | What it identifies | What should be evaluated |
|---|---|---|
| RDP | Remote Desktop Protocol, supported by clients such as Windows App and servers such as xrdp | Session creation, display encoding, latency and supported channels |
| VNC | A family of remote framebuffer clients/servers | Which display is exported, compression and update behavior |
| NoMachine | A remote-desktop product using NX technology | Installed edition, supported physical/virtual sessions and client behavior |

The protocol name alone cannot establish which option is faster for a workload.
Image complexity, encoding, network bandwidth and the actual server/client
configuration matter. Use [Microsoft's client documentation](https://learn.microsoft.com/en-us/windows-app/get-started-connect-devices-desktops-apps),
[the xrdp project](https://github.com/neutrinolabs/xrdp) and
[NoMachine's documentation](https://www.nomachine.com/documents) for supported behavior.

## Physical display and remote session

A desktop session contains a user's graphical applications and settings.
A remote server may share the physical display or create a separate virtual
session. A virtual session need not show the HDMI desktop's exact arrangement.
Depending on the server and desktop environment, simultaneous sessions for the
same account can conflict. Logging out closes that session's applications;
it is not merely hiding its screen.

Clipboard, audio and device redirection are additional channels. A working
picture and mouse do not prove every channel is available. Clipboard operation
needs compatible and enabled behavior on both client and server.

## What an SSH tunnel adds

An SSH tunnel forwards a local TCP connection through an authenticated SSH
connection to a destination TCP endpoint. For example, a client connects to a
Mac-local listener, and SSH carries those bytes to a Jetson-local RDP listener.
That adds a forwarding process on Mac. It is useful when the server is only
reachable that way, but it is not a requirement of RDP.

If the RDP server listens on a reachable, appropriately restricted network
address, the client can connect there directly. This distinction changes how
the screen connection is transported; it does not change where model inference
runs or connect Mac to the robot's internal DDS network. The operating procedure
states which arrangement is currently configured.
