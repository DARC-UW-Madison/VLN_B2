# Documentation

[日本語](README.ja.md) · [Project](../README.md)

## Choose by purpose

- Understand a mechanism: read an **explanation**, which defines terms and follows inputs to outputs.
- Carry out a task: use a **procedure**, with prerequisites, execution location, commands, expected results and recovery.
- Look up an implementation or setting: use a **reference**, containing responsibilities, data contracts and configuration requirements.
- Find what was executed and observed: read the [experiment/build records](records/README.md), with dates, revisions, methods, results and limits.
- Check the current boundary and next work: read [status](status.md), not a historical snapshot.

## First reading sequence

1. [Communication between computers](explanations/network-topology.md): SSH, IP, DDS, SDK, ROS 2 and forwarding alternatives.
2. [How the model works](explanations/ticvla-explained.md): images/instructions, semantic features and predicted positions.
3. [From positions to robot control](explanations/control-loop.md): metric scale, state, speed/steering, feedback and slow inference.
4. [Short camera demo](how-to/live-camera-demo.md) on the prepared Jetson; for a new installation, start with [initial setup](how-to/setup-from-scratch.md).

## Learn the mechanisms

| Document |
|---|
| [What a build makes and how the result runs](explanations/build-fundamentals.md) |
| [From predicted positions to continuous robot control](explanations/control-loop.md) |
| [Deployment choices: computers, containers, ROS and sensors](explanations/deployment-design.md) |
| [Terminology: from Python packages to a robot](explanations/glossary.md) |
| [From an Ethernet cable to a robot request](explanations/network-topology.md) |
| [Understanding TIC-VLA: from an image to movement](explanations/ticvla-explained.md) |
| [Remote access: screen, login and transport](explanations/remote-access.md) |

## Perform a task

| Document |
|---|
| [View and capture built-in sensor images](how-to/built-in-sensors.md) |
| [Next B2 visit: collect facts and receive state on Jetson](how-to/next-visit.md) |
| [B2 visit checklist](how-to/field-card.md) |
| [Field visit: Ethernet, onboard computers and independent operation](how-to/field-network.md) |
| [Jetson account, Tailscale SSH, and isolated workspaces](how-to/jetson-bootstrap.md) |
| [Operator tutorial: a short camera and predicted-path demo](how-to/live-camera-demo.md) |
| [Offline operation without a separate access point](how-to/offline-operation.md) |
| [Onsite quick start](how-to/onsite.md) |
| [Remote desktop from Mac](how-to/remote-desktop.md) |
| [Run a ZED image through TIC-VLA and inspect the path](how-to/run-camera-demo.md) |
| [Set up a Jetson for local TIC-VLA inference](how-to/setup-from-scratch.md) |

## Look up contracts and configuration

| Document |
|---|
| [Architecture](reference/architecture.md) |
| [Asynchronous inference: references before workers](reference/asynchronous-runtime.md) |
| [Preparing the external ZED camera](reference/camera-runtime.md) |
| [Local checkpoint conversion](reference/checkpoint-conversion.md) |
| [Deployment information to collect](reference/deployment-intake.md) |
| [Development and experiments](reference/development.md) |
| [Licensing original work and upstream research software](reference/licensing.md) |
| [Model artifacts and verified loading path](reference/model-artifacts.md) |
| [From repository files to robot motion](reference/runtime-flow.md) |
| [System overview and unattended access](reference/system-overview.md) |
| [Isolated Unitree state-receive environment](reference/unitree-runtime.md) |

## Records and collaboration

[Experiment/build record index](records/README.md) · [Contributing](../CONTRIBUTING.md) · [Third-party sources and terms](../THIRD_PARTY.md)

English is the public base language; maintain the Japanese counterpart together. Follow the document-type rules in Contributing.
