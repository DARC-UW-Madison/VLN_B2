# Computers, network, SDK, and ROS 2

[日本語](network-topology.ja.md) · [Home](../README.md) · [Onsite guide](onsite.md)

The external AGX Orin now reaches an onboard **Intel i7 development PC** through
the B2 USB-C/Anker Ethernet hub. That PC's native Ethernet receives actual robot
state in DDS domain 0; the USB interface is separate and unbridged. Direct DDS
from the external Jetson remains unvalidated. Mac management over existing
Wi-Fi/Tailscale is independent. See [the current measured wiring](field-network.md)
and [the initial external baseline](target-baseline.md).
An additional onboard Jetson and the complete motion-control hardware remain
unverified. Do not treat the accessible i7 as the locomotion controller.

## What the external Jetson can control

An external computer can be the client of B2's published high-level walking API.
The official [B2 SportClient](https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/unitree_sdk2py/b2/sport/sport_client.py)
provides velocity requests and a stop request. This supports the proposed division:
external perception/planning, existing robot locomotion. It does not establish
which computer hosts the service on this robot, network reachability, operating
mode, command ownership, or physical stop behavior. `Move` uses a no-reply call;
its return does not confirm physical execution.

We aim to develop and run TIC-VLA on the external Jetson while retaining the
robot's existing locomotion software. This can avoid changing onboard software
**if** the needed state/control services and sensor streams are accessible.
Existing onboard localization, sensor drivers, network isolation, or control
arbitration may still require inspecting or integrating with the onboard Jetson.
Access to high-level walking is not unrestricted access to every robot function.

Unitree's [B2 specifications](https://www.unitree.com/b2/) distinguish platform
and user-development computers and list configuration options. They do not
identify the configuration of this lab robot. Treat “three computers plus Mac”
as a working inventory, not proof of the complete internal architecture.

| Host role | Intended responsibility | Evidence needed |
|---|---|---|
| Mac | Edit files, transfer code, optionally SSH to external Jetson, inspect results | Actual management connection; it need not participate in DDS |
| External Jetson | Camera input, TIC-VLA inference, tracking and eventually one command sender | OS/L4T, memory, interfaces, reachable SDK services and GPU runtime |
| Onboard development PC / possible additional Jetson | Preserve existing services; possible sensor/localization provider | Intel i7 measured and onboard state received; sensor ownership and additional Jetson remain unverified |
| Motion-control system | Preserve existing walking, balance, and actuator control | Manufacturer/lab interface description, service endpoint and operating procedure |

A host can have several IP addresses, aliases, containers, or virtual interfaces.
A cached neighbor or a recognizable address is not sufficient to identify a
computer. The host running the SDK service may also differ from the controller
ultimately operating the actuators.

## Proposed connections, not measured wiring

```text
Mac -- management link / optional SSH --> External Jetson
                                           |
                                 robot-facing Ethernet
                                           |
                              B2-side network (unverified)
                                  /                 \
                       Onboard Jetson       Published walking service
                       sensors/services       -> motion-control system
```

This is a logical deployment proposal. The switch layout, VLANs, routers, service
host, and reachability are unknown. It does not assert that the two internal
computers are both directly exposed on the external Ethernet port. Confirm the
cable endpoints physically. ZED USB and Mid-360 Ethernet connections must be
mapped to their actual host; their models do not establish where their data goes.

Prefer the external Jetson's wired link for robot traffic. Its Wi-Fi or a second
interface can independently serve Mac management and internet access. Check for
overlapping subnets and conflicting routes before deciding their configuration. With the
application running on that Jetson, Mac's SSH session and Jetson's DDS traffic
are separate connections. This design requires neither forwarding Mac packets
into the robot LAN nor a Wi-Fi/Ethernet bridge. Preserve an existing working
bridge if present until its role and recovery path are understood; do not remove
it based on this proposal. An SSH tunnel alone is not a general DDS network.

## Separate the communication layers

1. **Ethernet/IP:** cables, link state, addresses/prefixes, routes, and reachable
   interfaces. Similar-looking addresses do not establish a working path.
2. **DDS:** participant discovery and data exchange. Interface, domain, discovery
   configuration, message types, QoS and firewall behavior must be compatible.
3. **Unitree SDK2:** application APIs for status and robot requests on DDS. It
   does not require a ROS 2 installation on the external Jetson.
4. **ROS 2:** an optional framework for nodes, topics, sensor processing, SLAM,
   recording and visualization. Its DDS/RMW and interfaces must match the intended
   participants; installing ROS 2 does not configure robot connectivity.

Unitree documents [SDK2/ROS 2 DDS interoperability](https://github.com/unitreerobotics/unitree_ros2).
ROS 2 can communicate using compatible messages without an SDK wrapper. A ROS
adapter is useful when it actually converts application interfaces or coordinate
frames; it is not automatically needed between an external SDK client and B2.
Do not stop existing onboard ROS 2 services just because the first external probe
uses SDK2 directly. Several status readers can coexist; independent command
writers require explicit ownership and arbitration.

The Python [channel factory](https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/unitree_sdk2py/core/channel.py)
takes a domain ID and interface explicitly and initializes a process-global DDS
factory. `ROS_DOMAIN_ID` configures ROS processes; changing it does not rewrite
the argument passed by a separate SDK process. Our probe defaults to domain 0
but accepts `--domain-id`. Domain **0 was observed on this B2's native network**
and onboard ROS state reception passed there. This does not establish external
reachability. For another setup, identify the intended service's domain instead
of cycling through values or copying a reseller's configuration.

Inspect the installed SDK's initialization code and any patches before deciding
how `CYCLONEDDS_URI` interacts with a programmatic configuration. Do not assume
an environment variable always wins. Keep the first probe in a fresh terminal,
record relevant environment settings, and make only justified per-process changes.

## Standalone setup, accounts, and remote operation

Use [the host bootstrap procedure](jetson-bootstrap.md) for operator commands.
The selected remote path is Tailscale SSH; management access over Tailscale has
now been independently verified. See the measured baseline for completed checks.

The external Jetson can be prepared on the desk before attachment to B2. The
intended application is images/instruction -> TIC-VLA path prediction -> tracking
-> Unitree SDK velocity request -> existing B2 walking control. This is a target
architecture; the command sender and live asynchronous integration remain unimplemented.

| Component | Responsibility | Initial approach |
|---|---|---|
| JetPack/CUDA and compatible PyTorch | Host GPU support and model execution | Inspect the existing L4T and runtime before choosing packages |
| Unitree SDK2 | B2 state access and robot requests over DDS | First verify state reception on the host; no ROS 2 prerequisite |
| ZED SDK | ZED camera access | Separate from Unitree SDK; verify the actual camera and matching binding |
| ROS 2 | Optional sensor pipelines, SLAM, recording and visualization | Add for a defined dependency; preserve existing onboard services |
| Docker | Package application dependencies for repeatable execution | Evaluate a compatible image after host inventory; it is not a robot-control protocol |

Containerization does not replace the Jetson host's GPU drivers or make arbitrary
CUDA/PyTorch/ZED versions compatible. Match the image to the installed platform
and expose the required GPU/camera devices deliberately. `deploy/Dockerfile` is a generic CLI wrapper requiring an explicit base;
`deploy/jetson-runtime.Dockerfile` is the separately built model-free GPU candidate
documented in the runtime guide. Neither establishes a complete live robot stack. See [NVIDIA JetPack setup](https://docs.nvidia.com/jetson/jetpack/install-setup/index.html)
and [Stereolabs' Jetson container guidance](https://docs.stereolabs.com/docs/integrations/docker/install-on-nvidia-jetson).

For a lab device, use a host Linux account assigned to the researcher. If the
current account already serves that purpose, another is optional; if it belongs
to a previous user, create a new research login. Multiple researchers should
have separate logins and individual authentication identities. Use individual
SSH keys with conventional OpenSSH; Tailscale SSH authenticates through tailnet
identities and policy; see [Tailscale SSH](https://tailscale.com/docs/features/tailscale-ssh). Use ordinary permissions for routine work
and administrator privileges only where needed. A new login separates home
files and credentials; it does not create another OS or isolate system drivers.
Host login accounts and users inside containers are different configuration
layers. See [Ubuntu user management](https://ubuntu.com/server/docs/how-to/security/user-management/).

Prefer Mac-to-Jetson SSH for development, with the connected display/keyboard
available for initial setup and recovery. The SSH server runs on the Jetson
host. An ordinary reachable LAN/Wi-Fi path is enough; VPN is optional for remote
or otherwise separated networks. Same Wi-Fi does not guarantee peer access if
client isolation or firewall rules block it. Use a lab-approved VPN for the
management link when needed; reaching the Jetson is sufficient for this design,
without advertising the robot subnet. A VPN does not replace SSH or the
Jetson-to-B2 wired DDS connection. See [Ubuntu OpenSSH](https://ubuntu.com/server/docs/how-to/security/openssh-server/).

Wi-Fi and robot Ethernet can remain active together. Preserve the intended
management/internet route, avoid overlapping subnets, and identify the robot
interface explicitly. Configure the robot-side address from the actual lab or
manufacturer specification; do not add an unnecessary default route through B2.
The physical destination is the supported B2-side Ethernet network, not necessarily
a direct connection to an onboard application's host. The measured USB path is
separate from the native robot LAN; other internal wiring remains
to be mapped.

Proceed with host inventory -> account and local SSH -> optional VPN -> GPU and
compatible runtime checks -> SDK dependencies and offline model inference. Saved
images and explicitly labeled synthetic state allow software tests without B2;
model files and approved inputs must still be obtained separately. A ZED attached
to the desk setup can be tested there. Actual B2 state/control, sensor connections
left on the robot, mounting geometry, command loss, and autonomous operation
require later integration on the real robot. Management SSH, the host baseline
and model-free GPU/import checks are verified. Model loading and robot
integration remain unverified.

## Operation away from campus Wi-Fi

Campus Wi-Fi is a current management/internet connection, not the intended
robot-control transport. Roaming between access points can interrupt traffic;
outside coverage there may be no connection. Tailscale needs an underlying
network path and cannot supply radio coverage.

The intended local data loop is camera/state → local inference → local tracking
and supervision → SDK2/DDS over robot Ethernet. Reviewed code, model assets,
instruction/configuration and logs must be local before an offline run. Mac is
an optional management/visualization endpoint, not an inference server or a
required relay for every velocity request. No cloud call is planned for that loop.
The current model-free image runs with `--network=none`; this does not prove
future live inference or offline robot integration, which remain unimplemented.

An ordinary SSH foreground process can depend on its terminal session. A
detached process, terminal multiplexer, systemd service and container are
different lifetime/supervision mechanisms: creating a container does not by
itself detach its terminal or implement a robot watchdog. The existing build was
detached. The future robot application should have a local supervised lifecycle
and explicit arm/stop state; it is not installed as a service. See
[systemd service semantics](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html).
Restarting software must not automatically authorize movement after a fault.

Assume no separate AP is available. Mac is optional during a prepared run;
if local monitoring is needed, a Jetson-hosted Wi-Fi AP is a candidate after
radio/driver capability and direct OpenSSH authentication are verified. Both
machines may be offline. A single radio switching to AP mode can remove the
current eduroam/Tailscale path; first test with console recovery. Keep B2 on its
separate Ethernet subnet, without campus/robot forwarding. No AP profile has
been configured. The [offline-operation guide](offline-operation.md) provides
a manual-address template, rollback and acceptance criteria, without assuming
AP/client concurrency or internet-free Tailscale coordination. The existing B2
remote controller is a separate candidate for manual positioning/takeover/stop;
its actual arbitration and physical stop behavior still require validation.

Define two different events: loss of the **management/operator link** and loss
of **robot control/state/sensor data**. The core loop should not require an open
Mac SSH terminal. Whether it may continue after operator-link loss depends on
the trial's supervision/stop policy. A deadman-controlled trial may deliberately
require stopping. Robot Ethernet loss, stale live inputs, inference hangs and
process failure need independent expiry/watchdog behavior and measured receiver
response. Neither Tailscale nor a container restart policy supplies that safety
contract. Existing robot stop and override procedures remain essential.

Use [the field procedure](field-network.md) for cable attachment, IP/route
verification, state-only DDS, onboard inventory, sensor mapping and mobile tests.
The external ZED 2i can be USB-connected to the external Jetson; built-in B2
sensors require their existing onboard/network path. No direct built-in USB
connection to the external Jetson is available in the reported setup.

## First collection on the external Jetson

Remote SSH inspection has now completed; see the [baseline](target-baseline.md).
The following remains a manual collection alternative in the Jetson's own Linux
terminal. No project checkout is needed:

```sh
cat /etc/os-release
cat /etc/nv_tegra_release
ip -br address
ip route
bridge link
```

A missing file/tool is useful evidence; do not install packages to conceal it.
These commands read local configuration, send no robot requests and change no
network settings. Record how the external Jetson's Ethernet cable is actually
connected, how Mac is connected, and whether B2 is powered. The command output
cannot reveal the far end of a cable or identify every internal computer.

With the current project available, use one optional detailed inventory instead:

```sh
python3 tools/inspect_target.py --include-network --output local/external-jetson-01.json
```

The optional report adds address prefixes, link state/master, IPv4 route tables,
bridge ports, existing neighbor-cache entries, and selected forwarding/filtering
kernel flags. It performs no ping, subnet scan, peer login, packet capture, or
firewall changes. Missing tools and unrecognized JSON are reported explicitly.
This describes only the current network namespace; run on the Jetson host rather
than inside a container to identify its physical links. The report includes local
IP/MAC data: keep it in ignored `local/`, review before sharing, and do not commit
raw output or credentials to public documentation.

## Proceed through independent completion gates

| Stage | Action | Completion evidence |
|---|---|---|
| 1. Inventory and wiring | Inspect external Jetson; identify cable endpoints and existing management access | OS/L4T report and an annotated role/interface map |
| 2. Route | Identify the documented robot service address/subnet and its actual egress interface | Local route lookup and a justified route; no copied static address |
| 3. State-only DDS | Use the SDK subscriber on the host with explicit interface/domain | Finite changing state, topic, rate, and verified robot identity |
| 4. Sensors and internal services | Capture ZED RGB; inspect known onboard services only as needed | Actual stream origins, frames and timestamps; onboard dependencies identified |
| 5. Runtime selection | Select native environment or compatible container after host probe works | Same state/image delivery under the selected runtime, including timing |
| 6. Control and inference | Verify ownership/stop procedure, then controlled command tests and offline/live shadow inference | Separate evidence for physical commands, model execution, and later autonomous integration |

Once a documented destination is known, `ip route get ROBOT_SERVICE_IP` reads
which route Linux would choose. Replace the placeholder; the lookup does not
prove that the destination exists. A bounded ping to a known, authorized address
can subsequently test ICMP reachability but cannot validate DDS. Do not infer
service identity from ping alone or scan the subnet as the initial diagnostic.

Choose the DDS interface that owns the relevant address. If a physical port is
a member of a bridge, that address may belong to the bridge rather than the
physical port. Do not automatically use `eth0`, the default internet route, or a
Docker virtual interface. Preserve the working management connection while
reviewing overlapping prefixes and routes.

After identifying the real interface and domain, the existing observation-only
command is:

```sh
PYTHONPATH=src timeout -k 5s 15s python3 -m b2_tic_vla state \
  --interface IFACE --domain-id DOMAIN_ID --seconds 3 --output local/state-01.json
```

The subscriber listens to normal and low-frequency sport-state topics. A topic
name seen on Go2-W is not proof of B2 behavior. Keep the candidate command sender
absent during discovery. No public example with “test” in its name should be
assumed observation-only; some examples start movement as part of initialization.

Introduce ROS 2 only for a defined dependency. When Docker is needed, verify
networking again: Linux host networking shares the host network namespace, while
Docker Desktop has different constraints. Do not assume Mac container behavior
matches Jetson Linux. See [Docker's host-network documentation](https://docs.docker.com/engine/network/drivers/host/).

## Record the result without exposing the lab network

Keep the address/interface/service table in approved local storage. Publish only
a sanitized diagram using host roles. For each link, record physical cable,
interface, subnet, selected route, observed service and the evidence date. For
each service, distinguish its host, protocol/domain/topic, consumer, and command
owner. Mark an inferred role as inferred until the computer or documentation
confirms it. Update [project status](status.md) when actual target evidence arrives.
