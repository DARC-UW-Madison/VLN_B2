# GPU environment build record

[日本語](gpu-build-process.ja.md) · [Records](README.md)

> Document type: **Record**. Steps performed for this environment.

## What the completed build actually did

1. **Use a matching base image.** NVIDIA's pinned ARM64 L4T image provides a
   compatible userspace/toolkit foundation. It uses the host's kernel/driver.
2. **Build Python.** Download checked CPython source, configure `/opt/python`,
   compile with four jobs and install it inside the image. A separate host Python
   was built under the research login; these are distinct installations.
3. **Build Torch.** Fetch the exact source revision and submodules. CMake/Ninja
   compile C++/CUDA, target Orin and package a wheel; pip installs that wheel into
   the image's Python. The 2093-target counter referred to native build tasks,
   including compilation/linking, not training iterations or overall completion.
4. **Build torchvision.** Compile the selected vision package against that Torch.
   Independently matching version numbers is insufficient without compatible
   native libraries.
5. **Install inference dependencies.** Install the selected Transformers,
   Lightning and related packages. The build-only CMake/Ninja wheels are removed
   after compilation; check the remaining package requirements and record them.
6. **Finish the image and test it.** Store the environment as
   `vln-b2-runtime:jp5`; create offline test containers using the real Orin GPU.

`MAX_JOBS=4` limits concurrent compiler jobs to bound resource use. It is unrelated
to the GPU core count, robot count or inference rate. Compilation takes time
because Torch contains a large amount of native code and many GPU kernels.

The candidate intentionally excludes TensorPipe RPC. Torch's Python availability
check nevertheless tried to import it, so a hash-checked local feature guard was
added. This is unrelated to Unitree requests and does not repair checkpoint
deserialization vulnerabilities. Build-only wheels also had malformed metadata;
their binaries worked, then they were removed before the final dependency check.
See [actual recovery and evidence](jetson-runtime.md#torch-import-guard-and-build-recovery).
