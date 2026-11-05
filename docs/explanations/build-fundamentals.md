# What a build makes and how the result runs

[日本語](build-fundamentals.ja.md) · [Actual setup](../records/jetson-runtime.md) · [Runtime flow](../reference/runtime-flow.md)

> Document type: **Explanation**.

## Start with the objects involved

A CPU executes machine instructions. Source code expresses a program in a form
people can edit. A compiler translates suitable source into instructions for a
target machine. A build coordinates this translation, combines its outputs and
packages the result. Installing places that result where an application can use
it; running creates a process and executes it. Training changes learned model
parameters; inference applies those parameters to inputs. These are separate
operations. Our long build made software, not learned navigation weights.

| Object | Meaning in this project |
|---|---|
| Source | Python, C++ and CUDA files describing software behavior |
| Object file, often `.o` | Compiled component, usually awaiting combination with others |
| Executable | Program the OS can launch, such as the Python interpreter or our CUDA check |
| Shared library, `.so` on Linux | Compiled functionality loaded by another program |
| Wheel, `.whl` | Installable Python-package archive; may contain Python and compiled libraries |
| Model weights | Learned numeric tensors; not produced by compiling PyTorch |
| Docker image | Application filesystem/configuration assembled from layers |
| Container | Running instance with its own process/filesystem namespaces, sharing the host kernel |

## Why Python can require a compiler

Ordinary CPython translates `.py` into bytecode and executes that bytecode in its
interpreter. Its `.pyc` cache is not a standalone ARM executable. The interpreter
itself is compiled software. Packages can also load compiled extensions:
`torch._C` connects Python to native Torch functionality. Python is the API,
while heavy operations execute through compiled C++ and GPU libraries.
See [CPython extension modules](https://docs.python.org/3.11/extending/building.html).

```text
Python application
  -> Python package / native extension
  -> compiled CPU code and operation dispatcher
  -> CUDA libraries or compiled GPU kernels
  -> host NVIDIA driver
  -> GPU
```

Calling a matrix multiplication on a CUDA tensor dispatches GPU work. The host
CPU still runs Python, schedules work and manages data. CPU and GPU sharing
physical RAM on Orin does not remove tensor-device placement or synchronization.
GPU operations can be asynchronous; a measurement must wait for completion rather
than timing only the CPU's submission of the operation.

## Compiler, linker, build system and package manager

For native code, a simplified path is:

```text
.cpp -> C++ compiler -> .o files --+
                                +-> linker -> executable / .so -> wheel -> install
.cu  -> nvcc -> CPU/GPU objects --+
```

The compiler checks/translates individual source units. The linker combines
compiled units and resolves references to other functions/libraries. A missing
header is normally a compilation problem; an unresolved symbol can be a linking
or loading problem. A missing Python module is another layer again. Classifying
the failure avoids repeatedly changing unrelated packages.

CUDA source mixes CPU-side coordination and GPU functions. `nvcc` coordinates
their compilation, including a host C++ compiler and GPU compilation. Compiling
a CUDA kernel normally uses CPU compiler processes; it does not mean the GPU is
learning. Read [CUDA 11.4's compiler guide](https://docs.nvidia.com/cuda/archive/11.4.0/cuda-compiler-driver-nvcc/index.html).

CMake discovers dependencies and generates a build graph. Ninja executes that
graph, scheduling compilation/link commands. CPython's build used configure and
Make. pip installs Python packages and can invoke package build tooling when a
suitable built package is unavailable. A wheel can avoid compilation during
installation because compilation already happened elsewhere.

## Why this Jetson did not get an arbitrary wheel

Compiled packages must match several boundaries:

| Boundary | Current target |
|---|---|
| CPU architecture | Linux aarch64, rather than an x86-64 PC |
| OS/native ABI | Linux shared-library interfaces; an ARM Mac package is not a Linux package |
| Python extension ABI | CPython 3.11 for the selected application runtime |
| CUDA/toolchain and driver | Inspected L4T 35.4.1 / CUDA 11.4 generation |
| GPU instruction target | Orin compute capability 8.7, selected as `sm_87` / `8.7` |
| Library interfaces | Torch/vision and other native dependencies must agree |

A wheel's compatibility tags describe interpreter, ABI and platform; see the
[Python packaging specification](https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/).
For example, `cp311` denotes CPython 3.11 in the relevant tag. These tags alone do
not certify every CUDA/driver constraint. Compute capability 8.7 is a GPU
architecture identifier, not CUDA version 8.7.

The inspected NVIDIA JetPack-5 wheel used Python 3.8, while the selected upstream
application needs Python 3.10+. pyenv changes the interpreter; it does not rebuild
Torch or replace the GPU driver. We therefore evaluated a source-built candidate
against the existing host. This is not a rule to build everything from source:
a compatible reviewed binary is usually simpler. The exact constraints and older
Torch's unresolved loading risks are in [runtime compatibility](../records/runtime-compatibility.md).

## Build record

The steps performed on this Jetson are in [the GPU build record](../records/gpu-build-process.md).

## Docker's build and the compiler's build are different scopes

An image build executes Dockerfile instructions. A `RUN` step can download a
package, invoke a compiler, run a check or write metadata. Consequently one
Docker build can contain several native software builds.

| Instruction | What our recipe uses it for |
|---|---|
| `FROM` | Select a base image/stage |
| `ARG` | Build-time values such as pinned revisions; not a secret store |
| `ENV` | Environment values retained for later steps and container execution |
| `RUN` | Execute installation, compilation or validation during image construction |
| `COPY` | Put selected context files into the image |
| `CMD` | Set the default command for a later container run; writing it does not execute it |

See the [Dockerfile reference overview](https://docs.docker.com/build/concepts/dockerfile/).
The final `.` in `docker build ... .` is the build context: the directory from
which permitted `COPY` inputs come. `.dockerignore` excludes private/local files.
Docker records filesystem changes in image layers, not a running Python session
or already-loaded model memory. `docker run` starts a fresh process later.

Unchanged build layers can be reused. Changing an early input can invalidate
later cached work; this is why copying frequently edited documentation before a
long compile can cause unnecessary recompilation. Our recovery preserved the
completed Torch image and generated the remaining recipe with its build arguments.
See [cache invalidation](https://docs.docker.com/build/cache/invalidation/).
No compiler runs just because someone opens SSH or starts the existing image.

## One small example you can trace completely

The existing `deploy/cuda-smoke.cu` calculates `output[i] = 2*x[i] + y[i]` for
256 values. CPU code creates inputs, allocates CUDA buffers, submits a GPU kernel,
waits, and compares every result with a CPU reference. The kernel uses two blocks
of 128 threads and rejects indices outside the array. This builds/runs a program
with no neural network, sensor, internet or robot dependency.

The build command already used on this target was:

```sh
/usr/local/cuda/bin/nvcc -O2 -arch=sm_87 deploy/cuda-smoke.cu -o local/native-smoke/cuda-smoke
```

`-O2` selects compiler optimization, `-arch=sm_87` targets Orin's GPU architecture,
and `-o` names the output executable. Compilation creates the file; launching it
performs the calculation. Our Torch test then checks larger library operations.
Both are narrower than running TIC-VLA with real weights.

## What to rebuild when you change something

| Change | Usual consequence |
|---|---|
| Navigation instruction | New inference input; no Torch rebuild |
| Compatible model weights | Review/load new assets; usually no Torch rebuild, but model compatibility must be checked |
| Our Python adapter | Update source and restart the process; rebuild the application image if source was baked into it |
| C++/CUDA extension | Recompile/relink that extension and rebuild its package/image as applicable |
| Torch native source or enabled backends | Rebuild affected native components and dependent extensions |
| JetPack/driver/GPU platform | Re-evaluate compatibility, then rebuild/retest the affected environment |

Later optimizations may involve quantization, TensorRT engine generation,
`torch.compile` or kernel specialization. Those are additional transformations
with their own hardware, numerical, timing and artifact constraints. They were
not done by the build described here. Fine-tuning is another operation again:
it updates learned parameters using data and a training objective.

Version pins and a base-image digest improve provenance. They do not make this
recipe a complete reproducibility lock: apt/transitive packages and build
conditions also matter. Keep inventories and exact revisions, then strengthen
the lock before formal research comparisons. Build success, import success,
finite GPU arithmetic, model inference quality and safe physical motion are
separate claims with separate tests.
