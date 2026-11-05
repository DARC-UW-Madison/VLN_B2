# Documentation

[日本語](README.ja.md) · [Project](../README.md)

## Choose by purpose

- Understand a mechanism: read an **explanation**, which defines terms and follows inputs to outputs.
- Carry out a task: use a **procedure**, with prerequisites, execution location, commands, expected results and recovery.
- Look up an implementation or setting: use a **reference**, containing responsibilities, data contracts and configuration requirements.
- Find what was executed and observed: read the [experiment/build records](records/README.md), with dates, revisions, methods, results and limits.
- Check the current boundary and next work: read [status](status.md), not a historical snapshot.

## First reading sequence

1. [Inside the model](explanations/ticvla-explained.md): follow pixels and instruction tokens through language generation, numerical semantic features and 30 predicted positions.
2. [How it learns](explanations/ticvla-training.md): demonstrations, labels, language supervision, delayed imitation and reinforcement learning; distinguish training from deployment.
3. [From a path to B2 movement](explanations/control-loop.md): calculate speed/turn from a point, encode a request, trace its communication, return measurements, and examine Go2-to-B2 differences.
4. [Communication between computers](explanations/network-topology.md): further detail on SSH, IPv4/IPv6, DDS and forwarding alternatives.
5. [Short camera demo](how-to/live-camera-demo.md) on the prepared Jetson; for a new installation, start with [initial setup](how-to/setup-from-scratch.md).

The first three chapters develop mechanisms rather than provide launch commands.
They use worked examples and identify which statements describe the paper,
the pinned release, our implementation or a proposed design. Read them in sequence
before interpreting a displayed path as a robot command.

## Learn the mechanisms

| Document |
|---|
| [What a build makes and how the result runs](explanations/build-fundamentals.md) |
| [From a predicted path to B2 movement](explanations/control-loop.md) |
| [Deployment choices: computers, containers, ROS and sensors](explanations/deployment-design.md) |
| [Terminology: from Python packages to a robot](explanations/glossary.md) |
| [From an Ethernet cable to a robot request](explanations/network-topology.md) |
| [How TIC-VLA turns images and instructions into a path](explanations/ticvla-explained.md) |
| [How TIC-VLA learns navigation](explanations/ticvla-training.md) |
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
