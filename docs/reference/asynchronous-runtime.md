# Asynchronous inference: references before workers

[日本語](asynchronous-runtime.ja.md) · [Documentation](../README.md) · [Runtime measurements](../records/model-runtime.md)

> Document type: **Reference**.

## Implemented boundary

`src/b2_tic_vla/semantic_cache.py` implements a thread-safe publication boundary
and pure metadata/input gates. It starts **no worker, service or background
process**, on Mac or Jetson. The separate experimental tools below add a bounded camera/model loop. A sender
and independent stopping mechanism remain unimplemented.

The recorded stage costs justify investigating separation of semantic reasoning
and current-image/action processing. They do not validate live concurrency,
navigation quality or a ten-second operating delay. Cache acceptance here means
metadata checks only; it is not authorization to move a robot.

Here, **shadow** means computing and logging predictions without sending them
to a robot. The semantic cache is the VLM's attention key/value tensors from the
complete image/instruction/reasoning conversation. The action decoder reads
those tensors alongside new visual features. It is temporary process/GPU memory,
not new model weights, a text-only answer or the disk-based Hugging Face cache.

## One cache, one reference observation

`Observation` binds an image, robot state and instruction. `begin()` returns a
request with that immutable observation. `publish()` stores the resulting opaque
payload, request/reference and completion time in one locked update. Starting
another request leaves the published reference unchanged. Superseded requests,
duplicate publication and requests outstanding across `reset()` cannot publish.
An instruction change rejects the previous cache immediately.

Image files must have unique immutable names; a path to an overwritten image
does not preserve an observation. The cache object transfers payload ownership
but cannot make arbitrary tensors immutable. Producers must not mutate published
tensors. A clone can establish independent storage; `detach()` alone shares it.
See the [Torch API](https://docs.pytorch.org/docs/2.2/generated/torch.Tensor.detach.html).

Consumers retain the selected snapshot and call `is_current()` again after model
computation. Reset/replacement can happen during GPU work. An actual sender needs
its own current-generation, expiry, authority and stop gates; this library does
not make an earlier returned context valid indefinitely.

## Three different times

All subtraction uses an established host monotonic clock, never an unconverted
camera/robot timestamp. The semantic reference is the latest image in the
semantic context, paired with its corresponding pose, not generation completion.

| Quantity | Definition |
|---|---|
| Semantic age for expiry | Decision time minus semantic-reference capture time |
| Model delay input | Current action-image capture time minus semantic-reference capture time |
| Observation/state freshness | Decision time minus each current sample time, with separate receipt checks |

`state_aligned_at` records the host-clock time represented by pose and velocity,
including a validated interpolation if necessary. A fresh packet receipt does
not establish a fresh sample. Verified image/state sample times must satisfy the
pair-skew limit. Receipt pairing is checked separately. Setting verification
flags is not clock synchronization; evidence must precede those flags.

Until capture/state clocks and poses are established, `select()` rejects normal
acceptance. Explicit `shadow_only=True` can return diagnostic context using
receipt-based delay/age when capture time is unknown. That timing is a **lower
bound**, clearly labelled, and never clears a physical command. Cache limits are
required explicit arguments; no default is presented as an approved B2 limit.

## State-vector frame contract

The inspected runtime uses `[vx, vy, yaw_rate, dx, dy, delay]`. Velocities are in
the current body frame. Displacement is cumulative movement expressed in the
**semantic reference's** body frame. The existing two-dimensional state supports
only a planar yaw transform:

$$
\Delta x=x_{now}-x_{ref},\quad \Delta y=y_{now}-y_{ref},
$$

$$
d_x=\cos(\psi_{ref})\Delta x+\sin(\psi_{ref})\Delta y,\quad
d_y=-\sin(\psi_{ref})\Delta x+\cos(\psi_{ref})\Delta y.
$$

Positions/displacements use metres; yaw uses radians, velocity m/s and yaw rate
rad/s. Current/reference poses need the same established world frame. Roll,
pitch and vertical motion are not represented; `pose_frame_verified` must include
evidence that the planar approximation is appropriate. B2 data has not established
that. Do not silently substitute current yaw for reference yaw or assume that
reported world velocity is already body velocity.

The reference convention is supported by the pinned
[Spot caller](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/DynaNav/behavior/spot_test_ticvla.py#L994-L1006)
and [training loader](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/data/policy_data.py#L354-L365).
Code review also identified a possible handoff mismatch between the caller's
start-frame history and a newly published cache inside `predict_async`; this
project attaches metadata to the actual payload instead of copying that history
heuristic. Training's floor/round delay indexing and future-sample offset still
need parity review before a research reproduction claim.

## Verification and remaining work

Unit tests cover in-flight request replacement, reset, original-reference age,
body projection, receipt/capture pairing, stale samples, changed instructions,
unknown timing and overflow. They use synthetic metadata, not a robot.

`tools/profile_model_runtime.py --cached-actions N` performs an explicitly requested numerical
cache-reuse experiment. It captures the full-conversation VLM forward output,
normalizes reviewed cache APIs, validates shapes/budget and clones the tensors.
It checks zero-delay agreement with synchronous output, then delayed decoding
and bytewise cache preservation. The default `N=0` does not perform this extra
experiment. This is separate from a live worker; actual run evidence belongs in
the [runtime guide](../records/model-runtime.md).

Next establish real state/time/frame inputs, investigate refresh gaps and verify
longer operation and failure recovery before a sender. The first B2 visit remains
network/state inspection without motor output, not immediate autonomous walking.

## Experiment record

Commands and measurements are in [the asynchronous experiment record](../records/async-shadow.md). For control timing, read [from predicted positions to velocity control](../explanations/control-loop.md).
