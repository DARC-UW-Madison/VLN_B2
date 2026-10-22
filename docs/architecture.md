# Architecture

[日本語](architecture.ja.md) · [Home](../README.md)

This is the proposed integration, not an implemented system.

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
