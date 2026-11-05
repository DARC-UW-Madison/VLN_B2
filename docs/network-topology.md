# How the computers and connections work

[日本語](network-topology.ja.md) · [Documentation](README.md) · [Connection commands](field-network.md)

This chapter follows one actual experiment: starting a program from the external
Jetson, receiving B2 state on its onboard Intel PC, and sending one damping
request. It explains each component before using it in that sequence. The
[connection procedure](field-network.md) contains commands for a later visit;
[this chapter's results](status.md) are observations from the completed inspection.

## 1. Which computer does what?

The external Jetson and the onboard Intel PC are separate computers. The model
runs on the external Jetson's NVIDIA GPU. It has not been installed or run on
the onboard Intel PC.

Unitree's [B2 specification](https://www.unitree.com/b2/) lists a Core i5 for
platform functions and a Core i7 for user development in the standard
configuration; additional computing options include Orin NX. That describes the
product configuration, not an inspection of every board in this laboratory unit.
We logged into one onboard i7. We have not inspected the platform i5, established
its exact model/OS, or confirmed an additional onboard Jetson.

| Computer | What is established | Role in this project |
|---|---|---|
| Mac | SSH management of the external Jetson works | Editing, starting experiments and viewing results |
| External Jetson | AGX Orin 64 GB class; TIC-VLA loads and predicts using its GPU | Camera acquisition and model inference; future path tracking |
| Onboard development PC | Core i7-1265U; existing Ubuntu and ROS 2 work | Receives internal state/video; ran our temporary diagnostic |
| Platform computer | Core i5 is listed in the official standard configuration; this unit's hardware has not been inspected | Preserve the manufacturer's existing robot functions |
| Additional onboard Jetson | Not confirmed | Do not assume one is installed or required |

The i7 is a general development computer supplied for user applications. Sensor
processing, localization, recording and communication are possible uses of such
a computer; we have not established the original purpose of every installed
program. None of these tasks automatically requires running TIC-VLA. A fast
NVIDIA GPU is useful for our large model, but a computer does not need that GPU
to handle messages or run a controller. The implementation of B2's existing
walking controller, including any inference it performs, was not inspected.

The measured i7 details are:

| Item | Result |
|---|---|
| CPU | Intel Core i7-1265U, x86_64; 12 logical CPUs visible to Linux |
| Memory | About 15.22 GiB visible to Linux |
| Storage | NVMe, 512,110,190,592 bytes, approximately 512 GB |
| Graphics | Intel graphics listed by PCI inspection; no NVIDIA GPU listed on this PC |
| OS / kernel | Ubuntu 20.04.6; Linux 5.15.76-rt53 |
| Networking | An internal robot-facing Ethernet interface, USB Ethernet interfaces and Wi-Fi |
| Other software | Docker was running; its containers and complete firewall rules were not inventoried |

## 2. What did the cable connect?

An Ethernet adapter converts USB access into an Ethernet network interface for
its host computer. Here the USB end of the Anker adapter was plugged into B2,
so **the adapter added a network interface to the onboard i7**.

```text
External Jetson Ethernet
          |
      LAN cable
          |
Anker Ethernet socket
          |
       USB-C
          |
Onboard i7
  A: USB Ethernet interface <---- external Jetson
  B: internal Ethernet interface ----> B2 internal network
```

A network interface is a connection a computer can send and receive through.
`eth0` and similar Linux names identify interfaces; they are not IP addresses.
A and B belong to the same PC but are separate connections. We found no network
bridge joining them. A bridge would forward Ethernet traffic between interfaces
so that other devices could communicate through them.

The current cable **already permits communication with the onboard PC**: we
successfully logged into the i7. Reaching a robot service beyond the i7 is a
second question. A PC with two network interfaces does not automatically
forward traffic between them.

There is no established requirement to expose an RJ45 socket directly on the
Intel board. An external connector that actually reaches the internal Ethernet
network could also work. Unitree lists Ethernet interfaces, but we have not
matched an accessible connector, adapter or pinout on this unit to that network.
An unfamiliar multipin connector cannot be identified from its shape alone.
Do not buy a guessed adapter or substitute a generic USB hub for an unverified
Ethernet breakout. At the next visit, match connector labels and the unit's
manual/accessory list with the lab. Follow the manufacturer's handling procedure;
do not unplug an unknown powered connector as an identification test.

## 3. IPv4, IPv6 and the address on each interface

**IPv4 is the addressing system that uses four numbers separated by dots.**
An address such as `192.168.10.20` is an IPv4 address, not an alternative to IPv4.
The `192.168.0.0` through `192.168.255.255` range is reserved for private networks;
not every address starting with `192` is private. See [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918).

An IP address identifies an interface's network endpoint. A subnet prefix tells
the computer which destinations it should treat as directly attached. For
example, `/24` groups addresses by their first three numbers. A route tells the
computer which interface or next router to use for a destination. A cable gives
a physical path, but the two computers still need compatible addresses and
working return routes.

For illustration, suppose a PC's internal interface is `192.0.2.20/24`, its USB
interface is `198.51.100.20/24`, and an external computer is attached to USB.
Assigning `192.0.2.10/24` to that external computer does not move the USB cable
onto the internal network. The PC may send its reply toward its internal
interface because the destination looks directly attached there. These are
example addresses, not this robot's configuration.

That kind of return-path mismatch was observed on B2: the i7 selected its
internal interface when replying to the external Jetson's configured IPv4,
although the cable reached USB Ethernet. The USB side also had overlapping
IPv4 configurations. A direct IPv4 test failed. This is evidence of an address/
route problem; it does not exclude additional filtering or DDS problems.

**IPv6** is another IP addressing system, written with colons. Both systems
can use the same cable. An IPv6 *link-local* address beginning `fe80::` can be
used between directly attached devices without first repairing their IPv4
configuration. The `%INTERFACE` suffix selects the sender's outgoing interface.
We reached the i7 that way using SSH. This did not involve internet routing,
Tailscale on B2, or translating the IPv4 robot network into IPv6.

SSH means Secure Shell: it authenticates a login and lets us execute a program
on another computer. The program runs on the destination computer. Therefore,
SSH into the i7 lets a program use **the i7's own internal Ethernet**, even if
the external Jetson cannot directly reach that internal network.

Do not confuse a physical socket with a TCP/UDP *port*. A software port number
selects a receiving application within IP networking; it does not specify which
connector to plug into. Seeing a service address or software port number does
not identify a physical socket.

## 4. ROS 2, DDS, Cyclone DDS and the SDK

Start with the task: a program needs to receive robot state and request a robot
operation. It must agree with the receiver about both the data format and how
the data is transported.

**DDS (Data Distribution Service)** provides communication between programs.
A message is a structured data record.
For state data, a producer publishes messages and a consumer subscribes to a
named stream, called a *topic*. Participants discover matching peers and exchange
data. The topic name and message structure must match. A DDS domain is a logical
communication group selected by a number; we observed domain 0 on the internal
network. Using the same domain number alone does not establish connectivity.

**Cyclone DDS** is a particular software implementation of DDS. It handles the
communication; it is not a model, robot driver or additional computer.

**ROS 2** is a framework for building robot software. A ROS 2 *node* is a running
software component. Nodes can publish and subscribe to topics. In the environment
we used, ROS 2 calls Cyclone DDS through its middleware adapter, named
`rmw_cyclonedds_cpp`. A message workspace is a directory containing the built manufacturer-specific
message packages and their environment setup file.
Unitree message definitions describe fields such as robot
velocity and API-request headers. Installing ROS 2 alone does not supply every
manufacturer's message definitions.

**Unitree SDK2** is Unitree's Software Development Kit, a programming library.
An API is the defined set of operations and request/response formats that a
program can use. A robot service here means the running program that accepts
those requests; this does not imply the ROS 2 `srv` service mechanism. The tested
Unitree API uses request and response messages on topics. Its B2 client offers methods
such as `Damp()` and `Move(vx, vy, yaw_rate)`. The SDK builds the required request
and uses DDS to communicate. For example, the pinned [B2 client implementation](https://github.com/unitreerobotics/unitree_sdk2_python/blob/814556d15970dd2ecf1c9984e845ca02ab07e206/unitree_sdk2py/b2/sport/sport_client.py)
implements `Damp()` by sending the corresponding API request with empty parameters.

There are two ways for a compatible program to reach the same published robot
interface:

```text
Application -> Unitree SDK2 -> Cyclone DDS -> robot service
Application -> ROS 2 + Unitree message definitions -> Cyclone DDS -> robot service
```

These are alternative application paths, not a requirement to install the SDK
under ROS 2 or to run ROS 2 under the SDK. Unitree's [ROS 2 documentation](https://github.com/unitreerobotics/unitree_ros2)
explicitly supports compatible ROS 2 messages without wrapping the SDK.
For our i7 experiment we used the **second path**. We did not establish that a
complete standalone SDK distribution was installed on the i7. The external
Jetson has a separate prepared SDK state-receive container; the SDK remains a
candidate for direct communication if a working network path is established.

## 5. Versions: what is known and what works?

| Component | Confirmed version or status | Evidence and remaining gap |
|---|---|---|
| i7 ROS 2 | Foxy, with existing Unitree message workspace | State reception and the single API request ran successfully |
| i7 Python used for ROS | System Python 3.8 | Used `/usr/bin/python3`; the separate conda Python 3.11 was not substituted |
| i7 DDS middleware | Cyclone DDS via `rmw_cyclonedds_cpp` | Runtime communication passed; exact loaded library version/source revision not recorded |
| i7 standalone Unitree SDK | Installation and version not established | Not required by the ROS-message diagnostic; inventory remains to be done |
| B2 sport-service API | `1.0.0.1` | Returned by a version query; not the robot firmware or SDK package version |
| External SDK state image | Pinned SDK source revision `814556d…`, declared SDK version 1.0.1; Cyclone DDS 0.10.2 | Source/native-library and synthetic state checks passed; actual direct state probe received zero messages |
| External model image | Python 3.11.18, PyTorch 2.2.2, Transformers 4.44.2 | GPU model load and real-camera prediction passed independently |

Unitree lists Ubuntu 20.04/Foxy as a tested pairing in its ROS 2 documentation.
The successful messages are stronger evidence for this narrow communication
check than assuming all installed versions match a recommended list. They do
not validate every API or sustained operation. Python versions need not be
identical on separate computers exchanging messages; each process must use
bindings compatible with its own interpreter. Preserve the working i7 setup
while collecting the missing versions, rather than upgrading it to match the
model container.

## 6. Exactly what did we execute?

The completed sequence was:

1. From the external Jetson, SSH into the i7 over the USB Ethernet link using
   its verified IPv6 link-local address and pinned SSH host key.
2. In a temporary shell on the i7, load `/opt/ros/foxy/setup.bash` and the existing
   Unitree message workspace's `install/setup.bash`. Loading these files sets
   library/module paths for that shell; it does not install software.
3. Select the i7's internal Ethernet and observed domain 0 for Cyclone DDS.
   Run system Python 3.8 with `rclpy`, ROS 2's Python library, and the existing
   Unitree message types.
4. Subscribe to the named state streams. A 12-second trial received 5,994 normal
   and 240 low-frequency sport-state messages. Later passive subscriptions also
   received IMU/joint data and decoded front/back camera images.
5. Query the sport-service API version. Later, at the operator's request and
   after checking fresh state was already damping, send **one** API-1001 Damp
   request using the ROS request/response messages. Match its response to that
   request; it returned status 0. No stand-up or translation was requested.
6. Observe mode 7/error 0 before and after, then exit the temporary program.
   The operator reported no change and that the robot remained damped.

This created the following **two separate conversations**:

```text
External Jetson <-- SSH --> temporary program ON the i7
                                  |
                       ROS 2 / Cyclone DDS
                                  |
                         B2 internal service
```

The external program did not send a motor command into the i7 over SSH for a
preinstalled relay to automatically forward. It used SSH to start a temporary
program **on the i7**, and that program generated the request locally. There is
no persistent relay installed by this project.

From the i7 to the visible B2 service, the inspected transport was Ethernet/IP
and DDS. The service endpoint responded, but its physical host and the path
from that service to motor-control boards were not mapped. We did not access joint drivers or establish how the internal control boards
connect to the motors. Those details cannot be inferred from an API response.

The API round trip measured on the i7 was about 1.34 ms. It excludes SSH startup
and Jetson-to-i7 time and does not measure a physical posture transition. The
already-damped request is not a stand-to-damp test.

## 7. Docker and the earlier firewall problem

Docker packages dependencies into containers: isolated process/filesystem
environments sharing the Linux host kernel. It is not a robot communication
protocol. Its network configuration can nevertheless affect communication.

A firewall filters network packets. Linux's `FORWARD` rules apply to packets
passing through a computer between connections; local receive/send traffic is
handled separately. The earlier Go2-W experiment recorded a Wi-Fi/Ethernet
bridge whose forwarded traffic was blocked by Docker-related `FORWARD DROP`
rules. That is a relevant previous failure, not proof of the same cause here.

The successful B2 diagnostic ran directly on the i7's existing ROS 2 environment,
not in our new Docker container. SSH terminated on the i7; its program then
originated new DDS traffic through the internal interface. That sequence did
not require routing the external Jetson's DDS packets through the i7.

For the external SDK container, the tested recipe uses Linux `--network host`,
which shares the Jetson's network interfaces rather than creating a separate
container bridge/address-translation path. Address translation (NAT) rewrites
network addresses while forwarding traffic. It does **not** join the i7's two interfaces, bypass
host firewalls or repair return routes. See Docker's [host-network explanation](https://docs.docker.com/engine/network/drivers/host/)
and [firewall behavior](https://docs.docker.com/engine/network/packet-filtering-firewalls/).

Docker was running on the i7. We have not audited all of its forwarding rules
or compared the external SDK subscriber on bare host and container under an
otherwise identical working IP path. Therefore, we have not ruled out all
Docker/firewall issues. The established result is narrower: the i7-local path
worked, and the external direct path did not. No firewall was disabled or
forwarding rule copied from Go2-W to make this test pass.

## 8. What should happen next?

First collect the missing i7 software/library versions and inspect firewall
rules without changing them. At the next powered visit, also identify connector
labels and the actual internal-network access point. Then select between:

| Approach | How it works | Work still needed |
|---|---|---|
| Direct external SDK | Jetson reaches the robot service through an identified internal-network connection | Confirm the connector/path, IPv4 return route, host/container reception and DDS settings |
| Application relay on i7 | A small i7 program reads internal state and sends defined data to Jetson; later it could accept tightly limited commands | Define and test the protocol, timestamps, link-loss behavior, ownership and command expiry |

An application relay is different from making the i7 a general network bridge:
it receives application data and produces a new, deliberately defined message.
The current USB link could support that approach without exposing all internal
DDS traffic. It is a proposal, not an installed service.

Start with continuous **state reception only**, then combine received state
with the working external ZED camera and evaluate TIC-VLA predictions without
sending commands. Establish units, axes and time alignment before using state
values as model inputs. Physical posture, stopping and translation tests follow
separately at a suitable site. B2 can stay off while software is developed
against saved/synthetic data. See [current status](status.md), [sensor capture](built-in-sensors.md)
and [field commands](field-network.md).

## Operation away from campus Wi-Fi

Mac management and the robot's local data/control traffic are different links.
The intended model/control application runs on Jetson, so an open Mac SSH window
is not a required part of every future command. The application lifecycle and
response to lost operator access still need implementation and testing.
Tailscale needs an underlying network; it cannot create Wi-Fi coverage.
The [offline-operation guide](offline-operation.md) explains the proposed local
hotspot, direct SSH and link-loss checks. The [account/setup guide](jetson-bootstrap.md)
and [remote desktop guide](remote-desktop.md) cover management access.
