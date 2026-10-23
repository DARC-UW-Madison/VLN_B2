# Architecture

[日本語](architecture.ja.md) · [Home](../README.md)

The full live system below is a proposed integration. The repository now
implements observation adapters, synchronous offline inference, and candidate
tracking for offline evaluation. It does not implement the asynchronous live
cache or motor output. See [the current code boundary](#current-code-boundary).

## Problem and approach

A vision-language model (VLM) interprets images and instructions. A navigation
policy converts that context into motion. If inference takes time, its context
describes an older scene. TIC-VLA gives the action policy current observations
alongside delayed semantic features and timing information. See the
[paper, version 2](https://arxiv.org/html/2602.02459v2#S3).

The B2 integration will retain the robot's existing walking controller. It will
evaluate navigation above that controller rather than replace joint control.
ROS 2 is an option, not a prerequisite selected by this document.

```text
RGB images + robot state + instruction
                 |
     Timestamped observation history
          |                  |
     VLM worker        Current observation
          |                  |
 Semantic cache              |
 + capture time              |
 + reference pose            |
          |                  |
          +------+-----------+
                 |
           Action policy
                 |
   Relative plan -> trajectory -> velocity command
                 |
     Command limits and expiry checks
                 |
       B2 high-level motion interface
                 |
        Existing walking controller
```

## Timing and coordinate frames

Every image and state sample needs a capture timestamp. Pair each completed
semantic cache with the exact observation timestamp and reference pose used to
produce it. The age of that cache is `current_time - reference_capture_time`;
it includes inference time and time spent reusing the result. Do not measure
only the duration of the most recent inference call.

Use a monotonic clock for elapsed time on one host. If sensors and inference run
on different hosts, establish clock alignment before subtracting timestamps.
Publish the cache and its metadata as one consistent update. Starting another
inference must not change the reference pose of the cache still being used.

Record each interface's frame, axis directions, units, quaternion ordering, and
timestamp meaning. Position in a world frame is not interchangeable with body
velocity. Document the transform between the camera and robot body. Validate
transforms using stationary, straight-motion, and rotation recordings before
connecting the output to the robot.

## Model and robot boundary

The inspected [upstream inference implementation](https://github.com/ucla-mobility/TIC-VLA/blob/main/DynaNav/ticvla.py)
instantiates a two-component action head. Package inference returns future XY
offsets from the current frame without cumulative summation, whereas the paper
describes three-component increments and integration. Its asynchronous entry point accepts six
state values and reduces them to five before adding delay. This interface must
be checked against a pinned revision and checkpoint before integration; paper
notation alone does not define a compatible input tensor.

Interpret the trajectory according to the pinned code and checkpoint. Do not
apply cumulative summation to positions already relative to the current frame.
Then use a validated tracking controller to obtain translational and yaw
velocities. Do not pass pose increments directly as velocity commands.
The [B2 SDK client](https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/unitree_sdk2py/b2/sport/sport_client.py)
exposes `Move(vx, vy, vyaw)` and `StopMove()`. API availability is not evidence
that a particular robot firmware accepts or safely executes a command.

## Execution states

The initial implementation should distinguish observation-only operation,
ready, explicitly enabled motion, and stopped/faulted states. In observation-only
operation, no motion commands are sent. Inference initialization and errors must
not authorize movement.

Check image/state freshness separately from semantic-cache age: delayed semantic
features are expected, but stale live observations can invalidate control.
Reject non-finite or malformed output. Bound velocity and acceleration, expire
old commands, and require explicit re-enabling after a fault. Determine actual
thresholds through measured latency and laboratory operating limits.

A software stop depends on communication and the robot controller. It is not an
independent emergency stop. Verify operator override and the robot's behavior
on command loss before any model-driven movement.

## Transfer to B2

Camera height and field of view, body footprint, tracking response, and stopping
distance may differ from the published platform. These are research variables,
not parameters that can be inferred from the model name. Begin with the
[staged validation procedure](development.md) and report observed failures
before deciding whether adaptation or additional training is necessary.

## Current code boundary

The available flows are deliberately independent so that failures can be localized:

```text
inspect_target.py -> installed-system inventory (no SDK imports)
ZedCamera -> JPEG + receipt time + unverified source time
UnitreeStateReader -> finite state + receipt time + unverified frames
                  -> observation.json + frame.jpg
                  -> TicVlaPredictor -> offline future XY plan (no motor output)
synthetic replay fixture -> PathTracker -> candidate velocity + acceptance reason
```

| File | Responsibility |
|---|---|
| `tools/inspect_target.py` | Standalone Python 3.8+ inventory; no install or robot messages |
| `src/b2_tic_vla/types.py` | Explicit image, state, plan, and velocity contracts |
| `src/b2_tic_vla/hardware.py` | Lazy ZED capture and Unitree state subscriptions only |
| `src/b2_tic_vla/recording.py` | Validated portable observation manifests; no overwrite |
| `src/b2_tic_vla/inference.py` | Strict local-file loading and synchronous upstream package calls |
| `src/b2_tic_vla/control.py` | Pure candidate tracking with freshness, frame, and limit checks |
| `src/b2_tic_vla/cli.py` | Separate probe, recording, replay, and inference commands |
| `examples/` | Synthetic data, unvalidated limits, and blank onsite notes |
| `tests/` | Unit and command tests with synthetic data and fake vendor libraries |
| `deploy/Dockerfile` | Source-only template requiring an explicitly matched base image |

The new predictor calls `ticvla.models.ticvla.TICVLA.predict`, not the asynchronous
DynaNav entry point. It supplies `[vx, vy, yaw_rate, 0, 0]` and zero delay: the
last two values represent relative displacement, which is zero for this
synchronous smoke test. It expects shape `[1, horizon, 2]` and preserves the
returned relative XY positions without cumulative summation. Output times use
an assumed 0.1-second waypoint interval from the inspected implementation; exact
revision/checkpoint compatibility and physical timing remain to be validated.
The CLI currently supplies one image as both the current and semantic reference
observation. It does not reproduce a multi-image asynchronous observation history.

`PathTracker` is a basic forward-only lookahead controller for evaluation. For a
selected target `(x, y)` in the current body frame, it calculates curvature
`2*y/(x*x+y*y)`, proposes `yaw_rate = vx*curvature`, reduces forward speed to meet
the yaw bound, and limits changes in speed and yaw rate. Lateral velocity is
always zero. Missing, stale, nonfinite, mismatched, or unsupported data produces
a zero candidate with a rejection reason. The synthetic fixture checks straight,
curved, and stale-image cases. The tracker neither checks obstacle clearance nor
implements a stop-distance model, goal completion, or time-optimal tracking.
It is not validated B2 navigation.

Host receipt times are monotonic, while vendor clock values remain separate
metadata. A verified capture timestamp must be converted into the same host
clock before use. With unverified capture time, even an otherwise accepted
candidate is marked `shadow_only_capture_time_unknown`. A fresh receipt cannot
prove a camera frame is newly exposed. Replayed records start a new timing
interval and cannot become fresh live inputs by relabeling recorded timestamps.

No implemented module creates `SportClient`, calls `Move`, or publishes motor
commands. Consequently, software rejection means a zero **candidate**, not a
physical stop. Future motion integration needs validated clock/frame transforms,
atomic asynchronous cache/reference metadata, control ownership, an independent
command-expiry path, verified receiver behavior, and operator override. Follow
[onsite preparation](onsite.md) to obtain the missing evidence before that work.
