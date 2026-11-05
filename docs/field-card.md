# B2 connection visit: field card

[日本語](field-card.ja.md) · [Detailed Ethernet procedure](field-network.md) · [Current status](status.md)

The first USB attachment reached an onboard Intel i7 development PC and
received state there. Direct external-Jetson DDS is still pending; see the
[measured USB/network boundary](field-network.md). A supported native-network
breakout was not found among the available accessories. Next identify that
connection or review an explicit onboard relay before changing B2 settings.
Repository tools send **no actuator requests**. A separately guarded one-shot
Damp check subsequently acknowledged the already-damped state; no standing or
translation was attempted. See [the recorded result](status.md). External-camera capture and
model prediction already passed; a successful cable connection is not yet a
model-driven walking system.

## Before leaving

- Bring the external Jetson with its current power supply, Mac and their normal
  chargers, and an Ethernet cable/adapter appropriate to the lab's **actual B2
  user-network port**. Confirm the connector/breakout with the lab; do not assume
  every expansion connector is an ordinary RJ45 port. Keep the Jetson on its own
  supply for this stationary network visit; robot-mounted power is separate work.
- Have the charged, paired B2 controller and the lab's normal operating/stop
  procedure available. Identify who owns the current robot control session.
- Have the lab's known working robot subnet/service address and approved onboard
  access available if documented. They are unit-specific facts, not Go2-W or
  reseller defaults. If unavailable, inspect lab configuration onsite before
  assigning an address or initiating a state subscription.
- Keep local recovery available if Wi-Fi fails. Mac uses existing Tailscale and
  direct RDP when needed; no Mac tunnel or new background service is required.
  [Windows App settings](remote-desktop.md#connect-directly-from-windows-app).
- Reference the manufacturer's [B2 manual/controller page](https://www.unitree.com/app/b2/)
  and [B2 development portal](https://support.unitree.com/home/en/B2_developer).
  Use the lab's matching manual; do not apply B2-W instructions to this B2.
  Official B2 user/controller pages were also cached privately on Jetson under
  `local/reference-manuals/unitree-b2-01`: open each document's `index.html` for
  offline reading. The cache contains 23/14 image pages and a source/SHA256
  manifest, about 29.35 MB total; it is excluded from Git and is not redistributed.

## Software already staged

| Item | Prepared evidence | Field requirement |
|---|---|---|
| Source | Hash-synchronized Jetson archive at `~/Developer/Projects/Robotics/b2/VLN_B2` | Open a terminal in its root |
| Camera | Private binding/calibration; USB 5 Gbps; 275 saved JPEGs in the bounded trial | Check USB/power and final mounted view if used |
| Model | Local fixed base/upstream and converted checkpoint; real-image prediction passed | No new download, Mac Docker or model execution required |
| GPU runtime | Existing `vln-b2-runtime:jp5` image checked | Use reviewed camera/model mounts, not host venv |
| State runtime | Existing `vln-b2-unitree:jp5`; fresh network-isolated verifier passed | Set the confirmed robot-facing interface and DDS domain |
| Direct RDP | Tailnet-only listener and Mac TCP/RDP/TLS check passed | Operator confirmed direct desktop use; clipboard remains unresolved |

The field readiness check revalidated the converted checkpoint SHA256 and the
presence of the pinned base snapshot, upstream package and camera binding.
Private results are under `local/field-ready-01`. That preparation passed 162
ordinary tests on Mac/Jetson; subsequent demo work passed 177. Those facts do not
establish real B2 firmware/topic/frame compatibility.

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

## At the robot

1. Confirm the correct B2, normal operator control/stop procedure, intended user
   Ethernet port and cable endpoints. Do not change onboard services or firmware.
2. Open [Ethernet steps 1–2](field-network.md#1-before-connecting-the-cable).
   Save external interfaces/routes **before** attachment and inspect existing
   profiles. The external interface was `eth0`; carrier was absent during the
   initial desk survey and 1 Gbps during the USB attachment. Verify it again.
   Keep eduroam/Tailscale management and do not bridge to campus.
3. Use the confirmed subnet and an unused external-client IP. Check carrier,
   address and route to the known robot service. If DHCP/VLAN/bridge topology is
   in use, follow that lab setup rather than the static-IP template.
   With the measured USB-only path, this external-service step is still incomplete;
   use the native connection or review an explicit relay. The separate onboard
   diagnostic does not satisfy the external container's acceptance check.
4. Run the [prepared state-container command](unitree-runtime.md#prepared-receive-only-command)
   with the verified interface/domain. Read actual received/valid counts and
   samples; exit code zero or ping alone is insufficient. No model or motion
   client is needed for this check.
5. Inspect accessible onboard computers using authorized lab access. Record
   actual hosts, services, sensor exporters, protocol/topic/domain and ownership.
   The motion controller and accessible user-development PC must not be treated as one host
   merely because one Ethernet port reaches both.
6. Record units, axes, timestamp meaning, world/body velocity convention and the
   camera/body mount. Built-in streams and Mid-360 wiring are separate from the
   working external USB camera. Keep frames/timing unverified until established.
7. Save the conclusion and next step. Later work connects received state to
   model inputs, addresses cache-refresh gaps, implements guarded sending and
   verifies command loss/override/stopping before model-driven movement.

Use a new numbered private output directory for every attempt. Copy
[blank visit notes](../examples/onsite-notes.json) into ignored `local/`; keep
actual IPs, accounts, raw reports and camera images out of Git. An unrecognized
network or zero DDS samples is a diagnosis task, not a reason to run a movement
example. The full sequence and recovery commands are in the Ethernet guide.
