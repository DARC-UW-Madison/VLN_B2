# Local checkpoint conversion

[日本語](checkpoint-conversion.ja.md) · [Documentation](README.md) · [Artifact plan](model-artifacts.md)

This guide records independent tooling, generated-fixture checks and the
subsequent approved actual-checkpoint conversion. Acquisition requires exact-file
approval and terms review; the recorded 17-file plan was approved on 2026-10-29.
Conversion does not remove source restrictions or authorize public distribution.
GPU loading and the single synthetic inference are separate runtime checks.

## Why CPU conversion is separate

The existing Jetson GPU runtime uses Torch 2.2.2 against CUDA 11.4. Its checkpoint
deserializer is blocked in our adapter. The new converter uses Torch 2.15.0+cpu
in a separate container venv. It needs no compatible new CUDA driver because
it decodes and copies CPU tensors rather than running navigation inference.
The host interpreter and GPU environment remain intact.

A build constructs the filesystem and installs tools. A conversion run starts
a separate process using those tools. A built image does not start a robot,
download model weights or automatically convert a file.

## Build inputs and boundaries

`deploy/checkpoint-converter.Dockerfile` reuses the inspected local Python-stage
image by its full image ID. `deploy/converter-requirements.lock` pins all 12
packages and official wheel hashes for CPython 3.11, aarch64 and glibc 2.31.
CPU Torch is an explicit official CPU URL, avoiding CUDA dependencies from the
ordinary PyPI package. The inspected wheels total 197,569,238 bytes; installed
size, base layers and build cache are additional. Dependency terms and notices
are recorded in [third-party materials](../THIRD_PARTY.md).

From the project root on Jetson, after reviewing that base image and storage:

```sh
sudo env DOCKER_BUILDKIT=0 docker build --pull=false \
  --build-arg BASE_IMAGE="$(sudo docker image inspect vln-b2-python:jp5 --format '{{.Id}}')" \
  -f deploy/checkpoint-converter.Dockerfile -t vln-b2-converter:cpu-v1 .
```

The existing builder works without adding a host buildx plugin. The initial
BuildKit attempt failed before installation because that plugin was absent;
retain its log. Build-time Internet access is used only for the pinned software.
The installer requires hashes, binary wheels, `pip check` and CPU-only Torch
checks, and retains its install report/freeze. Preserve the resulting image ID.
Neither a matching filename nor a successful import validates model conversion.

## Generated-fixture acceptance

Run the following in a new ignored workspace. Use a new numbered directory for
repeats; do not delete or overwrite a previous attempt to conceal a failure.

```sh
mkdir -m 700 local/converter-fixture-01
sudo docker run --rm --runtime runc --network none --read-only \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 128 --memory 2g --cpus 2 --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  --mount "type=bind,src=$(pwd)/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$(pwd)/tools/verify_checkpoint_conversion.py,dst=/workspace/probe.py,readonly" \
  --mount "type=bind,src=$(pwd)/local/converter-fixture-01,dst=/work" \
  -e PYTHONPATH=/workspace/src --entrypoint python \
  vln-b2-converter:cpu-v1 /workspace/probe.py --workspace /work/fixture
```

The probe writes its own small Torch checkpoint, converts it, and verifies
BF16 shared aliases, transposed tensors, scalars, empty tensors, NaN payloads
and signed-zero bytes. Unsupported serialized metadata must fail without
unrestricted pickle retry. It does not exercise the published model checkpoint.

Then verify that the generated safetensors output can be read by the older
GPU image. This check also uses CPU tensors and deliberately exposes no GPU:

```sh
sudo docker run --rm --runtime runc --network none --read-only \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 128 --memory 2g --cpus 2 --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  --mount "type=bind,src=$(pwd)/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$(pwd)/tools/verify_checkpoint_conversion.py,dst=/workspace/probe.py,readonly" \
  --mount "type=bind,src=$(pwd)/local/converter-fixture-01,dst=/work,readonly" \
  -e PYTHONPATH=/workspace/src -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python3.11 \
  vln-b2-runtime:jp5 /workspace/probe.py --verify-only /work/fixture/converted
```

`--runtime runc` avoids GPU integration. Both runs have no network, an ordinary
UID, dropped capabilities, no-new-privileges, a read-only root, and CPU/memory/
process/temporary-space limits. Only reviewed source, the probe and the fixture
are mounted; the second run mounts the fixture read-only. No home, robot devices,
credentials, model cache or Docker socket is exposed. Two GiB is a fixture-test
limit, not an estimate for the real checkpoint or model inference.

## Recorded fixture result

On 2026-10-29, attempt 02 built successfully with all hashes verified, `pip check`
and CPU-only imports passing. Attempt 01 stopped before installation because
buildx was absent; it remains recorded. Image `vln-b2-converter:cpu-v1` is:

```text
sha256:fbb182b51c0e6aee011dc43c4b7f1405493f9b17113531ea2d30a330525dc98c
```

Its logical size is 11,073,891,434 bytes, including the shared existing Python
base; this is not the amount downloaded or additional disk use. It contains
Torch 2.15.0+cpu, safetensors 0.8.0 and NumPy 2.4.6. The CPU fixture probe and
old-Torch readback both exited 0. Six original names, BF16 aliases, scalar/empty/
transposed tensors, NaN and signed-zero bytes were retained. Unsupported globals
were rejected without unrestricted retry. The self-generated source was 2,799
bytes and the tensor output 512 bytes; discarded training metadata makes this
size comparison unsuitable for estimating actual model output. These fixture
checks did not acquire, construct or infer a real model. At that stage, all
**121 tests** passed on Mac and Jetson.

The 90-second probes used no network/GPU, ordinary UID, read-only root and source,
no capabilities, no-new-privileges, 2 GiB RAM, two CPUs, 128 processes and 64 MiB
temporary space. Fixture reports, image/source hashes and resource provenance
are private under ignored `local/cpu-converter-build/verification-01`; build
attempts are retained alongside it. Public source contains neither fixtures nor
raw machine records. These fixture checks did not test the actual checkpoint;
the subsequent approved result is recorded below.

## Approved actual-checkpoint result

The operator-approved TIC-VLA source checkpoint was acquired through the official
Hub client, hash-verified and converted offline on 2026-10-29. All 1,324 original
names and their values/dtypes/shapes passed readback; architecture metadata
agreed with horizon 30 and three action layers. The original was 1,938,501,547
bytes and the derived tensor file 3,773,492,276 bytes. Materializing aliases makes
this output larger; it is not evidence of extra unique model parameters.

The immutable source stays in the standard Hub cache. The derived file and
manifest are private SSD data under `models/tic-vla-671de608-01`, through the
ignored project symlink to `/mnt/b2-research/VLN_B2/models`. The actual run used
CPU-only Torch 2.15.0+cpu, no network/devices/home/credentials, an ordinary UID,
read-only source, two CPUs, a 32 GiB memory limit and a 1,200-second supervisor.
It completed successfully. These limits are not measured peak RAM.

The derived output passed subsequent strict GPU loading and a synthetic-image
inference; those results, image/file hashes, GPU access and limits are described
in [offline model checks](model-runtime.md). Original and derived payloads remain
outside Git and on Jetson, with applicable source terms intact.

## Actual conversion contract

After separate approval, mount exactly the approved checkpoint read-only and a
new dedicated project output area writable. Run without network or devices, with
reviewed memory/CPU/time limits and the pinned CPU image ID. The module entry
point is `python -m b2_tic_vla.checkpoint_conversion`; its CLI requires expected
SHA256, public repository/type, pinned revision and a new output directory.
No command to acquire or convert the unapproved model is prescribed here.

1. Reject an existing output, invalid provenance, nonregular input, excessive
   source size or a checksum mismatch before decoding. The default source limit
   is 3 GiB. Hash the source again after decoding; use an immutable input mount.
2. Require CPU-only Torch and the adapter's supported stable version gate.
   Decode with CPU placement and `weights_only=True`. Do not add globals or retry
   unrestricted pickle when published metadata is unsupported.
3. Accept a nonempty plain tensor mapping or Lightning `state_dict`. Require
   supported dense CPU dtypes/layouts and a bounded key count/name length. The
   default raw tensor budget is 4 GiB, counting every alias name separately.
4. Retain every original key and value. Materialize separate contiguous copies
   for shared aliases; do not remove names, normalize prefixes or change dtypes.
   This may make output larger than the source checkpoint.
5. Write `model.safetensors`, read it back, and compare every name, dtype, shape
   and SHA256 of raw tensor bytes. Byte comparisons retain NaN and signed-zero
   distinctions. Allow at most 128 MiB of serialized header beyond the raw budget.
6. Write `manifest.json` last as the completion marker: original source identity,
   digests/sizes, tool hash, software versions, bounds, alias strategy, per-tensor
   hashes and the two positive-integer architecture fields when present. Other
   training metadata is not copied. A failed output without a verified manifest
   is incomplete and must not be used for inference.

The manifest records consistency and provenance supplied by the reviewed caller;
it is not a signed authenticity certificate or a redistribution permission.
Actual full-state compatibility, base-model code and recorded-image inference
remain separate acceptance steps. Converted model outputs and manifests belong
outside Git under approved storage; the small generated probe workspace is not
the real model store.
