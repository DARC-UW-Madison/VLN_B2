# B2 connection and request-response inspection

[日本語](b2-connection-2026-11-03.ja.md) · [Records](README.md)

**Scope: the 2026-11-03 connection inspection and Damp/sensor findings recorded through 2026-11-04.**
This is a record of execution locations, results and open questions, not an operating procedure.

## Hardware identification

The inspected development PC was Intel i7. Unitree lists a platform i5 and a user-development i7 in its [standard B2 configuration](https://www.unitree.com/b2/); the platform host and any additional Jetson were not inspected on this unit.

| Item | Result |
|---|---|
| CPU | Intel Core i7-1265U, x86_64; 12 logical CPUs visible to Linux |
| Memory | About 15.22 GiB visible to Linux |
| Storage | NVMe, 512,110,190,592 bytes, approximately 512 GB |
| Graphics | Intel graphics listed by PCI inspection; no NVIDIA GPU listed on this PC |
| OS / kernel | Ubuntu 20.04.6; Linux 5.15.76-rt53 |
| Networking | An internal robot-facing Ethernet interface, USB Ethernet interfaces and Wi-Fi |
| Other software | Docker was running; its containers and complete firewall rules were not inventoried |


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


## First-motion boundary

The operator requested stand, a small forward/back movement and lie down, but
reported insufficient room for a fall or a larger-than-intended movement.
**No standing or translation trial was performed.** A later single Damp
request was sent only after confirming the robot was already damped. The operator
reported no change or unexpected motion; this did not test a posture transition. The current site supports observation and
communication diagnosis, not commissioning locomotion. A short distance request
does not bound leg sweep, body movement, tracking error or a fall.

The currently linked official [B2 remote manual](https://marketing.unitree.com/article/en/B2/Remote_Control.html),
page 8, lists **hold L2 + click B** for damping and **hold L2 + click A** for
standing-lock/lying transition. Do not certify L1+A from another manual/version
for this unit. Match the actual remote/firmware and the lab's procedure before
movement. Damping can remove support
and lower/drop the body. It is different from holding a stable standing pose.

For a later suitable site, proceed through separate observed stages:

1. Establish a reliable state and read-only service response over the selected
   external path. A native i7 API-version response already passed; direct external
   DDS currently returns zero samples. An SSH-triggered temporary onboard client was used only for the
   guarded single Damp request and separate passive sensor checks. A persistent
   relay/control deployment still needs review and validation.
2. Confirm local stopping, controller priority and command-loss behavior under
   the lab's procedure, with appropriate clearance and an onsite operator.
3. Review a posture-only trial first; observe stable standing and controlled
   return to lying before considering translation. Do not queue a whole sequence.
4. Define displacement, speed, duration, independent expiry and abort criteria
   for a later forward/back trial. SDK `Move` takes velocities, not a number of
   footsteps; speed times duration is only nominal travel, not a guaranteed bound.
5. Keep this a model-free SDK test. TIC-VLA prediction quality is a separate
   experiment after communication, execution and physical stopping are validated.

The [B2 SDK](https://github.com/unitreerobotics/unitree_sdk2_python/blob/814556d15970dd2ecf1c9984e845ca02ab07e206/unitree_sdk2py/b2/sport/sport_client.py)
has separate StopMove, StandDown and Damp requests; names/return codes alone do
not validate physical behavior. This repository has no commissioned motion
sender or automatic posture/movement sequence. Do not use a generic example's
default movement speed as a small-space test.
