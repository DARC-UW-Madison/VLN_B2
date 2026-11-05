# Checkpoint conversion checks

[日本語](conversion-checks.ja.md) · [Records](README.md)

> Document type: **Record**. Evidence of performed configuration and checks, separate from current operating procedures.

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
