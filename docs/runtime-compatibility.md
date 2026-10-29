# Inference runtime compatibility

[日本語](runtime-compatibility.ja.md) · [Target baseline](target-baseline.md)

Research date: **2026-10-27**. The model-free candidate has built and passed
GPU/import checks. On 2026-10-29, approved assets and CPU conversion enabled
strict GPU loading and one synthetic inference; original pickle decoding on
this older GPU Torch remains blocked.
See [runtime setup](jetson-runtime.md) for executed steps, the local RPC guard,
build recovery, results and storage prerequisites.

## Decision

Keep Ubuntu 20.04, L4T 35.4.1, CUDA 11.4, ROS Foxy and ZED intact. Evaluate a
**custom arm64 inference container based on `nvcr.io/nvidia/l4t-jetpack:r35.4.1`,
with Python 3.11.18 and source-built PyTorch 2.2.2**. This is a bounded engineering
candidate with a successful build and model-free GPU/import tests. The evidence
does **not** establish that changing the host OS or JetPack is unavoidable.

The [observed host](target-baseline.md) has a working native CUDA driver query
and GPU arithmetic check. Arithmetic also passed in the matching base container,
and the Python stage exposes a CUDA device. The final image also passed eight
FP32/BF16 Torch operations and full imports without models.
Docker shares the host kernel/driver interfaces; selecting a newer CUDA image
does not establish compatibility.

## Evidence and constraints

| Layer | Finding and implication |
|---|---|
| Python | This package and [upstream](https://github.com/ucla-mobility/TIC-VLA/blob/main/pyproject.toml) require 3.10+. The host default is 3.8.10. Preserve system Python; build the application interpreter inside the container. Use [3.11.18](https://www.python.org/downloads/release/python-31118/) for this candidate; the [3.10 series](https://www.python.org/downloads/release/python-31019/) is now unsupported. |
| Official JetPack 5 wheel | NVIDIA lists `torch-2.1.0a0+41361538.nv23.06-cp38-cp38-linux_aarch64.whl` for JetPack 5.1.2. It is ARM64 GPU software but its CPython 3.8 ABI cannot serve the selected Python 3.11. See [NVIDIA's download center](https://developer.nvidia.com/embedded/downloads). |
| Official matching base | [NGC tags](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/l4t-jetpack/tags) confirm `nvcr.io/nvidia/l4t-jetpack:r35.4.1`, `linux/arm64`, compressed size **4.9 GB**, manifest digest `sha256:d1c8e971ab994235840eacc31c4ef4173bf9156317b1bf8aabe7e01eb21b2a0e`. It supplies JetPack libraries, not the proposed Python/PyTorch stack. |
| Existing PyTorch image | [NGC](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/l4t-pytorch/tags) confirms `nvcr.io/nvidia/l4t-pytorch:r35.2.1-pth2.0-py3`, `linux/arm64`, **5.66 GB** compressed. This is an older L4T tag and does not establish a Python 3.11 runtime for this project. No ready-made official image satisfying all constraints was verified. |
| Training versus inference | [Training requirements](https://github.com/ucla-mobility/TIC-VLA/blob/main/requirements-train.txt) pin Torch 2.8.0/cu128. They are not a demonstrated inference minimum. NVIDIA's [Tegra compatibility table](https://docs.nvidia.com/cuda/cuda-for-tegra-appnote/) limits JetPack 5 CUDA upgrade packages to 11.8–12.2; CUDA 12.3 onward is unsupported there. The existing 11.4 driver query is not approval for cu128. |
| FlashAttention | [TIC-VLA's loader](https://github.com/ucla-mobility/TIC-VLA/blob/main/ticvla/models/vlm.py) explicitly sets `use_flash_attn=False`. [InternVL3-1B code](https://huggingface.co/OpenGVLab/InternVL3-1B/blob/main/modeling_internvl_chat.py) then selects eager language attention and disables vision FlashAttention. Do not install FlashAttention for this first candidate. Even historical [FlashAttention 2.3.6](https://github.com/Dao-AILab/flash-attention/blob/v2.3.6/README.md) requires CUDA 11.6+, above the current toolkit. |
| Inference dependencies | `ticvla.models.vlm` imports `ticvla.data.vlm_data`, which imports Lightning. A model-only import therefore still needs Lightning and its bounded dependencies unless a separately reviewed upstream compatibility patch removes that coupling. Do not install the complete training/robotics requirements blindly. |
| TensorRT | The inspected synchronous adapter uses PyTorch and Transformers. Installed TensorRT 8.5.2 does not provide a conversion, cache interface, or compatible engine for this path. |

## Bounded build candidate

After storage preparation, use the matching base above, pinned by digest. Keep
image layers/build cache and application artifacts on dedicated SSD storage. Review base-image and dependency terms before use.

1. Build an isolated **CPython 3.11.18** interpreter and an ARM64 wheelhouse inside
   the image; leave the container's vendor Python and the host interpreter alone.
2. Build **PyTorch v2.2.2** from its exact upstream source/submodule revisions
   against CUDA 11.4 and the base's cuDNN. Its [CUDA CMake check](https://github.com/pytorch/pytorch/blob/v2.2.2/cmake/public/cuda.cmake)
   permits CUDA 11.0+, and its [build options](https://github.com/pytorch/pytorch/blob/v2.2.2/CMakeLists.txt)
   disable fused attention below CUDA 11.6. This is source-level eligibility,
   **not proof that the complete Jetson build succeeds**. Use GCC 9.4+, C++17,
   `TORCH_CUDA_ARCH_LIST=8.7`, `USE_FLASH_ATTENTION=0`,
   `USE_MEM_EFF_ATTENTION=0`, `USE_DISTRIBUTED=1`, `USE_NCCL=0`, Gloo enabled,
   and initially `MAX_JOBS=4`. Distributed availability matters for Lightning and
   InternVL's `torch.distributed.is_initialized()` call; no distributed run is needed.
3. Build **torchvision v0.17.2** against that exact wheel/interpreter. Start the
   Python dependency compatibility trial with **Transformers 4.44.2**,
   **pytorch-lightning 2.2.5**, **torchmetrics 1.2.1**, **NumPy 1.26.4**,
   **timm 0.9.12** and **einops 0.7.0**; resolve and record remaining transitive
   dependencies without replacing Torch. These are proposed trial pins, not a
   tested lockfile. [Lightning 2.2.5](https://github.com/Lightning-AI/pytorch-lightning/blob/2.2.5/requirements/pytorch/base.txt)
   bounds Torch below 2.3 and torchmetrics below 1.3. InternVL requires
   Transformers 4.37+, and the trial satisfies upstream's declared 4.40–4.x range.
4. Pin TIC-VLA and the eventual base-model Python/config revisions. Check import,
   processor/tokenizer kwargs, and the actual cache type. The synchronous
   [`predict()`](https://github.com/ucla-mobility/TIC-VLA/blob/main/ticvla/models/ticvla.py)
   accepts a legacy tuple or a cache with `layers`; [Transformers 4.44.2](https://github.com/huggingface/transformers/blob/v4.44.2/src/transformers/models/qwen2/modeling_qwen2.py)
   has a legacy-cache return path. Training's stricter cache handling is outside
   this inference trial. If import/build/cache compatibility fails, record the
   exact failure and stop for a scoped patch or revised pin; do not broaden into
   host upgrades or an unbounded dependency search.

PyTorch 2.2.2 exposes [`torch.load(weights_only=True)`](https://github.com/pytorch/pytorch/blob/v2.2.2/torch/serialization.py),
which the adapter requires, but this version is affected by the official
[2025 weights-only advisory](https://github.com/pytorch/pytorch/security/advisories/GHSA-53q9-r3pm-6pq6)
and [2026 weights-only advisory](https://github.com/pytorch/pytorch/security/advisories/GHSA-63cw-57p8-fm3p).
Do not describe its deserializer as safe merely because that flag exists.
The initial candidate is limited to the model-free smoke below. Before external
checkpoint loading, resolve reviewed fixes/backports or a separately reviewed
conversion and loading path such as safetensors. The adapter now rejects
checkpoint decoding on Torch 2.2.2, supports a tensor-only safetensors path and
forces safetensors for base-model AutoModel loading. Its mocked contracts and
a real generated-tensor CPU probe passed on Jetson. A separate Torch 2.15.0+cpu
converter subsequently passed generated checkpoint conversion and old-runtime
readback. The exact 17-file acquisition was approved on 2026-10-29; payload
verification, actual CPU conversion, strict GPU loading and one synthetic-image
inference subsequently passed. [Artifact records](model-artifacts.md) retain
pins and applicable terms; [offline model checks](model-runtime.md) record the
actual runtime and limits. Real sensors, navigation quality and asynchronous
control remain unvalidated. Retain strict keys/shapes and no unrestricted-pickle
fallback.

## Next smoke test and acceptance

First inventory already-present images and local runtimes. If no suitable image
exists, prepare storage before downloading or building it. These steps and the
model-free checks below passed on the inspected target. For another target,
build/check its matched image and run it with `--pull=never`,
`--runtime=nvidia`, `--network=none`, no robot devices/sockets and Hugging Face
offline settings. No model is needed for these acceptance checks:

- Assert ARM64, Python 3.11, the intended Torch/torchvision/Transformers versions,
  `torch.version.cuda == "11.4"`, CUDA device availability and capability 8.7.
- Synchronize actual GPU operations: FP32 and BF16 matrix multiplication,
  convolution, layer normalization and multihead attention; require finite
  outputs. Record BF16 support, peak allocated memory and elapsed time.
- Import torchvision, Transformers, Lightning and `ticvla.models.ticvla`;
  inspect `torch.load`'s `weights_only` argument. Record library-loading errors
  instead of treating a successful `cuInit` or `import torch` as acceptance.

Only after those pass and the checkpoint-loading issue above is resolved,
separately approve the precise base-model/checkpoint
files, revisions, terms, sizes and official-cache location. Load trusted local
assets offline, require strict checkpoint compatibility, and run one recorded
image sequence through the existing synchronous adapter. Check finite
`(1, horizon, 2)` waypoints and measure latency/memory. This establishes package
inference only; asynchronous caching, control and real-time capability remain
unproven. OS/ROS/ZED changes are not part of either smoke test.
