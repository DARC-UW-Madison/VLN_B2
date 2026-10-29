# Offline model checks on Jetson

[日本語](model-runtime.ja.md) · [Documentation](README.md) · [Inputs](model-artifacts.md) · [Conversion](checkpoint-conversion.md) · [Status](status.md)

This is a recorded model-load and numerical-inference check, not a B2 navigation
evaluation. It uses approved local assets, the existing Jetson GPU image and no
network. No camera, SDK control client or robot command sender participates.

## What passed on 2026-10-29

| Check | Result | Limit |
|---|---|---|
| Approved acquisition | 17 files, 3,827,163,803 bytes, official Hub client 0.24.7; pinned sizes/digests verified | Private research approval does not authorize redistribution |
| Actual CPU conversion | 1,324 names; 3,773,492,276-byte safetensors; source/readback verified | Source terms remain; do not use old GPU Torch to decode the original pickle |
| Strict GPU loading | 948,462,978 unique parameters; horizon 30; action layers 3; about 10.42 seconds | One load, excluding the preceding checksum; not inference timing |
| Synthetic inference | One generated 448×448 RGB image and zero velocities; 30 finite XY points; about 13.64 seconds | No real image, accuracy, stopping or control-rate validation |
| PyTorch allocation | Load peak 2,110,120,960 bytes; inference peak 2,624,592,384 bytes | GPU allocator only; excludes CPU RAM, driver allocations and total unified memory |
| Ordinary tests | 130 passed on Mac and Jetson | Unit/synthetic tests do not validate sensors, firmware or movement |

The synthetic run retained the upstream sampling configuration: maximum 200
new tokens, sampling enabled, temperature 0.7. No seed was fixed or recorded.
This is one bounded smoke, not a repeatable numerical benchmark or latency
average. Returned coordinates from an artificial scene establish no navigation
quality. A three-second predicted path taking 13.64 seconds in this synchronous
call cannot simply be connected to a walking loop. Asynchronous reasoning,
coherent cache metadata, fresh observations, watchdogs and stopping remain work.

The GPU image was the existing `vln-b2-runtime:jp5`:

```text
sha256:7f83ebeee829a67ed80fce0a4a738026fce84be6c025203ff24d28a62d43a44a
```

The actual CPU-converted input SHA256 is:

```text
2d2cab167ef723cf6644729128016ccbb0ab5b131a3aa561c7418a3318ea51e4
```

## Input, code and filesystem boundaries

The base snapshot is the approved InternVL revision in the Hub cache. Its five
custom Python files and config were read statically before execution: all
relative imports existed and no explicit network/subprocess/exec/eval/pickle or
independent weight-loading call was found in those five files. This review is
not a proof about every dependency. Optional FlashAttention/apex imports fall
back when absent; `use_flash_attn=False` selects eager attention. Config constructs
Qwen2ForCausalLM with hidden size 896 and 24 layers; a retained model-name string
mentioning 32B does not instantiate that larger architecture.

Our wrapper forces local loading and safetensors for AutoModel. The actual run
also had network isolation, an ordinary UID, dropped capabilities, no-new-privileges,
read-only application/base/converted/upstream inputs and writable temporary
module caches. The base-config and five custom-code hashes recorded after loading
match the approved acquisition. No home or credentials were mounted. No robot,
USB or profiling device mounts/groups were explicitly requested; the NVIDIA
runtime provides its vendor GPU interfaces.

Mount the **base repository cache directory**, containing both `snapshots` and
`blobs`, read-only. Mounting only the snapshot directory elsewhere breaks its
relative symlinks. This exposes only the base repository, not the original TIC
pickle in the separate dataset cache. Mount the derived tensor file separately.
`HF_MODULES_CACHE` must point to writable temporary storage: Transformers copies
reviewed custom Python there even when model data is read-only. This is not an
extra model download and does not modify the original snapshot.

## GPU access and failed first checks

A non-root container initially reported no CUDA device. Matched 2 GiB checks
without the device's video group reported no device; adding only that numeric
GID inside the container reported one available GPU. Host account membership
and device permissions were not changed. Do not substitute `--privileged`, a
whole `/dev` mount or root for this inspected access requirement.

The first load verifier then stopped **before model construction** because
Torch 2.2.2 memory statistics were reset before CUDA initialization. Explicit
CUDA initialization/device selection fixed the tool; strict load attempt 02
passed. That failure is not a checkpoint-compatibility result. All attempts,
commands, source/image hashes, reports and stderr are retained privately under
ignored `local/model-loading` and `local/model-inference` on Jetson.

## Reproduce the explicit load check

Run on Jetson from this project's root after acquisition, conversion and code
review, with the recorded image. This is not a Mac command. Choose a new output
directory for every attempt and verify private input hashes first. The following
foreground example loads the model only; it does not infer or move anything:

```sh
mkdir -m 700 local/model-check-01
sudo docker run --rm --pull never --runtime nvidia --network none --read-only \
  --user "$(id -u):$(id -g)" --group-add "$(stat -c '%g' /dev/nvmap)" \
  --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 128 --memory 24g --cpus 2 --tmpfs /tmp:rw,nosuid,nodev,size=256m \
  --mount "type=bind,src=$(pwd)/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$(pwd)/tools/verify_model_load.py,dst=/workspace/verify.py,readonly" \
  --mount "type=bind,src=$(readlink -f "$HOME/.cache/huggingface")/hub/models--OpenGVLab--InternVL3-1B,dst=/input/base-repo,readonly" \
  --mount "type=bind,src=$(readlink -f models/tic-vla-671de608-01/model.safetensors),dst=/input/weights/model.safetensors,readonly" \
  --mount "type=bind,src=$HOME/Developer/External/TIC-VLA,dst=/opt/upstream,readonly" \
  --mount "type=bind,src=$(pwd)/local/model-check-01,dst=/reports" \
  -e PYTHONPATH=/workspace/src -e HOME=/tmp/home \
  -e HF_HOME=/tmp/hf-home -e HF_MODULES_CACHE=/tmp/hf-modules \
  -e XDG_CACHE_HOME=/tmp/cache -e TORCH_HOME=/tmp/torch -e CUDA_CACHE_PATH=/tmp/cuda \
  -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e HF_DATASETS_OFFLINE=1 \
  -e HF_HUB_DISABLE_IMPLICIT_TOKEN=1 -e HF_HUB_DISABLE_TELEMETRY=1 \
  -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
  -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e TOKENIZERS_PARALLELISM=false \
  -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python3.11 vln-b2-runtime:jp5 \
  /workspace/verify.py --base-model /input/base-repo/snapshots/4415a3b810e636d11dfa86b0e9ba40bb00535aa8 \
  --checkpoint /input/weights/model.safetensors \
  --expected-sha256 2d2cab167ef723cf6644729128016ccbb0ab5b131a3aa561c7418a3318ea51e4 \
  --upstream-root /opt/upstream --report /reports/load-report.json
```

To explicitly run the generated-image smoke, use a different new report directory
and append `--synthetic-inference` to the verifier arguments. It writes a
synthetic PNG and private JSON with finite waypoints/timing. Default load mode
never creates an image or calls inference. An existing report fails before
runtime import; checkpoint-format/checksum/offline guards prevent invalid starts.

The recorded host runners supervised named containers, with 900 seconds for
load and 1,200 seconds for synthetic inference, stopping their own container on
timeout. The foreground example needs equivalent operator supervision; it is not
an autonomous service or robot watchdog. Runs used a 24 GiB container memory
limit, two CPUs, 128 processes and 256 MiB temporary space. Those limits do not
measure total device memory or prove real-time behavior.

## Next acceptance

Use real RGB and received robot state without commands, validate clocks/frames/
units/calibration, and profile individual model stages. Implement and test the
asynchronous path and cache-age gates before any sender. Confirm SDK authority,
remote-controller priority and actual stopping onsite. A successful synthetic
forward is a useful compatibility milestone, not permission to skip those steps.
