# Local checkpoint conversion

[日本語](checkpoint-conversion.ja.md) · [Documentation](../README.md) · [Artifact plan](model-artifacts.md)

> Document type: **Reference**.

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
are recorded in [third-party materials](../../THIRD_PARTY.md).

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

See the separate [record](../records/conversion-checks.md) for the result and history.

## Approved actual-checkpoint result

See the separate [record](../records/conversion-checks.md) for the result and history.

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
