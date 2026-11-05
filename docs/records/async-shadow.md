# Asynchronous camera inference experiment

[日本語](async-shadow.ja.md) · [Records](README.md)

> Document type: **Record**. Results at source `c261a5e`; not evidence of continuous control.

## Bounded camera/model experiment

`tools/record_camera_stream.py` owns a new private directory, writes unique JPEGs
and per-frame metadata, then atomically replaces `latest.json` only after the
complete image and manifest exist. Published images become read-only. It retains
source SDK time separately; unknown capture time stays null and unverified.
Its capture window is at most 60 seconds and target rate at most 10 images/s.
Missed slots are skipped rather than replayed as a burst. Native SDK/device hangs
still require an external process deadline.

`tools/observe_async.py` reads that directory **read-only** and checks schema,
clock, bounded regular files, paths, immutable basenames and SHA256 before use.
It loads the reviewed safetensors/base model offline, keeps at most one semantic
request in a thread worker, and uses the published cache for new images on the
main thread. Semantic and action work use separate CUDA streams with stream-local
completion waits. This permits an overlap experiment; it does not guarantee GPU
kernel overlap, thread safety for other model versions, or a maximum latency.
Model parameters are shared read-only and cache tensors are cloned before
publication. No state subscriber, tracker, sender or robot client is constructed.

The worker invokes the synchronous package predictor to obtain a complete
semantic cache; that call also computes an unused synchronous action. The
embedded predictor's description still describes that synchronous component.
The outer experimental tool supplies concurrency; it is not upstream DynaNav
reproduction or a multi-image-history implementation.

The observer explicitly requires `--assumed-stationary --shadow-only` and a
positive `--max-semantic-age`. It uses zero assumed motion, not real state.
Receipt-based age remains a lower bound. Before **and after** each action it
checks freshness/cache identity and discards invalid results. Input receipts
older than 0.5 s are skipped; this diagnostic setting is not an approved B2
threshold. Duration begins after model load. Shutdown resets the cache, starts
no new requests, waits for the last GPU call and discards a late completion.
An external supervisor must stop only the two experiment containers after
180 seconds; `Future.cancel()` cannot interrupt native GPU work.

### Commands inside the prepared containers

These are explicit **container-internal** commands, not host-venv commands or
Mac setup. Prepare two separate ordinary-UID, read-only-root NVIDIA containers
with `--network none`, dropped capabilities and no-new-privileges. Use the
[camera guide](../reference/camera-runtime.md) for its private binding, read-only SDK, exact
current USB/video nodes and dedicated writable calibration directory. The model
container gets reviewed source/base repository/derived safetensors read-only,
offline Hub settings, a temporary module cache and its own writable report
mount. It needs no USB devices or credentials. Mount project `src` and `tools`
read-only, and set `PYTHONPATH=/workspace/src:/workspace/tools` for the observer.

Only the camera writes `/observations`; the observer mounts that same host SSD
directory read-only. The parent exists, but `frames` must be new. Start the
producer, wait for a complete `latest.json`, then start the observer. Use the
same host monotonic clock in both containers. Do not replay old manifests as
live observations. Every attempt needs new output paths; never overwrite data.

```sh
python3.11 /workspace/record_camera_stream.py \
  --output-dir /observations/frames --settings-dir /camera-settings \
  --duration 55 --fps 5
```

```sh
python3.11 /workspace/tools/observe_async.py \
  --observations /observations/frames \
  --base-model /input/base-repo/snapshots/4415a3b810e636d11dfa86b0e9ba40bb00535aa8 \
  --checkpoint /input/model.safetensors \
  --expected-sha256 2d2cab167ef723cf6644729128016ccbb0ab5b131a3aa561c7418a3318ea51e4 \
  --upstream-root /opt/upstream --report-dir /reports/run \
  --duration 25 --max-semantic-age 20 --assumed-stationary --shadow-only
```

### Measured result and gaps

The first target run at source `c261a5e` passed with the existing GPU image
`sha256:7f83ebeee829a67ed80fce0a4a738026fce84be6c025203ff24d28a62d43a44a`.
Camera and model containers had 4 GiB/24 GiB memory limits, two CPUs each,
128-process limits and 256 MiB temporary space. No host service or Mac background
job was created. Both containers exited successfully and were removed.

| Observation | Result |
|---|---|
| Camera publication | 275 immutable JPEGs in a 55-second capture window; 39,668,458 image bytes |
| Model loading | 9.354 s, before the observation window |
| Observer | 126 distinct latest observations in about 25 s; this intentionally does not consume every saved image |
| Semantic requests | Two completed; first published after 12.659 s; second completed after shutdown and was discarded |
| Accepted shadow actions | 35, all while the next semantic request was in flight; each returned 30 finite XY points |
| Action wall time | Minimum 0.131 s, median 0.156 s, maximum 0.283 s; includes current image/features/decoder and stream wait |
| Skipped observations | 65 before a cache existed; 26 after the 20-second experimental semantic age limit |
| Semantic age during accepted actions | Receipt-based lower bound about 13.05–19.98 s |
| Errors / shutdown | Zero errors; one late semantic result discarded after reset |

These counts expose substantial startup/refresh gaps. Dividing the fastest
action time into one second does **not** yield an end-to-end controller rate.
The 20-second limit only made this diagnostic observable; no navigation-quality
or physical-delay acceptance follows. Camera capture-clock alignment, actual
robot motion, mounted field of view, clearance, continuous control availability
and physical stopping remain unverified.

Private invocation/source/image records and event/summary JSON live under
`local/async-shadow/attempt-01`; images/per-frame records live in the dedicated
SSD observations area. They are excluded from Git. Unit tests cover malformed or
changed manifests, unknown timing, publication failures, stale/late actions,
worker failure and shutdown, in addition to the cache module tests. Mac and
Jetson pass all 162 ordinary tests. These tests and this short run do not
establish long-duration reliability or command authority.
