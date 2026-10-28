# Field visit: Ethernet, onboard computers and independent operation

[日本語](field-network.ja.md) · [Field card](field-card.md) · [Network concepts](network-topology.md)

This is a prepared procedure, not a record of a completed robot connection.
No network setting below has been applied. The external Jetson is still separate
from B2. Use the lab's existing handling/stop procedure and leave our motion
sender absent. Obtain a recovery terminal before changing a link used for access.

## 1. Before connecting the cable

Identify B2's designated user Ethernet port and the cable's other endpoint. It
may lead to an internal switch or gateway; it does not necessarily expose every
computer. Confirm the lab's working service IP/subnet, an unused client address,
DDS domain, interface and existing control owner. Obtain authorized access to
the onboard user computer if available. Unknown facts remain unknown; do not
substitute a Go2-W address, a reseller's example, or an assumed domain 0.

Before plugging in, inspect existing Ethernet profiles: automatic DHCP/profile
activation can change routes. On a fresh unconfigured link, prepare the verified
profile below before attachment when possible. Do not overwrite a working lab
profile. Keep current Wi-Fi management intact for this visit.

Use a fresh numbered directory; do not overwrite an earlier visit:

```sh
cd ~/Developer/Projects/Robotics/b2/VLN_B2
mkdir -p local/field-visit-01
ip -br link > local/field-visit-01/link-before.txt
ip -br address > local/field-visit-01/address-before.txt
ip -4 route show table main > local/field-visit-01/routes-before.txt
ip rule show > local/field-visit-01/rules-before.txt
nmcli -f DEVICE,TYPE,STATE device status > local/field-visit-01/devices-before.txt
python3 tools/inspect_target.py --include-network --output local/field-visit-01/external-before.json
```

These inspect local configuration without probing peers. Reports contain private
network information and stay outside Git. Record cable endpoints physically.

## 2. Establish a local IP path

Set the following variables only from verified lab information. They are
placeholders, not robot defaults:

```sh
ROBOT_IFACE='VERIFIED_INTERFACE'
JETSON_ROBOT_CIDR='VERIFIED_UNUSED_ADDRESS/PREFIX'
ROBOT_SERVICE_IP='VERIFIED_SERVICE_ADDRESS'
DDS_DOMAIN_ID='VERIFIED_DOMAIN_ID'
```

`JETSON_ROBOT_CIDR` is the external Jetson's address and prefix, not the robot's
address. A prefix defines the local subnet. An interface is a local port/logical
device. A route chooses where a destination's packets leave. Inspect bridge
membership first: if the address belongs to a bridge, do not configure its slave
port as an unrelated standalone interface.

For a **documented direct IPv4 subnet with static addressing**, first verify
that the profile name `b2-research-link` is unused. Then this template creates
a new profile and explicitly activates it after the cable is connected:

```sh
sudo nmcli connection add type ethernet ifname "$ROBOT_IFACE" \
  con-name b2-research-link connection.autoconnect no \
  ipv4.method manual ipv4.addresses "$JETSON_ROBOT_CIDR" \
  ipv4.never-default yes ipv6.method link-local ipv6.never-default yes
sudo nmcli connection up b2-research-link
```

This changes the external Jetson only. `manual` assigns the agreed client IP;
the connected-subnet route is derived from its prefix. There is no robot-side
internet gateway/DNS setting. `never-default` prevents this profile becoming the
default route; `autoconnect no` keeps initial activation deliberate. See
[NetworkManager IPv4 settings](https://networkmanager.dev/docs/api/latest/settings-ipv4.html).
The profile is saved in the host OS; `up` activates it now. With `autoconnect no`
it is not automatically activated at the next boot. After commissioning, review
persistent link startup separately from application startup and motion arming.
If the lab instead uses DHCP, a gateway, VLAN or an existing bridge, adapt the
profile to that verified topology; do not run this static template unchanged.
Do not use connection sharing, bridge Wi-Fi to B2 or change onboard IPs to make
an unknown topology look like the template.

After attachment, inspect:

```sh
ip -br link
ip -br address
ip route get "$ROBOT_SERVICE_IP"
ip -4 route show default
```

Check physical carrier, the intended local address, and a route through the
verified robot-facing interface with the expected source address. Verify that
management still works in a second Mac terminal. A route through Wi-Fi,
Tailscale or Docker is not evidence of the desired direct robot link. Resolve
overlapping prefixes with the lab before continuing.

Only after that route is correct, test a known authorized service address:

```sh
ping -c 3 -W 1 "$ROBOT_SERVICE_IP"
ip neigh show dev "$ROBOT_IFACE"
```

Ping sends ICMP; the neighbor command reads a cache. Ping failure may reflect
filtering; success proves neither service identity nor DDS. No subnet scan is
needed. During this observation-only visit, deactivate just the new profile if
its route is wrong; the profile remains for inspection:

```sh
sudo nmcli connection down b2-research-link
```

## 3. Subscribe to B2 state

The host venv currently lacks Unitree SDK2/CycloneDDS. Verify an approved SDK
installation and its Python compatibility before running the probe. Use the
verified interface/domain explicitly in a fresh process:

```sh
source .venv/bin/activate
PYTHONPATH=src timeout -k 5s 15s python3 -m b2_tic_vla state \
  --interface "$ROBOT_IFACE" --domain-id "$DDS_DOMAIN_ID" \
  --seconds 3 --output local/field-visit-01/state-01.json
```

The probe sends DDS discovery/subscription traffic but no motor requests. Record
topic, received/valid counts, behavior and source identity. Finite samples do not
establish axes, units, clock alignment or physical readiness. A successful ping
with zero DDS samples calls for interface/domain/type/QoS/firewall inspection,
not random IP changes or running a movement example.

## 4. Identify the onboard computers and services

Use known lab credentials/endpoints and normal host-key verification. The SDK
server need not offer SSH or be the onboard Jetson. Lack of SSH does not prove
the motion service is unavailable. Do not guess accounts or replace firmware.

On each authorized accessible onboard computer, save these local read-only facts
in an approved private record:

```sh
uname -m
cat /etc/os-release
test ! -r /etc/nv_tegra_release || cat /etc/nv_tegra_release
ip -br address
ip route
lsusb
ps -e -o comm=
systemctl list-units --type=service --state=running --no-pager
```

Commands may be absent on a specialized controller. Record that rather than
installing software. Process names avoid dumping command-line arguments that may
contain secrets. Inspect existing Docker/ROS launch definitions with the lab as
needed; keep raw results private. For ROS 2, first identify the existing working
environment, interface/discovery configuration, domain and message packages.
Only then list relevant topics/services in that context; a broad default ROS
discovery on campus Wi-Fi is not an inventory method.

Fill a table for each actual host: physical identity, interfaces, reachable
endpoint, running service, producer/consumer, protocol/topic/domain and evidence.
Keep suspected roles explicitly suspected. Learn how the published walking
service reaches locomotion from existing lab/manufacturer documentation; do not
infer an internal motor bus from external IP reachability.

## 5. Map sensor paths

The operator confirms that the external ZED 2i can connect to the external
Jetson by USB. B2's built-in cameras/sensors cannot be connected directly to that
Jetson by USB in this setup. Treat these as different acquisition paths:

| Source | Visit action | Required evidence |
|---|---|---|
| External ZED 2i | Attach powered USB connection; inspect USB link and SDK access; obtain one RGB image after bindings work | Correct camera/view, link, frame size, rate, buffering, source/receipt timestamps and mount |
| Built-in camera/sensor | Identify attached onboard host and existing driver/export service | Stream/topic, type, format/compression, rate, frame, timestamp meaning, access and reachable transport |
| Livox Mid-360 | Trace Ethernet, power and receiving host/driver | Actual subnet, publisher, point-cloud/pose interfaces and clock source |

The existing ZED adapter deliberately requests left RGB with depth disabled.
RGB-D hardware capability does not mean depth is already consumed. With multiple
cameras, establish device selection before trusting a default SDK camera.
Built-in streams need a supported network export/subscription path; Ethernet
does not automatically forward USB devices. Do not stop existing sensor services
or attach a competing consumer without understanding ownership.

After the actual SDK/binding is available, the external-camera command is:

```sh
PYTHONPATH=src timeout -k 5s 30s python3 -m b2_tic_vla camera \
  --output local/field-visit-01/camera-01/frame.jpg
```

LiDAR may use another Ethernet adapter or a documented common switch/subnet;
neither is selected yet. Do not bridge the robot network to campus to add a
sensor. This project has no direct depth/point-cloud processing adapter; decide
their localization/clearance role separately from TIC-VLA's RGB input.

## 6. Access, boot and operation without campus Wi-Fi

- Complete the deferred [boot/credential checks](system-overview.md#personal-credentials-sharing-and-return).
  Verify local recovery, then cold boot with no GUI login and test SSH.
- Test [remote desktop](remote-desktop.md) from Mac, both with and
  without HDMI, and after logout/reboot. Validate an actual usable framebuffer,
  authentication and restricted access; package presence is not success.
  Establish recovery access and address the documented Tailscale SSH update
  before forwarding tests; preserve the only working remote path meanwhile.
- Identify a lab-approved local management network for mobile use, such as a
  portable access point. Verify Mac and Jetson addressing and ordinary local SSH
  without campus internet. Do not assume Tailscale enrollment/coordination always
  works offline or that the Wi-Fi adapter can provide AP and client concurrently.
- Verify that closing SSH does not own the application lifetime. For now use only
  an offline replay/detached-process exercise; this is not a robot watchdog test.
- Before future motion, validate separately: management-link loss, camera/state
  loss, inference hang, command-process failure and robot-Ethernet loss. Record
  each stop/continue policy and physical receiver behavior. An offline-capable
  planner does not by itself establish acceptable unattended operation.

The intended live program runs under a local supervisor on the external Jetson,
with reviewed local code/assets/configuration and B2 Ethernet. Mac is for
management, not a required inference hop. That robot application/service and its
watchdog are not implemented or enabled. Keep boot in observation/disarmed mode
until explicit motion authorization and stopping behavior have been validated.
See [mobile operation](network-topology.md#operation-away-from-campus-wi-fi).

Complete `examples/onsite-notes.json` in ignored local storage. Keep actual IPs,
identities, sensor recordings and raw service reports outside public Git.
