# Model artifacts and verified loading path

[日本語](model-artifacts.ja.md) · [Documentation](README.md) · [Runtime compatibility](runtime-compatibility.md) · [Licensing](licensing.md)

Metadata review: **2026-10-28**; executed acquisition/conversion/runtime checks:
**2026-10-29**. The operator approved the exact 17 files below for private
academic research. All payload sizes/digests passed; the actual checkpoint was
converted on modern CPU Torch, then strictly loaded on the older Jetson GPU
runtime. One synthetic-image inference returned 30 finite XY points. This is
not redistribution permission, real-camera validation or a real-time controller.

The original pickle checkpoint is never decoded on Torch 2.2.2. The GPU path
uses the verified derived safetensors plus the reviewed local base snapshot.
Independent tooling is implemented; runtime evidence, failed checks and limits
are in [offline model checks](model-runtime.md), with conversion details in
[the conversion guide](checkpoint-conversion.md). Source/component terms remain
applicable to raw and derived artifacts; model payloads are outside Git.

## 1. Inputs are different artifacts

The reviewed TIC-VLA implementation is source revision
`9fa6f8b66b9e121d5df5df071297bba8e5353ebb`. Its
[package metadata](https://raw.githubusercontent.com/ucla-mobility/TIC-VLA/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/pyproject.toml)
requires Python 3.10 or later. Its
[training requirements](https://raw.githubusercontent.com/ucla-mobility/TIC-VLA/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/requirements-train.txt)
select Torch 2.8.0/cu128; that is not evidence of an inference minimum. The
[VLM loader](https://raw.githubusercontent.com/ucla-mobility/TIC-VLA/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/models/vlm.py)
constructs the base model with BF16, FlashAttention disabled and trusted custom
Python code. Reusing a trained model needs code, configuration/tokenizer assets,
base weights and the navigation checkpoint; they are not one installation file.

| Input | Function | Current state |
|---|---|---|
| Reviewed upstream Python | Defines TIC-VLA and its model calls | Source-only checkout exists separately for prior import checks |
| InternVL base snapshot | Defines/initializes the pretrained vision/language model and text/image processing | Pinned approved assets acquired and digest-verified |
| TIC-VLA checkpoint | Supplies the trained navigation/model state | Approved checkpoint acquired, hash-verified and CPU-converted |
| CPU converter environment | Decodes the source checkpoint using a separately reviewed runtime, then emits tensor data | Built with pinned CPU software; generated conversion and old-runtime readback passed |
| Derived tensor artifact and manifest | Input to the proposed Jetson loader, with conversion provenance | Actual converted artifact and verified manifest exist privately on SSD |

The current independent adapter constructs the upstream model and then loads a
strict full-model state dictionary. The apparently similar base/checkpoint sizes
do not prove that a base-weight download can be omitted. A configuration-only
construction optimization would be separate work, including upstream/API and
strict-state verification; it is not selected here.

## 2. Exact model candidates from official metadata

The following identities and expected sizes/digests came from the official
[TIC-VLA dataset API](https://huggingface.co/api/datasets/handsomeYun/TIC-VLA?blobs=true)
and [InternVL model API](https://huggingface.co/api/models/OpenGVLab/InternVL3-1B?blobs=true).
Resolve the pinned revisions, not an unqualified moving `main`, when preparing
an approved acquisition. Published LFS digests are expected values; they have not
been compared with local payloads at the initial metadata-only review. The
subsequent approved acquisition verified the actual files as recorded above.

| Repository and file | Pinned candidate revision | Expected bytes |
|---|---|---:|
| Dataset `handsomeYun/TIC-VLA`, `TIC-VLA-model.ckpt` | `671de608f39ccae41b66cbb24ab923c0275f8fb4` | 1,938,501,547 |
| Model `OpenGVLab/InternVL3-1B`, `model.safetensors` | `4415a3b810e636d11dfa86b0e9ba40bb00535aa8` | 1,876,463,472 |

Expected SHA256 values:

```text
TIC-VLA-model.ckpt
376263f89fad0f42c267d85655019232edc91d36e214e23424804dd4cd42e036

model.safetensors
a8b67c54568417f3631723e6b3e120720eaa638e03e62dc25666c70e3ae3e484
```

The TIC repository's inspected file list contains the `.ckpt` but no official TIC
safetensors alternative. InternVL already provides an official safetensors file;
there is no reason to fetch a pickle base-model alternative for this proposal.
Do not fetch the TIC repository's large training-data archives for first inference.

### InternVL allowlist

At the pinned InternVL revision above, the acquisition candidate is the following
set. Include the README for its terms/context; examples, videos and Git attributes
are not required for this runtime input. The custom Python must be reviewed as
executable code even though it is hosted next to weights.

| File | Expected bytes |
|---|---:|
| `README.md` | 35,849 |
| `added_tokens.json` | 790 |
| `config.json` | 6,326 |
| `configuration_intern_vit.py` | 5,548 |
| `configuration_internvl_chat.py` | 4,036 |
| `conversation.py` | 15,309 |
| `generation_config.json` | 69 |
| `merges.txt` | 1,671,853 |
| `model.safetensors` | 1,876,463,472 |
| `modeling_intern_vit.py` | 18,099 |
| `modeling_internvl_chat.py` | 15,971 |
| `preprocessor_config.json` | 287 |
| `special_tokens_map.json` | 613 |
| `tokenizer.json` | 7,033,297 |
| `tokenizer_config.json` | 7,330 |
| `vocab.json` | 3,383,407 |
| **Total** | **1,888,662,256** |

The two acquisition candidates total **3,827,163,803 bytes**, approximately
**3.83 GB / 3.56 GiB**. This excludes downloaded runtime packages, image layers,
conversion output, temporary files, recordings and logs. Derived size and peak
conversion/inference memory are unknown until measured. Check current free
space and define resource limits before acquiring or converting anything.

### Approved acquisition

On 2026-10-29 the operator explicitly approved the two pinned repositories,
17 files and 3,827,163,803 bytes above for private academic research in the
standard SSD-backed Hub cache. This is not approval for redistribution, robot
motion or unrestricted loading. Preserve the applicable source/component terms.
Acquisition verification, custom-code review and actual inference remain separate.

`tools/acquire_model_assets.py` prints the plan by default without importing the
Hub client or contacting the network. Explicit `--download` mode requires cache
and private report paths, uses the official client with token access disabled,
and verifies pinned repository revisions, approved sizes, weight SHA256 and
small-file Git blobs. It fetches only the allowlist and never executes model code.
Four non-network tests bring the suite to 125 local tests. Do not mount a home,
credential file or GPU into the downloader; mount only the standard Hub cache,
reviewed script and dedicated private report directory.

## 3. Terms and approval remain separate gates

The [reviewed TIC-VLA Academic Software License](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/LICENSE.md)
restricts research use and onward transfer, including derivatives. The dataset
API's CC-BY-4.0 label alone does not resolve conditions applying to this particular
checkpoint and its dependencies. InternVL's metadata contains an Apache-2.0
label together with a Qwen license name/link; do not certify all components from
the badge alone. Review the pinned model card, component terms and intended use.
No extra author permission or completed artifact-specific terms review is
asserted here, and no author has been contacted.

Before acquisition, present the exact repository/type, revision, file allowlist,
expected bytes, cache location and applicable terms to the user and obtain
approval. Building a runtime or authorizing general setup is not the recorded
approval for these model files. Do not run an automatic model downloader during
an import, conversion test or first inference.

## 4. Why a separate CPU conversion environment

The official [2025 weights-only advisory](https://github.com/pytorch/pytorch/security/advisories/GHSA-53q9-r3pm-6pq6)
affects Torch through 2.5.1; the official
[2026 advisory](https://github.com/pytorch/pytorch/security/advisories/GHSA-63cw-57p8-fm3p)
affects versions through 2.9.1. Their documented fixes are 2.6.0 and 2.10.0
respectively. `weights_only=True` on the existing 2.2.2 is insufficient. The
[PyTorch security policy](https://github.com/pytorch/pytorch/security/policy#backporting-security-fixes)
states that security fixes are not backported to old versions. No complete,
reviewed local backport has been established for our candidate.

A checkpoint-to-tensor conversion needs CPU operations, not a working new CUDA
stack. A separate CPU runtime could decode the source once and leave only tensor
data for the existing GPU runtime. This does not make old Torch generally
secure, remove trust in model Python or prove every other runtime component safe.
It narrows this particular deserialization path.

### Pinned CPU package and fixture validation

The [official PyTorch CPU index](https://download.pytorch.org/whl/cpu/torch/)
listed this candidate during the review:

```text
torch-2.15.0+cpu-cp311-cp311-manylinux_2_28_aarch64.whl
Expected bytes: 170730380
SHA256: 97dc6b0a7cbad2109e615da3eac03df626c61e821e9486438b0248ba896178c6
```

The initial HEAD/metadata review established the size and CPU/Python platform.
On 2026-10-29 the exact wheel was installed with 11 hash-pinned dependencies in
`vln-b2-converter:cpu-v1`, reusing the inspected Focal/Python-stage image.
`pip check`, CPU-only checks, generated checkpoint conversion and readback by
Torch 2.2.2 passed. This validates the recorded fixture path, not the real model
or a permanently current software selection. See the conversion guide for the
recipe, full image ID, failed first attempt and limits.

Do not substitute the ordinary PyPI ARM64 Torch package: its inspected 2.15.0
metadata declares Linux CUDA 13.2 dependencies. A matching ARM64/Python filename
alone is not proof of CPU-only packaging. Explicit CPU source/version selection
prevents accidentally changing the GPU stack during this conversion work.
The exact [CPU wheel reference](https://download-r2.pytorch.org/whl/cpu/torch-2.15.0%2Bcpu-cp311-cp311-manylinux_2_28_aarch64.whl)
and its [small package metadata](https://download-r2.pytorch.org/whl/cpu/torch-2.15.0%2Bcpu-cp311-cp311-manylinux_2_28_aarch64.whl.metadata)
identify the installed software pin; approved model assets were acquired separately.

## 5. Loading sequence and validation boundaries

1. Review permissions, acquire approval for exact assets and separately review
   the converter recipe/dependency plan. Preserve current images and host
   software. Keep conversion separate from Lightning/the older GPU Torch.
2. Build and test a CPU-only converter with self-generated small tensors first.
   Use no NVIDIA runtime/GPU, robot devices, Docker socket, personal credentials
   or writable home mounts. For actual conversion, disable networking, use an
   unprivileged process and bounded memory/CPU/time, expose only the one reviewed
   checkpoint read-only and a dedicated output directory. A container reduces
   exposure; it is not proof that executing arbitrary code is harmless.
3. On the reviewed CPU runtime, decode with `weights_only=True` and CPU placement.
   Require a nonempty string-keyed tensor mapping, accounting explicitly for a
   Lightning `state_dict` wrapper. Reject unsupported serialized metadata or
   types; do not automatically add unsafe globals or retry unrestricted pickle.
4. Retain every state key and tensor's dtype, shape and values. Shared tensor
   storage needs a deliberate strategy such as materializing separate contiguous
   copies. Do not silently drop tied/duplicate names: the receiving adapter
   requires exact full-model keys. Bound output size and validate supported
   tensor layouts before allocation/writing.
5. Save safetensors, read it back, and compare all keys, dtypes, shapes and values
   with the extracted state. Write a non-secret JSON manifest with source
   repository/type/revision/digest, converter source/image/dependency versions,
   output digest, tensor inventory, alias-handling method and verification result.
   Preserve architecture metadata explicitly when needed; never use pickle for
   the new manifest.
6. Add a reviewed safetensors-only path to our adapter. Keep strict key/shape
   validation and infer/validate horizon/layer counts from the state. Reject
   unexpected files; never fall back to `torch.load` on the old GPU runtime.
7. Force base-model loading to use local safetensors, with no pickle fallback.
   The current upstream call does not explicitly pass `use_safetensors=True`.
   An independent loader wrapper may provide that argument without copying
   upstream implementation; verify its actual effect with the pinned library.
   If a local upstream edit is needed, review permission for that edit and any
   transfer separately, preserve its provenance and terms, and do not publish
   restricted source or a combined image under our MIT notice.
8. Test model construction and one recorded observation on Jetson offline, with
   no robot connection or command sender. Require strict state agreement, finite
   expected waypoint shape and measured memory/latency. Record failures. Only
   then consider live observation and later asynchronous/motion integration.

The independent adapter now implements the application-side reader and wrapper
in steps 6–7. A `.safetensors` input uses `safetensors.torch.load_file` on CPU;
parse errors never retry pickle. Every key still passes prefix normalization,
architecture inference and strict full-model key/shape checks. For other inputs,
a stable parsed Torch version of at least 2.10.0 is required before calling
`torch.load(weights_only=True)`; older, unknown and prerelease versions are
rejected before decoding. This minimum addresses the documented advisories,
not all possible current or future vulnerabilities.

The Transformers AutoModel wrapper forces `use_safetensors=True` and
`local_files_only=True`, including when a caller requests otherwise. Tokenizer
and processor calls retain local-only loading. This is not an OS network sandbox
or protection against arbitrary trusted custom Python; review pinned code and
run actual inference without network access. Mocked contract tests bring the
local suite to **113 passing tests**. `tools/verify_tensor_loading.py` provides
a separate generated-tensor check for the real runtime; no external assets or
model construction are involved. The independent CPU converter now also passed
generated checkpoint conversion and cross-runtime readback. Actual source
payloads and strict model architecture/loading now passed, followed by one
synthetic inference; real-input accuracy and asynchronous operation remain
unvalidated.

### Generated-tensor verification completed on Jetson

On 2026-10-29, the existing Torch 2.2.2 image passed the real-reader probe.
The generated file was 4,504 bytes with four keys, including two names that
originally shared storage. FP32/BF16 values, shapes and dtypes survived; both
alias names remained. Malformed safetensors was rejected and old-Torch
checkpoint decoding was blocked, with no `torch.load` call. All 113 ordinary
tests also passed on Jetson. This proves the tested I/O boundary, not a working
converter, real checkpoint, base-model construction or navigation inference.

From the project root on Jetson, the repeatable probe command is:

```sh
sudo docker run --rm --runtime runc --network none --read-only \
  --user 1000:1000 --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 128 --memory 1g --cpus 2 \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  --mount "type=bind,src=$(pwd)/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$(pwd)/tools/verify_tensor_loading.py,dst=/workspace/verify_tensor_loading.py,readonly" \
  -e PYTHONPATH=/workspace/src -e PYTHONDONTWRITEBYTECODE=1 \
  --entrypoint python3.11 vln-b2-runtime:jp5 /workspace/verify_tensor_loading.py
```

`runc` avoids the NVIDIA runtime; `--network none` removes network access.
Read-only root/source mounts, an ordinary UID, dropped capabilities and
`no-new-privileges` restrict the process. CPU, memory, process and temporary-space
limits bound this small test. The mounts contain only reviewed application
source and the verifier, with no model cache, home directory, Docker socket,
sensors or credentials. No image build or new package was needed. The image ID,
source revision/hashes, report hash, limits and output are recorded privately
under ignored `local/access-setup` on Jetson. Preserve old failed attempts if a
repeat fails, and investigate rather than weakening the restrictions blindly.

## 6. Official conversion tools are not automatic approval

Hugging Face's [conversion guide](https://huggingface.co/docs/safetensors/en/convert-weights)
links an official converter. Its
[implementation](https://github.com/safetensors/safetensors/blob/main/bindings/python/convert.py)
still calls `torch.load` while reading the original file, so it must run in an
appropriately reviewed environment. Its deduplication policy can remove names
and needs review against our full-state strict loader.

The hosted Convert Space downloads, converts and opens a pull request to upload
the result. Do not submit restricted TIC-VLA artifacts to that workflow or use
its public-sharing behavior without applicable permission. The independent local
converter passed fixture and approved actual-checkpoint checks; it is not an
upstream-provided or author-certified converter. A converted weight retains applicable upstream conditions.

## 7. Storage and reproducibility

Fetch approved Hugging Face inputs with the official Hub client and pinned
allowlists into the standard `~/.cache/huggingface`. On the prepared Jetson,
that path already points to `/mnt/b2-research/VLN_B2/huggingface` on the SSD.
Do not manually populate cache internals, alter its cached source payloads or
copy large inputs into the public project. Mount selected cache snapshots
read-only when needed and preserve file-level hashes after acquisition.

Project-derived outputs belong under the ignored project `models/` directory,
with their local manifest and the command/recipe that produced them. Check its
actual filesystem and available capacity; if SSD placement is needed, make an
explicit dedicated-storage plan before writing rather than scattering copies.
Public documentation can retain revisions, expected hashes and the method;
weights, converted outputs and raw private permissions remain outside Git.

No cached source/weight or derived artifact has been published or redistributed
to another person by this work. Review allowed recipients before lab handover or image sharing. Follow
[the development guide](development.md) for experiment records and
[the status page](status.md) for what has actually passed.
