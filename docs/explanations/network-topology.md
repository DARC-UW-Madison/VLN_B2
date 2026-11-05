# From an Ethernet cable to a robot request

[日本語](network-topology.ja.md) · [Documentation](../README.md)

> Document type: **Explanation**. This chapter explains communication mechanisms. Hardware inventories, commands actually executed and test results are in [the B2 connection record](../records/b2-connection-2026-11-03.md); executable checks are in [the connection procedure](../how-to/field-network.md).

## 1. Where a program runs matters

Opening an SSH connection means logging into another computer and executing
commands there. If a terminal on Jetson logs into the i7 and starts Python,
that Python process uses the i7's network interfaces. It does not use Jetson's
interfaces simply because the keyboard input came from Jetson.

Compare two arrangements:

```text
A. Jetson application -> Jetson network -> B2 robot service
B. Jetson SSH client -> i7 SSH server -> start an application ON i7
                                      i7 application -> B2 robot service
```

Here a robot service means a running program accepting requests such as a
posture change. In A, Jetson constructs and exchanges the robot messages. In B,
SSH transports the command to start a program; the i7 program then constructs
and exchanges robot messages. B does not require the i7 to forward Jetson's
robot-network packets. Starting ROS 2 nodes through SSH is arrangement B.
It is not direct ROS 2 communication from Jetson.

“Direct” in this manual refers to the application endpoints, not a requirement
for a single uninterrupted cable. A switch or correctly configured router can
sit between Jetson and B2 while Jetson remains the robot API client.

## 2. What a USB Ethernet adapter connects

A USB Ethernet adapter adds a network interface to the computer at its USB end.
An interface is an operating-system connection for sending and receiving data.
If the USB end is attached to the i7, the Ethernet socket belongs to the i7.
It does not automatically connect to every other Ethernet network inside B2.

```text
Jetson -- Ethernet cable -- USB Ethernet adapter -- USB -- i7
                                                        |
                                      another i7 Ethernet interface
                                                        |
                                               robot internal LAN
```

A LAN is a local network. “Robot internal LAN” here means the network on which
the robot's state/control programs exchange data. An i7 with one connection
to Jetson and another to this LAN has two independent interfaces until a
forwarding mechanism is configured.

There is nothing inherently unsuitable about the adapter brand in this diagram.
A different physical Ethernet connection is one way to reach the internal LAN;
forwarding through the i7 is another. A connector's shape does not establish
which LAN it reaches. **Ethernet access to the internal LAN** means a connection
that can exchange data on that LAN; the connector mapping is established by inspecting the wiring.

## 3. IPv4 and IPv6 on the same cable

IP provides network addressing and packet delivery. A packet is a bounded unit
of data sent over the network. IPv4 and IPv6 are different versions of IP:

| Property | IPv4 | IPv6 |
|---|---|---|
| Example notation | `192.0.2.10` | `fe80::1234` |
| Address size | 32 bits | 128 bits |
| Use on an Ethernet cable | Supported | Supported; the same interface can use both |
| What success proves | The tested IPv4 path works | The tested IPv6 path works, not an untested IPv4 path |

An IPv6 link-local address begins with `fe80::` and is used on the attached
link, without routing it across the internet. In `fe80::1234%eth0`, `%eth0`
selects the sender's interface because the same link-local range can exist on
several connections. IPv6 address configuration can therefore permit a local
SSH login even when existing IPv4 addresses or return routes are unsuitable.
This is not an IPv4-to-IPv6 translation and does not fix IPv4 robot traffic.
See [IPv6 addressing](https://www.rfc-editor.org/rfc/rfc4291).

For either version, a route selects the outgoing interface or next router.
The recipient also needs a return route. Putting an address from an internal
subnet on an external interface does not physically join the networks. For
example, an i7 may send replies toward its internal interface when the external
client's address appears to be on that internal subnet, although the cable
arrives at USB Ethernet. That produces an asymmetric path.

A physical Ethernet socket and a TCP/UDP port number are different things.
Sockets carry the cable. TCP/UDP port numbers help deliver received IP traffic
to software. Neither an IP address nor a port number identifies a connector's
physical location.

## 4. What DDS does between two programs

Suppose one robot program repeatedly produces a velocity measurement and an
application wants to receive it. The application needs more than a cable:
it needs a common record format, a way to find the producing program, and rules
for receiving updates. DDS, short for **Data Distribution Service**, defines
these facilities for distributed applications.

A message is one structured data record. A *topic* is a named stream of a
particular record type. A *publisher* writes records to it; a *subscriber*
requests records from it. These words describe program behavior, not extra
computers. As an illustrative example, not B2's actual message layout:

```text
Topic: example/velocity
Record fields: forward_mps, lateral_mps, yaw_rate_rps
Producer: writes {0.20, 0.00, 0.05}
Consumer: receives those three numbers and updates its latest state
```

The communication library performs several concrete jobs:

1. Discover other participants and announce which topics/types they provide or
   request. A domain number separates logical groups of participants.
2. Match compatible writers and readers. Their delivery policies must also
   agree, such as whether missing updates may be discarded or retransmitted.
3. Serialize a record: convert its fields into bytes in a shared wire format.
4. Send those bytes through the selected network interface. The receiver
   reconstructs the record and makes it available to the consuming program.

Compatible topic names do not compensate for unreachable addresses. Discovery
may use multicast, which sends to a group of receivers; a router or firewall
can pass ordinary SSH yet block discovery or subsequent data packets. DDS also
advertises addresses for later exchanges, and those addresses must be reachable.
This is why ping, SSH and DDS reception are separate checks.

**Cyclone DDS** is the product name of a library that performs these DDS jobs.
“Cyclone” is not another network layer or another robot computer. A program
loads the library, which opens communication endpoints and moves the messages.
The DDS specification permits different implementations; selecting Cyclone DDS
chooses one of them. See [the Cyclone DDS project](https://github.com/eclipse-cyclonedds/cyclonedds/tree/0.10.2).

## 5. How SDK2 and ROS 2 use that communication

An API defines operations a program may request and their input/output formats.
Unitree SDK2 is a developer library that exposes robot APIs as functions.
Calling its B2 `Damp()` method builds a particular request, sends it using DDS,
and processes the reply. The SDK is not the walking controller running the legs.

ROS 2 is a framework for robot programs. Each running component is called a
node. ROS 2 can use Cyclone DDS to move messages between nodes. The adapter
`rmw_cyclonedds_cpp` connects ROS 2's communication interface to that library.
Unitree's message packages define the fields for robot state and API requests.
A matching ROS 2 program can use these definitions to exchange the required
messages without calling the SDK's convenience functions.

```text
Application -> Unitree SDK2 -> Cyclone DDS -> network -> robot API endpoint
Application -> ROS 2 + Unitree messages -> Cyclone DDS -> network -> same API
```

Unitree documents this [ROS 2/DDS interoperability](https://github.com/unitreerobotics/unitree_ros2).
It does not mean arbitrary ROS 2 versions, message definitions or network
settings are interchangeable. Compatibility has to include record types,
transport configuration and observed request/response behavior.

## 6. Three ways to connect the two networks

A USB connection can be retained. The alternatives are about **how** data crosses
the i7, not whether its USB Ethernet adapter is a valid network device.

| Method | What crosses the i7? | What must be established? |
|---|---|---|
| Ethernet bridge | Ethernet frames forwarded between the two interfaces | Driver/interface support, address placement, multicast and forwarding filters; changes can affect existing networking |
| IP routing | IP packets forwarded between separate subnets | Routes in both directions, filtering and DDS-discovery/advertised-address reachability; enabling forwarding alone is insufficient |
| Application relay | One program receives internal data, then sends a newly defined message to Jetson | The message format, time meaning, connection/reconnection and failure behavior |

For a bridge or router, Jetson could remain the SDK/ROS 2 client if the network
and DDS endpoints become reachable. An application relay instead terminates
one conversation and starts another. For example, an i7 reader receives robot
velocity, packages its value and timestamp, and sends that record to Jetson.
Jetson need not join all internal DDS topics. A command-capable relay would
also need to define accepted commands, authority, expiry and failure handling.
A temporary program started through SSH is not automatically such a relay.

An external Ethernet connector already connected to the internal LAN provides
a fourth physical arrangement: Jetson can join there without using the i7 as
a bridge or router. Identifying that connector is useful, but it is not proof
that the USB alternatives cannot work. No bridge, route change or relay is
selected merely by this explanation.

## 7. Docker and packet filtering

Docker separates application files and processes into containers. A default
container bridge can add another network and address translation. On Linux,
`--network host` instead uses the host's network interfaces directly. It does
not bridge two physical interfaces, add return routes or bypass host filters.
See [Docker host networking](https://docs.docker.com/engine/network/drivers/host/).

A firewall filters packets according to rules. Traffic received by a local
application, traffic sent by that application, and traffic forwarded through
the computer are different cases. Docker can configure forwarding rules that
prevent a host from acting as a router. Thus an i7-local ROS 2 process can work
while a bridge/routing arrangement fails. Existing rule counters and the actual
packet path must be inspected before attributing a failure to Docker.
[Docker's firewall documentation](https://docs.docker.com/engine/network/packet-filtering-firewalls/)
describes this behavior. A blanket firewall-disable command is not a diagnosis.

## Operation away from campus Wi-Fi

The local robot network and Mac's management connection are separate. Losing
Mac access need not remove the Jetson-to-robot Ethernet path. It can still
require stopping a supervised experiment, depending on the agreed operating
policy. A local application needs its own lifetime and data-loss handling;
an SSH window is not that implementation. The [offline procedure](../how-to/offline-operation.md)
explains proposed local access, and [control-loop timing](control-loop.md)
explains why observation/control must continue independently of slow inference.
