# Offline operation without a separate access point

[日本語](offline-operation.ja.md) · [Documentation](README.md) · [Field procedure](field-network.md)

## Operating assumption and completion status

Assume no portable laboratory AP is available. The intended core loop runs on the
external Jetson with local assets, sensor input and a wired B2 connection. Mac
and internet are optional management resources. This is a target design: the
live application, command sender, arming logic and watchdog are not implemented.
No hotspot profile or offline robot operation has been tested or enabled.
On 2026-10-28, NetworkManager and `iw list` both reported AP support on the
existing radio; its listed interface combinations share a single channel.
Direct LAN OpenSSH worked from Mac. These facts do not establish AP/client
concurrency in the field, hotspot association, range or offline cold boot.

A network-independent computation does not imply an unsupervised experiment.
Trials still need a verified operator control/stop procedure and a defined
operating area. The operator reports that B2 has its own remote controller;
identify its exact behavior instead of treating a Mac terminal as the only stop.

## 1. Why would Mac be connected while running?

Mac can request a start/stop, show status/video, change a future task between
trials, or retrieve logs. Those are useful interfaces, not a computational need
for every camera frame, inference call or walking request. If a future design
streams images to Mac for inference, it would introduce a link dependency;
that is not the deployment proposed here.

Before a prepared trial, Jetson needs the exact reviewed code and runtime,
model/tokenizer/configuration assets, instruction, sensor calibration, known B2
network configuration, logging space and local lifecycle configuration. Record
these locally. No download, GitHub pull or cloud model call belongs in the live
loop. Current tools are not yet that offline autonomous service.

A future local supervisor should start in observation/disarmed mode. Arming is a
separate explicit operator action. Closing SSH must not be the definition of
process lifetime, and service restart must not rearm motion. A detached Docker
process can survive a terminal closing, but that alone supplies neither input
freshness checks nor measured B2 stop behavior.

## 2. Two different networks, and an optional third path

```text
                  OPTIONAL MANAGEMENT
Mac -- Wi-Fi --> external Jetson acting as local AP
                       |
                       | local Python / inference / supervision
                       |
                       +-- Ethernet --> B2's supported user network
                       |
                       +-- USB --> external ZED candidate

B2 remote controller -- its existing independent radio path --> B2 control
                        actual arbitration/stop behavior to verify
```

The local AP assigns no magical internet connection. In the proposed manual-IP
profile below, neither Mac nor Jetson has internet through that AP, and no
routing/NAT is added between Wi-Fi and robot Ethernet. Inspect pre-existing
forwarding/firewall/bridge settings as well; this template alone does not prove
host-wide isolation. B2 remains on its separate verified subnet. A camera/local program can continue without internet.
The actual availability of the pictured sensor/control links remains to be tested.

When the one Wi-Fi radio changes from eduroam-client mode to AP mode, expect the
current eduroam/Tailscale SSH route to disappear. Simultaneous AP/client service
is not assumed. A configured hotspot is a new Wi-Fi role on the existing radio,
not extra hardware. Verify driver AP support, permitted channel/band and actual
client association; a radio model name alone is insufficient.

Use ordinary OpenSSH to the verified local AP address. Tailscale SSH intercepts
its own overlay path, not automatically every local LAN address. Prepare a real
local OpenSSH authentication method and verify its listener/firewall first.
Do not assume a tailnet identity alone authenticates a new offline LAN SSH login
or that new Tailscale peer coordination always succeeds without internet.

## 3. Read-only preparation

Run these on Jetson when access is available; they do not activate a profile:

```sh
ip -br address
ip -4 route
nmcli -f DEVICE,TYPE,STATE device status
nmcli -f GENERAL.DEVICE,WIFI-PROPERTIES.AP device show wlan0
command -v iw
ss -lnt '( sport = :22 )'
```

`wlan0` is the previously observed interface, not a universal name. If `iw` is
installed, `iw list` exposes supported interface modes and combinations; inspect
it locally without publishing identifying details. An absent tool is a finding,
not a reason to alter the only working network remotely. Check the configured
Docker subnet ranges as well before choosing a new AP subnet.

Before switching, verify Mac has an approved local SSH credential and that the
Jetson's host SSH server accepts it on an appropriate local interface. Check
existing firewall policy and host-key verification. Do not solve authentication
by opening passwordless login or broadening every firewall rule. Never place a
private key or hotspot password in Git, a Docker image or a chat.

## 4. Prepared hotspot template: not executed

The first switch requires a local console or another already-tested recovery
path. A remote shell that depends on the same Wi-Fi radio is not recovery.
Confirm AP capability and select unused addresses/subnet distinct from B2,
Docker, Tailscale and any other active interface. The placeholders below require
real verified values; they are not robot/default addresses.

```sh
AP_IFACE='VERIFIED_WIFI_INTERFACE'
AP_JETSON_CIDR='VERIFIED_UNUSED_JETSON_AP_ADDRESS/PREFIX'
EDUROAM_PROFILE_UUID='VERIFIED_EXISTING_EDUROAM_PROFILE_UUID'
```

Check that `b2-local-management` is an unused profile name. This template creates
a persistent, manually activated WPA2-Personal AP profile with a static Jetson
address. It does not create DHCP, DNS forwarding, NAT or a campus/robot bridge:

```sh
sudo nmcli connection add type wifi ifname "$AP_IFACE" \
  con-name b2-local-management ssid B2-Research \
  connection.autoconnect no 802-11-wireless.mode ap \
  802-11-wireless-security.key-mgmt wpa-psk \
  802-11-wireless-security.proto rsn \
  802-11-wireless-security.psk-flags 0 \
  ipv4.method manual ipv4.addresses "$AP_JETSON_CIDR" \
  ipv4.never-default yes ipv6.method link-local ipv6.never-default yes
sudo nmcli --ask connection up b2-local-management
```

Review the target's installed `nmcli` help before applying. `--ask` requests the
missing hotspot PSK interactively rather than putting it in command history.
Use a separate strong hotspot secret; it is not the eduroam or Linux password.
`psk-flags 0` requests system storage; verify root-only profile protection and
actual storage afterward. The university password is not copied into this AP.
The SSID is a generic example and can be changed before deployment. See
[NetworkManager's CLI manual](https://networkmanager.dev/docs/api/latest/nmcli.html).

Unlike `nmcli device wifi hotspot`, which normally creates a shared connection,
this manual-address proposal deliberately avoids automatic internet sharing.
It therefore needs a **manual Mac address** in the same selected subnet, a
different host address, and no router/DNS for this offline link. Record both
addresses privately before switching. The Mac's connection to an offline SSID
and direct Jetson SSH must be tested; do not let the Mac silently reconnect to
another network and mistake that for a successful local link.

From Mac, after that setup, use its actual local address/port and conventional
SSH credentials:

```sh
ssh RESEARCH_USER@JETSON_AP_ADDRESS
```

`connection.autoconnect no` means saving this profile does not select AP mode
at next boot. Decide desk/client versus field/AP boot behavior only after
commissioning. Do not make the AP win boot selection over eduroam accidentally.
To return during the first console-backed test, deactivate only the new profile
and reactivate the verified original one:

```sh
sudo nmcli connection down b2-local-management
sudo nmcli --ask connection up uuid "$EDUROAM_PROFILE_UUID"
```

Do not recreate/delete eduroam merely to change modes. Restore Mac's normal IP
configuration when returning to campus Wi-Fi. System-stored AP secrets also need
review during a later handover. None of these activation commands has been run.

## 5. The B2 remote controller is a separate control path

The lab's existing remote controller is a useful candidate for initial posture,
manual positioning, operator takeover and the documented stop procedure. It
should not depend on Mac, eduroam, Tailscale or the model process. Its actual
receiver/control relationship still needs confirmation; independence of one
radio does not prove independence of every internal controller.

At the visit, record the remote model, pairing/battery/status, exact documented
buttons/modes, control priority and operating limits. Have a trained operator
demonstrate the established procedure under the lab's handling rules. Before any
research motion, verify whether manual takeover inhibits SDK requests and
whether research software remains disarmed until a fresh authorization. Do not
let a background sender resume immediately after the operator releases control.

Distinguish a zero-velocity request, a posture/motor-mode change, damping or power
cut, and an actual emergency-stop function. They can have very different effects
on a standing quadruped. Do not invent a button combination or call any of them a
certified emergency stop based on its name. SDK stop request returns are not
physical stopping measurements. Record the applicable documented procedure,
observed result and limitations before selecting the trial's independent stop.

## 6. Failure cases need separate acceptance tests

| Event | Required policy/evidence before motion |
|---|---|
| Mac window/SSH disconnect | Local process lifetime independent of that terminal; chosen operator-supervision rule still enforced |
| Mac/AP link lost | Explicit experiment policy: disarm/stop for required operator link, or continue only under separately approved independent supervision |
| Camera or robot state stale | Reject/expire affected plans/commands and take the validated stop path |
| Model slow or hung | Respect valid cache/deadlines; no indefinite reuse of an old plan |
| Process/container fails | Local supervisor detects failure; receiver command-loss response measured; restart remains disarmed |
| Robot Ethernet lost | Local action alone cannot deliver a stop over a broken cable; measure B2's timeout and independent operator response |
| B2 remote controller lost | Follow the measured/documented receiver response and trial policy; do not assume indefinite manual authority |
| Internet unavailable | Prepared local inference/logging/control should not request internet; verify with network access removed during non-motion tests first |

Current expiry checks in pure software do not implement or prove this complete
contract. Begin with offline replay and observation-only lifecycle tests; then
validate physical command ownership/stopping in a separately controlled stage.
No link-loss robot test has been performed.

## 7. Acceptance and evidence

Record the AP driver capability, private address plan, local SSH authentication,
protected profile state and rollback. First demonstrate a no-motion offline
process continuing when Mac disconnects, and that reconnect retrieves its logs.
Test RDP over the same local SSH tunnel only after its server is commissioned.
Then verify cold boot/profile selection, login-independent access and the
specified disarmed startup. Keep the initial test console-backed.

The final motion acceptance additionally needs measured sensors/time/frames,
command authority, stop behavior and a bounded experiment plan. Store raw notes
in ignored `local/`; publish only reviewed descriptions. Mac independence,
internet independence and acceptable operator supervision are three distinct
claims, each requiring its own evidence.
