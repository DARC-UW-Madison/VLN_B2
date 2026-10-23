# B2 TIC-VLA

[日本語](README.ja.md)

Research workspace for evaluating TIC-VLA navigation on the Unitree B2.
The goal is to connect language-conditioned navigation to the robot's existing
walking controller and measure the effect of delayed model inference.

**Status:** documentation only. No inference service, robot adapter, or B2
experiment has been implemented or validated. This is an independent project;
it is not an official release from the paper's authors or the robot manufacturer.

## Read first

| Document | What it explains |
| --- | --- |
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
for confirmed facts and the next inspection. There is no installation or robot
launch command yet; the installed software and working interfaces remain unverified.
To inspect a local change, run `git diff --check` and follow the review steps in
[Contributing](CONTRIBUTING.md).

## License and publication

The rights holder and license for original project work have not been selected.
Lab GitHub hosting is authorized; its destination and visibility still need to be
specified. The repository is currently local. No upstream source code,
model weights, recordings, or laboratory data are included. A future project
license will not replace the terms of third-party materials.

Documentation was prepared with AI assistance and must be reviewed as research
material; it does not constitute experimental evidence.
