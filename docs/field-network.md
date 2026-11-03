# Field visit: Ethernet, onboard computers and independent operation

[日本語](field-network.ja.md) · [Field card](field-card.md) · [Network concepts](network-topology.md)

The first physical attachment was inspected on **2026-11-03**. Onboard state
reception passed; direct external-Jetson DDS and motion remain unvalidated.
The numbered sections are operating procedures, not proof that every step has
been completed. Use the lab's handling/stop procedure and preserve recovery access.

## Measured USB connection and its boundary

```text
Mac -- existing Wi-Fi/Tailscale SSH --> external AGX Orin
                                        |
                                  Ethernet (1 Gbps)
                                        |
                             Anker USB Ethernet hub
                                        |
                                B2 USB-C host port
                                        |
                            onboard i7 development PC
                       USB Ethernet       native Ethernet
                             |                   |
                     separate interface   robot service network
                     no bridge found      state DDS domain 0
```

This diagram describes this attachment, not every B2 configuration. The accessible
PC is **Intel Core i7-1265U, x86_64, 12 logical CPUs**, about **15.22 GiB** visible
RAM and a **512,110,190,592-byte NVMe**. It runs Ubuntu 20.04.6 and kernel
5.15.76-rt53. PCI inspection listed Intel graphics; no NVIDIA GPU was listed on
this host. This does not survey other computers inside B2. The manufacturer's
[B2 hardware description](https://support.unitree.com/home/en/B2_developer/About%20B2)
distinguishes platform and user-development computers and optional Orin modules.
This i7 is consistent with a user-development role; it is not identified as the
motion controller. No controller SSH access was attempted.

Scoped IPv6 reached this USB peer and existing authorized credentials worked.
The USB adapter and another adapter on the i7 had the same IPv4 address/subnet,
with different route metrics. Neither was bridged to native Ethernet. IP forwarding
being enabled does not create a working DDS path: return routes, discovery
locators and multicast transport must also work. We did not change those settings.

Only the external Jetson was temporarily assigned a documented native-LAN client
address using a new `b2-research-link` profile. Address-conflict probes received
no reply, but do not rule out an offline duplicate. The direct native-service
IPv4 test failed over this USB path. The original active wired profile was then
restored; the new profile remains saved with autoconnect disabled. Wi-Fi stayed
the default route. Never activate an unrelated saved profile merely because its
subnet resembles a manufacturer example.

On the i7's native Ethernet, the documented service address answered ping and
RTPS discovery advertised domain **0**. A 12-second receive-only check using the
existing Foxy/Cyclone DDS installation received **5,994** `/sportmodestate` and
**240** `/lf/sportmodestate` messages of type `unitree_go/msg/SportModeState`.
All checked position, velocity, yaw-rate and attitude values were finite.
This proves onboard reception only. It does not establish coordinate conventions,
source-clock alignment, navigation quality, external reception or command acceptance.
Discovered camera/odometry topic names alone do not validate their payloads or ownership.
Raw inventories and state evidence remain private under `local/b2-connection-01`.

For direct external SDK use, identify the supported **Network/Ethernet/GbE
breakout** that reaches the native robot network. The operator could not locate
one among the available accessories. The USB hub alone is not a substitute.
Alternatively, a separately reviewed program/router on the i7 could relay data
and requests; that changes the deployment and is not installed. Do not enable
bridging, NAT or a command relay as an automatic workaround. The manufacturer
prohibits hot-swapping aviation connectors; follow the lab's powered-down handling
procedure when changing that kind of connector. The diagram does not map motor buses.

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
mkdir -m 700 local/field-visit-01
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

Use the already built [state-only image](unitree-runtime.md), not the host
venv that lacks SDK/DDS dependencies. Offline import/serialization passed; the
following real robot subscription has **not** been run. Use the confirmed
interface/domain and the fresh private directory created above. Host networking
is needed here to reach the selected robot-facing interface, unlike the offline
verifier's `--network none`. This shares networking, not the host filesystem or
credentials, and does not bridge networks.

```sh
sudo docker run --rm --pull never --runtime runc --network host --read-only \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --memory 1g --cpus 2 --pids-limit 64 --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  --mount "type=bind,src=$(pwd)/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$(pwd)/local/field-visit-01,dst=/reports" \
  -e HOME=/tmp -e PYTHONPATH=/workspace/src:/opt/vendor/unitree_sdk2_python \
  --entrypoint timeout vln-b2-unitree:jp5 -k 5s 15s \
  /opt/unitree/bin/python -m b2_tic_vla state \
  --interface "$ROBOT_IFACE" --domain-id "$DDS_DOMAIN_ID" \
  --seconds 3 --output /reports/state-01.json
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

### Repeat the onboard receive-only check

This optional diagnostic runs **inside the authorized i7 SSH terminal**, not on
Mac or the external Jetson. It uses existing packages and a child shell; do not
install ROS or run a robot launch file. First verify the workspace setup file
and the native robot-facing interface from the private inventory. Replace both
placeholders below. Domain 0 was measured on this unit; recheck it for another
unit. Explicit interface selection keeps discovery off the campus Wi-Fi.
The system Python 3.8 matches Foxy's bindings; the existing conda Python 3.11
does not establish ABI compatibility.

```sh
bash --noprofile --norc <<'SH'
set -e
export PATH=/usr/bin:/bin:/opt/ros/foxy/bin
UNITREE_ROS_SETUP='VERIFIED_WORKSPACE/install/setup.bash'
ROBOT_IFACE='VERIFIED_NATIVE_ROBOT_INTERFACE'
source /opt/ros/foxy/setup.bash
source "$UNITREE_ROS_SETUP"
export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=0 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="<CycloneDDS><Domain><General><NetworkInterfaceAddress>${ROBOT_IFACE}</NetworkInterfaceAddress><AllowMulticast>true</AllowMulticast></General></Domain></CycloneDDS>"
/usr/bin/python3 - <<'PY'
import json
import math
import time
import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from unitree_go.msg import SportModeState

rclpy.init(args=['--ros-args', '--disable-rosout-logs', '--disable-external-lib-logs'])
node = rclpy.create_node('b2_read_only_state_check', enable_rosout=False,
                         start_parameter_services=False)
report = {'received': {}, 'finite': {}}
qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT,
                 durability=DurabilityPolicy.VOLATILE)

def receive(message, topic):
    values = [float(v) for v in message.position]
    values += [float(v) for v in message.velocity]
    values += [float(v) for v in message.imu_state.rpy]
    values += [float(message.yaw_speed)]
    report['received'][topic] = report['received'].get(topic, 0) + 1
    report['finite'][topic] = report['finite'].get(topic, 0) + int(
        all(math.isfinite(v) for v in values))

subscriptions = []
try:
    for topic in ['/sportmodestate', '/lf/sportmodestate']:
        subscriptions.append(node.create_subscription(
            SportModeState, topic, lambda msg, t=topic: receive(msg, t), qos))
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.2)
    print(json.dumps(report, allow_nan=False))
finally:
    node.destroy_node()
    rclpy.shutdown()
PY
SH
```

Expected output has positive `received` counts with matching `finite` counts
for each received topic. Empty counts mean no messages were received, even if
the process exits successfully. This creates only subscriptions and DDS discovery
traffic, with no command publisher, ROS daemon or motor service call. It does
not save a state stream, synchronize clocks or connect the model to live state.
The inspected Cyclone DDS accepted `NetworkInterfaceAddress` with a deprecation
warning; do not replace the existing installation to remove that warning.
Closing the child shell discards its environment settings. Keep the result private.

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

The host-only camera example below requires SDK/binding dependencies. On the
prepared target, use [the isolated camera environment](camera-runtime.md) or
[bounded camera observer](asynchronous-runtime.md); do not run it in the bare
host venv and interpret a missing binding as a camera failure:

```sh
PYTHONPATH=src timeout -k 5s 30s python3 -m b2_tic_vla camera \
  --output local/field-visit-01/camera-01/frame.jpg
```

LiDAR may use another Ethernet adapter or a documented common switch/subnet;
neither is selected yet. Do not bridge the robot network to campus to add a
sensor. This project has no direct depth/point-cloud processing adapter; decide
their localization/clearance role separately from TIC-VLA's RGB input.

## 6. Access, boot and operation without campus Wi-Fi

- Review the completed [boot/credential checks](system-overview.md#personal-credentials-sharing-and-return).
  eduroam system saving, a headless software reboot and subsequent SSH/RDP
  passed. Verify local recovery, then test a physical power cycle and SSH.
- Test [remote desktop](remote-desktop.md) from Mac, both with and
  without HDMI, and after logout/reboot. Validate an actual usable framebuffer,
  authentication and restricted access; package presence is not success.
  Direct tailnet RDP is now prepared; the Mac needs no SSH forwarding. Keep
  recovery access, confirm the new-route GUI login and preserve working SSH.
  Tailscale/eduroam reboot recovery was previously tested; the new RDP guard
  has passed service restarts, not a new whole-device reboot.
- Assume no separate AP. Follow [offline operation](offline-operation.md) to
  inspect a possible Jetson AP and direct local OpenSSH before a console-backed
  switch; no internet or concurrent eduroam/AP service is assumed. Mac remains
  optional for the core loop. Verify the B2 remote's manual takeover, stopping
  and research-command inhibition separately; no button behavior is assumed.
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
