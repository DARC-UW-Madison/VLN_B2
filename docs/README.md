# Documentation

[日本語](README.ja.md) · [Project](../README.md)

This manual explains the research goal, the software/hardware mechanisms, what
has actually been done, and what to do next. It is organized by learning and
operating task rather than by chat history. Commands marked as proposals or
templates are not records of execution. Keep private measurements in approved
local storage and promote reviewed conclusions into the relevant paired guide.

## Suggested reading order

1. Start with [deployment choices](deployment-design.md) for the role of each
   computer and why Docker/ROS/sensor placement are separate decisions.
2. Use [terminology](glossary.md) for unfamiliar words, then read
   [TIC-VLA explained](ticvla-explained.md) for the model and latency mechanism.
3. Read [runtime flow](runtime-flow.md) and [build fundamentals](build-fundamentals.md)
   to connect files, dependencies, GPU execution and eventual robot requests.
4. Check [the measured baseline](target-baseline.md), [system overview](system-overview.md)
   and [project status](status.md) before treating any design as implemented.
5. For the visit, open [the field card](field-card.md), then follow the detailed
   [Ethernet procedure](field-network.md). Motion remains a later validated stage.
6. Before collaboration/publication, read [development](development.md),
   [Contributing](../CONTRIBUTING.md) and [licensing](licensing.md).

## Concepts and design

| Guide | Questions answered |
|---|---|
| [Deployment choices](deployment-design.md) | What does each computer do? Does Mac need source, weights or Docker? Why containers? Where can ROS and sensors run? Can containers communicate? |
| [Terminology](glossary.md) | What are PyTorch, HF, wheel, pyenv, venv, CUDA, checkpoint, image, SDK, DDS and watchdog? |
| [Understanding TIC-VLA](ticvla-explained.md) | How do language/image reasoning, action prediction, training and delay compensation relate? |
| [From files to motion](runtime-flow.md) | How do this repository, separate upstream/model inputs, container processes and communications connect? |
| [Build fundamentals](build-fundamentals.md) | What are compilation, linking, wheels, CUDA compilation, image layers and rebuilds? |
| [Architecture](architecture.md) | What are the proposed timing, coordinate frames, plan tracking and control boundaries? |
| [Computers and network](network-topology.md) | How do Ethernet/IP, SDK2/DDS, ROS 2 and management links differ? What remains unknown inside B2? |
| [Offline operation without an AP](offline-operation.md) | Why is Mac optional? How could Jetson provide a local hotspot? What do the B2 remote and link-loss policies need to establish? |

## Verified state and installation

| Guide | Questions answered |
|---|---|
| [Project status](status.md) | What is complete, what is blocked/unverified, and what is the next milestone? |
| [Measured Jetson baseline](target-baseline.md) | Which CPU/GPU, memory, storage, OS, SDK and network facts were inspected? |
| [System overview and unattended boot](system-overview.md) | Which paths/settings changed? What is isolated? How do boot networking, credentials, sharing and return work? |
| [Jetson bootstrap](jetson-bootstrap.md) | How are accounts, SSH/Tailscale, interpreters and dependency boundaries prepared? |
| [Jetson runtime setup](jetson-runtime.md) | How were SSD/Docker storage, native CUDA, Python and runtime stages built and recovered? |
| [Runtime compatibility](runtime-compatibility.md) | Which candidate versions and model-free checks passed? Why is checkpoint loading still blocked? |
| [Remote desktop from Mac](remote-desktop.md) | How do Windows App/RDP/xrdp sessions differ from VNC? What must work before remote GUI can replace routine HDMI? |

Historical inspection dates are not automatic claims about the current device.
A successful past SSH or GPU check is evidence for that check, not permanent
reachability or an actual TIC-VLA/robot performance result.

## Field work and experiment procedure

| Guide | Questions answered |
|---|---|
| [First-visit card](field-card.md) | In what order should the operator proceed at the robot? |
| [Ethernet/onboard procedure](field-network.md) | How should cable endpoints, addresses, routes, DDS and internal service ownership be checked? |
| [Onsite preparation](onsite.md) | How are camera/state observations, paired recordings and optional offline inference invoked and interpreted? |
| [Deployment information](deployment-intake.md) | Which facts must come from the lab/unit instead of guessed defaults? |
| [Development and experiment guide](development.md) | How are tools run, validations staged, failures recorded and experiments made reproducible? |

Use these source templates only after copying to ignored local storage:
[blank visit notes](../examples/onsite-notes.json),
[commissioning example](../examples/commissioning.json) and
[synthetic replay input](../examples/replay.json).
Their values do not authorize physical operation or establish B2 limits.

## Collaboration, licensing and source navigation

| Guide or source | Purpose |
|---|---|
| [Contributing](../CONTRIBUTING.md) | Git branches/commits/review, bilingual docs, AI review and bounded parallel work |
| [Licensing explained](licensing.md) | Why original MIT code can coexist with separately restricted upstream requirements; copies/derivatives, future research and artifact release |
| [Third-party inventory](../THIRD_PARTY.md) | Exact reviewed sources, conditions, provenance and outstanding permission questions |
| [Original-work license](../LICENSE) | Actual MIT permission text for this project's original material |
| [Python package](../src/b2_tic_vla/) | Independent adapters, CLI, inference validation, replay and candidate tracking |
| [Tools](../tools/) | Target inventory and operator-driven Wi-Fi helper |
| [Deployment recipes](../deploy/) | Candidate environment definitions and model-free checks |
| [Tests](../tests/) | Synthetic/mocked behavior checks; not physical robot validation |

English is the public base language; Japanese companions use `.ja.md` and `，`/`．`.
Update both versions together, including prerequisites, commands, uncertainty and
limitations. Add new guides to this index rather than expanding the project
README into a second directory. Keep each mechanism's detailed explanation in
its responsible guide and link related topics; do not copy a growing chat log.
