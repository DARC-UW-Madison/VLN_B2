# Terminology: from Python packages to a robot

[日本語](glossary.ja.md) · [Documentation](../README.md) · [Build explanation](build-fundamentals.md)

> Document type: **Explanation**.

Terms are introduced here by the thing they describe. A component's presence is
not evidence that it has been integrated or tested. See [status](../status.md) for
actual completion and [deployment choices](deployment-design.md) for placement.

## Program, process and environment

| Term | Meaning | Example in this project |
|---|---|---|
| Source code | Human-readable instructions | Our `.py` files, upstream model implementation |
| Process | A running instance of a program, with memory and an execution lifetime | A camera receiver or one Python inference program on Jetson |
| Runtime | Software/support needed while a process executes | Python, native libraries, GPU support; not the model's learned knowledge |
| Dependency | Software a program relies on | Our optional inference adapter needs upstream code and PyTorch |
| API | Agreed programming interface: names, arguments and results | A Python model method or a robot velocity request |
| SDK | Vendor's libraries, headers, examples and tools for an API | Unitree SDK2 for B2 communication; ZED SDK for a camera; they are different SDKs |
| Driver | OS/device support translating requests to hardware | The host NVIDIA or USB driver; an SDK may use that driver |
| CLI / GUI | Command-line interface / graphical interface | SSH terminal / desktop settings dialog |
| Shell | Interpreter for terminal commands | Bash on Jetson; not the Python interpreter |
| Environment variable | Per-process configuration inherited by children | `PYTHONPATH`, a DDS setting; different shells can have different values |
| ABI | Binary-level calling/data convention | A native Python extension must match its interpreter/platform, not only its package name |

An API can be a local function call without network traffic. A network API also
needs a protocol and reachable service. An SDK is not automatically a server,
a separate computer, ROS, or the hardware's firmware.

## Python, pyenv, pip, venv and wheel

Python is both a language and an interpreter ecosystem. `python3` selects an
interpreter executable; that interpreter searches its configured package paths
when it executes `import torch`. Using another interpreter may select another
package installation even from the same terminal.

- **pyenv** manages interpreter versions such as Python 3.11.18. It does not
  install the correct GPU driver or grant filesystem isolation.
- **venv** creates a project package environment tied to an interpreter. It
  separates installed Python packages; it does not prohibit network/file access.
- **pip** installs Python distributions and resolves their declared dependencies.
  `python -m pip` explicitly uses the pip associated with that Python.
- **PyPI** is a package index. An index contains distribution metadata/files,
  rather than a running instance of a model.
- **Build** transforms source into an installable or executable artifact.
  Compiled extensions can require C/C++/CUDA compilation. Pure Python packaging
  need not involve machine-code compilation.
- **Wheel** is Python's `.whl` distribution format: a ZIP-based installation
  archive with metadata. It may contain pure Python or already compiled native
  libraries. It is neither a robot wheel nor a model checkpoint.

For example, `example-1.0.0-py3-none-any.whl` denotes generic Python 3/no binary
ABI/platform-independent tags. An illustrative
`example-1.0.0-cp311-cp311-linux_aarch64.whl` targets CPython 3.11 with that ABI on
Linux ARM64. Even appropriate filename tags do not promise compatibility with
this Jetson's CUDA, external libraries or GPU architecture. The actual Torch
wheel also needs the runtime configuration described in our build guide.
See the [wheel specification](https://packaging.python.org/en/latest/specifications/binary-distribution-format/).

Installation of a suitable prebuilt wheel usually avoids compiling that package
locally. If a compatible wheel is unavailable, its source may need a local
build. We built a candidate Torch wheel on Jetson because this inspected
Python/L4T/CUDA combination required a controlled compatible build, not because
every robot project must rebuild Torch. Installing that wheel inside Docker does
not put it into the host venv. Installing the separate `wheel` packaging tool is
also not the same as installing every package distributed as a `.whl` file.

## PyTorch, tensors, CUDA and precision

**PyTorch** is the numerical/deep-learning library whose Python import name is
`torch`. It provides tensors, neural-network operations and automatic
differentiation for training. Here its immediate purpose is to execute an
already trained model. PyTorch is an execution library, not TIC-VLA itself.
See the [official PyTorch documentation](https://docs.pytorch.org/docs/stable/index.html).

A **tensor** is a multidimensional array. An RGB image can become a tensor with
height, width and color-channel axes; a neural network's weights are also tensors.
An operation such as matrix multiplication combines these arrays. A tensor has
shape, data type and device placement; a CPU tensor does not automatically run
on the GPU merely because the machine has one.

| Term | Meaning | What it does not establish |
|---|---|---|
| CUDA | NVIDIA's GPU programming/execution platform | Not a replacement for the host GPU driver or a model |
| CUDA kernel | A function executing parallel GPU work | Not the Linux operating-system kernel |
| cuDNN | Optimized GPU operations used by deep-learning libraries | Does not supply model weights |
| torchvision | Image/model utilities and native operators used with Torch | Not a USB camera driver |
| Transformers | Library used to construct/run many language and multimodal models | Not one specific model or a mandatory cloud call |
| FP32 | 32-bit floating-point representation | A tiny FP32 test is not model-quality validation |
| FP16 / BF16 | Different 16-bit floating-point formats with different exponent/precision tradeoffs | Successful BF16 arithmetic does not prove all model operations are supported |
| INT8 / quantization | Integer representation / reducing representation precision with a defined method | Does not automatically preserve accuracy or remove source-weight terms |
| Training | Compute loss/gradients and update learned parameters | Not what compiling Torch or running inference does |
| Inference | Use learned parameters to compute output from input | Does not make every predicted action valid for the physical robot |

**Weights** are learned numerical parameters. **Architecture/model code** defines
how they are used. A **checkpoint** saves model state and may also include
training metadata, optimizer state or serialized objects. File suffixes such as
`.ckpt` and `.pt` do not guarantee a safe or tensor-only format. The candidate
Torch version's checkpoint loading is blocked pending review; offline execution
and `weights_only=True` alone do not resolve its documented vulnerabilities.

## HF, Hub and model assets

**HF** commonly abbreviates **Hugging Face** in our environment, as in
`HF_HUB_OFFLINE`. “HQ” is not a defined component in this project. Interpret any other
abbreviation from its exact command/context rather than adding an assumed tool.

Hugging Face hosts code, model and dataset repositories. The **Hub** is the
hosting/access service. `huggingface_hub` is a client library, and `hf` is its
command-line interface. These are different from PyTorch, which performs tensor
computation. A tokenizer maps text to model tokens; configuration describes model
structure/settings; weights hold learned values. A model may need all of these,
not just one large checkpoint.

A **revision** identifies a particular repository state. A **cache** stores fetched
files locally for reuse. The [official download guide](https://huggingface.co/docs/huggingface_hub/en/guides/download)
explains revision-specific acquisition. The standard Jetson cache points to our
SSD area and is currently empty. The workflow requires exact artifacts, terms,
revision, sizes and approval before acquisition. No model assets are downloaded
merely by reading these guides. Once every reviewed input is local and the
loader supports it, inference can be offline; HF is not necessarily an API
server in the live robot loop.

## Docker and version control

| Term | Meaning in this project |
|---|---|
| Dockerfile | Instructions for constructing an application environment |
| Image | Stored filesystem layers/configuration produced by a build |
| Container | A process environment instantiated from an image; it shares the host kernel |
| Bind mount | Explicitly make a host path accessible inside a container; can be read-only |
| Docker volume | Data managed separately from a container's writable layer |
| Build context | Files made available to the image builder; limited by `.dockerignore` |
| Tag / image ID / digest | A movable name / local content identity / content identifier used for image references; record the actual identity, not just the name |
| Git commit | A recorded source snapshot and its history/metadata |
| GitHub repository | A remote collaboration/history location; not an always-running robot service |
| Clone / pull / push | Create a Git copy / fetch and integrate source / send committed history |
| Artifact | A produced item such as a wheel, image, checkpoint or report; not every artifact belongs in Git |

Git revision, image identity and model-asset revision answer different questions.
One cannot substitute for the others in an experiment record. See
[deployment choices](deployment-design.md) and [build fundamentals](build-fundamentals.md).

## Network, robotics and supervision

| Term | Concrete meaning |
|---|---|
| Ethernet / Wi-Fi | Wired / wireless link technologies; neither alone assigns the correct IP settings |
| Interface / IP / subnet / route | Local link device / endpoint address / address group / selected packet path |
| AP / hotspot | Wi-Fi access point; a Jetson-hosted AP can connect Mac locally without internet |
| SSH / RDP / VNC | Remote terminal / two remote-desktop protocols; all require a working network |
| Tailscale | Identity/policy and encrypted reachability over an underlying network; not radio coverage |
| DDS / RTPS | Typed distributed data exchange/discovery / its wire-level interoperability protocol |
| ROS 2 / node / topic / RMW | Robotics framework / participating process / typed publication channel / middleware abstraction |
| QoS | Delivery/history/freshness-related communication settings; compatible endpoints are required |
| Timestamp / clock | A recorded time / time source; unrelated clocks cannot simply be subtracted |
| Coordinate frame / transform | A reference for axes/origin / mapping between references |
| Pose / velocity / waypoint | Position and orientation / rate of motion / a target position along a path |
| Localization / SLAM | Estimating pose in a map / estimating pose and building a map |
| Tracking controller | Converts a path and current state into candidate motion requests |
| Watchdog / expiry | Detect missing progress or invalidate data/commands after a deadline |
| Supervisor | Starts/observes process lifecycle; a restart policy alone is not a robot stop guarantee |
| Arm / disarm | Explicitly permit / inhibit the research application's motion requests |
| Deadman / operator override | Continued operator permission requirement / operator taking control away from software |
| Emergency stop | A separately verified physical/system stop function; do not equate any software stop request with it |

Detailed wiring, domains, times and physical stop behavior remain measurements to
make on this B2. A fluent explanation of the terms does not establish that the
interfaces work. Read [the field procedure](../how-to/field-network.md) and
[offline operation](../how-to/offline-operation.md) for the corresponding acceptance work.
