# B2 TIC-VLA

[日本語](README.ja.md) · [Documentation](docs/README.md)

Research workspace for evaluating TIC-VLA navigation on the **Unitree B2**.
The goal is to connect language-conditioned path prediction to the robot's
existing walking controller and measure the effect of delayed model inference.
This is an independent integration project, not an official release by the paper's
authors or the robot manufacturer.

## Scope and current state

The available setup is B2, an external Jetson AGX Orin, ZED 2i and Livox Mid-360.
The intended deployment keeps perception/inference and eventual high-level
control on Jetson; Mac is for development and optional result display. A prepared
local run should not require Mac, campus Wi-Fi or a cloud inference service.
The onboard sensor/service roles and control path still require inspection.

The repository provides target inventory, synthetic replay, camera/state
acquisition adapters, paired recording and optional synchronous offline inference.
**These tools send no motor commands.** Host setup and model-free GPU/import
checks passed. Approved weights were acquired and CPU-converted separately;
strict GPU loading and one synthetic-image inference passed. Real sensor/B2
integration, asynchronous control and physical stopping remain unverified.
No weights or third-party model code are included in this repository,
and no autonomous application is installed. Start with recorded observations,
then live observation; controlled movement follows only after interface and
stop validation. Training a replacement walking policy is outside this scope.

Read the [documentation index](docs/README.md) for concepts, terminology,
verified specifications, environment setup, field procedures, project status
and the next deliverable. All guides have maintained Japanese counterparts.

## Try the preparation tools

From the repository root, Python 3.10 or later can run the dependency-free CLI
help and local tests without installing the package:

```sh
PYTHONPATH=src python3 -m b2_tic_vla --help
PYTHONPATH=src python3 -m unittest discover -s tests -v
git diff --check
```

`replay` evaluates synthetic input. `camera`, `state` and `record` require working
vendor dependencies and verified hardware/network configuration. `infer` requires
separately approved local upstream/model assets and a reviewed compatible loader;
the older candidate runtime is currently restricted to model-free checks.
Dependencies and assets are not downloaded automatically. Synthetic/mocked tests
do not establish hardware performance; example limits are not B2 operating limits.

## Collaboration and license

The intended lab destination is
[DARC-UW-Madison/VLN_B2](https://github.com/DARC-UW-Madison/VLN_B2).
Initial source publication is pending the user's instruction. GitHub hosting is
not a runtime dependency. Development uses reviewed source changes, bilingual
documentation and separate machine-local environments/artifacts.

Original code and documentation use the [MIT License](LICENSE), with
`Copyright (c) 2026 VLN_B2 contributors`. Contributors retain their respective
rights. This does not relicense TIC-VLA, model weights, dependencies or datasets.
No upstream source, weights, recordings or private lab data are bundled.
Future results/assets require separate release decisions and applicable terms.
The documentation index includes the contribution rules, licensing explanation
and third-party inventory. Documentation uses AI assistance and requires review;
it is not experimental evidence.
