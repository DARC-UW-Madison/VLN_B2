# Project status

[日本語](status.ja.md) · [Documentation](README.md)

## Current stage

As of **2026-11-04**, model/camera observation and an onboard B2 diagnostic work
as separate experiments. They are not a connected navigation controller. B2
was shut down by the operator; off-robot preparation has not changed its settings.

| Capability | Current boundary | Evidence |
|---|---|---|
| External ZED and TIC-VLA | Camera/path display works with explicitly assumed zero motion | [Demo record](records/camera-demo-checks.md) |
| Internal state/video | A temporary i7 ROS 2 program received them | [Connection](records/b2-connection-2026-11-03.md), [sensors](records/built-in-sensors.md) |
| One Damp request | Acknowledged while already damped; operator observed no change | [Connection record](records/b2-connection-2026-11-03.md) |
| External SDK/ROS 2 robot path | Direct reception has not succeeded over the USB attachment | [Connection record](records/b2-connection-2026-11-03.md) |
| Actual state as model input | Not integrated; units, frames and timestamps need validation | [State contract](reference/asynchronous-runtime.md) |
| Repeated action prediction | Shadow experiment completed actions but had availability gaps | [Asynchronous record](records/async-shadow.md) |
| Path tracking and commands | Offline candidate tracker exists; no commissioned movement sender | [Architecture](reference/architecture.md) |
| Physical feedback/stopping/navigation | Not validated | [Development procedure](reference/development.md) |

The pre-visit review repeated real-camera prediction and added field diagnostics.
All 201 ordinary tests passed on Mac; new-tool target checks follow synchronization.
Methods/results are in [the readiness record](records/previsit-readiness-2026-11-04.md).
Ordinary tests do not measure robot execution.
The deployed source revision is recorded privately in `local/source-revision.txt`.
Source is shared in the public lab repository
[DARC-UW-Madison/VLN_B2](https://github.com/DARC-UW-Madison/VLN_B2).
Check published `main`, the working branch and the Jetson deployment revision separately. Models, images, raw logs and real network
identifiers stay outside Git.

## Next work

1. At the next powered visit, inspect the i7's missing SDK/library versions,
   routes and firewall rules without changing them. Identify external connector
   wiring. Compare bridging/routing, an application relay and a separate
   internal-LAN Ethernet connection using the same explicit acceptance test.
2. Establish continuous state delivery to Jetson; verify units, axes, timestamps
   and alignment with camera images. Receiving values is not enough to declare
   them valid model inputs.
3. Connect that input path to command-free predictions. Measure slow semantic
   updates, current action updates, startup/refresh gaps and failures.
4. Complete and test tracking, command expiry and local override separately at
   a suitable site before any model-driven movement.

[Communication mechanisms](explanations/network-topology.md) explains the
connection choices; [the control loop](explanations/control-loop.md) explains
state, metric scale, feedback and inference timing. Use [field commands](how-to/field-network.md)
for operations and [records](records/README.md) for completed work.

Use [the executable visit procedure](how-to/next-visit.md) for the next session.
