# Computers, network, SDK, and ROS 2

[日本語](network-topology.ja.md) · [Home](../README.md) · [Onsite guide](onsite.md)

The immediate goal is to establish who runs each service and how the external
Jetson reaches it. Do this before adding ROS 2 packages, containers, network
bridges, or model inference. The operator uses the **external Jetson** with a
directly connected display and keyboard, separately from the robot. A B2 network
connection and a Mac management link have not yet been demonstrated.
They also report an onboard Jetson and believe a separate motion-control computer
is present. Their exact identities, service placement, and wiring remain unverified.

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
| Onboard Jetson | Preserve existing services; possible sensor/localization provider | Module identity, actual running services, interfaces, sensor ownership |
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
but accepts `--domain-id`; **0 is not a measured B2 setting**. Identify the intended
service's domain from a working lab setup or manufacturer documentation instead
of cycling through values or copying a reseller's configuration.

Inspect the installed SDK's initialization code and any patches before deciding
how `CYCLONEDDS_URI` interacts with a programmatic configuration. Do not assume
an environment variable always wins. Keep the first probe in a fresh terminal,
record relevant environment settings, and make only justified per-process changes.

## First collection on the external Jetson

No remote connection to the Jetson has been established from this chat. Execute
these commands in its own Linux terminal. No project checkout is needed:

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
