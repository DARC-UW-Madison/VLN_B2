# B2 TIC-VLA

[日本語](README.ja.md)

Research workspace for evaluating TIC-VLA navigation on the Unitree B2.
The goal is to connect language-conditioned navigation to the robot's existing
walking controller and measure the effect of delayed model inference.

**Status:** preparation tools are implemented for target inspection, synthetic
replay, camera capture, state subscription, observation recording, and an optional
offline inference check. They send no motor commands. Real ZED/B2 operation and
GPU inference have not been validated. External-host inventory, management SSH,
and a CUDA driver/device query are verified in [the baseline](docs/target-baseline.md). This is an independent project, not an
official release from the paper's authors or the robot manufacturer.

## Read first

| Document | What it explains |
| --- | --- |
| [System overview](docs/system-overview.md) | Actual specifications, storage, isolation, GUI, unattended access and computer roles |
| [From files to robot motion](docs/runtime-flow.md) | Source sharing, upstream/weights, Docker execution and communication by layer |
| [Build fundamentals](docs/build-fundamentals.md) | Source, compiler/linker, native Python packages, CUDA, image construction and what needs rebuilding |
| [Field Ethernet procedure](docs/field-network.md) | Cable/IP/route/DDS sequence, onboard inventory, sensor paths and mobile operation |
| [Remote desktop](docs/remote-desktop.md) | Existing Vino state, SSH-tunneled screen sharing and headless/login acceptance |
| [Measured Jetson baseline](docs/target-baseline.md) | Verified host, GPU-driver, storage and network facts; runtime constraints |
| [Jetson runtime setup](docs/jetson-runtime.md) | Host interpreter/venv, native CUDA check, storage and staged container builds |
| [Runtime compatibility](docs/runtime-compatibility.md) | Candidate inference stack, model-free checks, and unresolved checkpoint-loading constraints |
| [Jetson bootstrap](docs/jetson-bootstrap.md) | New login, Tailscale SSH, dependency isolation, and later CLI boot |
| [Computers and network](docs/network-topology.md) | Host roles, SDK/ROS 2 boundaries, and the first external-Jetson survey |
| [First-visit card](docs/field-card.md) | Visit agenda, observation probes and the facts to record |
| [Onsite preparation](docs/onsite.md) | Commands to inspect the target, capture observations, and check local inference |
| [Understanding TIC-VLA](docs/ticvla-explained.md) | How reasoning, action prediction, latency, training, and robot control fit together |
| [Deployment information](docs/deployment-intake.md) | What to collect from the robot and lab before choosing an implementation |
| [Development guide](docs/development.md) | How to start, validate each stage, and record reproducible experiments |
| [Architecture](docs/architecture.md) | The proposed data flow, timing, coordinate frames, and control boundaries |
| [Project status](docs/status.md) | Completed work, unresolved questions, and the next deliverable |
| [Contributing](CONTRIBUTING.md) | Git, documentation, review, and AI-assisted collaboration |
| [Third-party materials](THIRD_PARTY.md) | Sources, provenance, and conditions to resolve before integration |

Each document has a Japanese counterpart. Update both languages together.

## Current scope

Start with recorded observations, then observe live predictions without sending
movement commands. Controlled B2 trials follow only after the interface and stop
behavior have been verified. Training a new walking policy is outside this scope.

The available setup is B2, Jetson AGX Orin, ZED 2i and Livox Mid-360.
Docker use and lab GitHub hosting are permitted. See [project status](docs/status.md)
for confirmed facts and the next inspection. External-host software inventory is
verified, and model-free GPU/import checks pass. Actual model/sensor integration,
connections, frames and timing remain unverified. No asynchronous robot-control
loop or motor command sender is implemented.

## Try the preparation tools

From the repository root, Python 3.10 or later can run the CLI and local tests
without installing this package:

```sh
PYTHONPATH=src python3 -m b2_tic_vla --help
PYTHONPATH=src python3 -m unittest discover -s tests -v
git diff --check
```

The standalone inventory tool needs only Python 3.8 or later and its standard
library. It can be copied to a target independently of the package:

```sh
python3 tools/inspect_target.py --help
```

| CLI command | Purpose | Additional local requirements |
| --- | --- | --- |
| `replay` | Evaluate synthetic trajectories and rejection checks; no neural model | None |
| `camera` | Save a ZED left color image | Connected camera, matching ZED SDK and Python binding |
| `state` | Subscribe to Unitree sport state | Working SDK2/DDS installation and explicit network interface |
| `record` | Save an image and corresponding received robot state | Both camera and state requirements |
| `infer` | Check synchronous inference using existing local model files | Compatible upstream TIC-VLA package, model dependencies, weights, and GPU |

See [onsite preparation](docs/onsite.md) for arguments and result interpretation.
Dependencies and model files are not downloaded automatically. The example
configuration contains unvalidated test limits, not approved B2 operating limits.
Local tests use synthetic inputs and mocked optional dependencies; they do not
establish sensor, model, or robot performance.

## License and publication

Original code and documentation use the [MIT License](LICENSE), with the
collective notice `Copyright (c) 2026 VLN_B2 contributors`. Contributors retain
their respective rights; this notice does not assign ownership to a person,
laboratory, or university.

The lab repository is [DARC-UW-Madison/VLN_B2](https://github.com/DARC-UW-Madison/VLN_B2).
No upstream source code, model weights, recordings, or laboratory data are
included. Their terms remain separate; this license grants no rights to TIC-VLA
or its weights. See [third-party materials](THIRD_PARTY.md).

Future datasets, recordings, and trained or converted weights need an explicit
release decision and artifact-specific terms; they do not automatically inherit
this repository's MIT license. Review unpublished research before sharing it.

Documentation was prepared with AI assistance and must be reviewed as research
material; it does not constitute experimental evidence.
