# From predicted positions to continuous robot control

[日本語](control-loop.ja.md) · [Model inputs and outputs](ticvla-explained.md) · [Documentation](../README.md)

> Document type: **Explanation**. Numerical examples illustrate the computation, not approved B2 motion settings. Implementation details are in [the architecture reference](../reference/architecture.md); measured timings belong to [the inference records](../records/model-runtime.md) and [the asynchronous experiment](../records/async-shadow.md).

## 1. Distinguish three computations

A navigation model predicts where to go. A path-tracking controller converts
those positions into a requested forward/lateral speed and turning rate. The
robot's existing locomotion controller turns such requests into leg motion,
using its own sensors and actuator control. These are separate computations:

```text
Image + instruction + measured motion
        -> navigation model -> future positions
        -> path tracker -> forward/lateral speed + turning rate
        -> B2 motion interface -> existing locomotion controller -> joints
```

A neural-network inference can run on a CPU; a GPU accelerates the large parallel
operations of models such as our VLM. Network handling and many control
computations do not require a large GPU. The choice of an Intel platform PC
therefore does not mean it must run TIC-VLA or cannot run a small learned model.
The manufacturer's actual walking algorithm and where it executes cannot be
identified from the brand of the CPU or a successful API request. Our large-model
computation is assigned to the external Jetson; the B2 locomotion implementation
is retained rather than replaced.

## 2. What a predicted metre means

The released package used here returns 30 XY positions relative to the current
robot frame. A frame specifies the origin and directions of coordinates: in
the inspected convention, x points forward and y left. Thus `(1.0, 0.2)` means
a proposed position 1 m forward and 0.2 m left, not a velocity. Successive points
share that origin; they are not increments to add to the preceding point.

The training targets are built from recorded future positions. That training
provides a numerical distance convention. An RGB image alone does not measure
the distance to every object geometrically. The model learns visual/motion
relationships from its data; camera height, lens, viewpoint and a new robot can
make its metric predictions inaccurate. The current RGB path does not use ZED
depth to correct the model's scale.

Consequently, a graph axis labelled metres means the interpretation of the
numbers, not a measured guarantee of accuracy. Evaluate predictions against
measured scene distances and motion before introducing scale corrections or
using them as destinations. Resizing the plot on screen does not alter metres.
The [pinned package](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/models/ticvla.py)
returns relative XY directly; the [training loader](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/data/policy_data.py)
constructs the corresponding targets. Package conventions take precedence over
assuming that every formulation in the paper is identical to this checkpoint.

The adapter labels its 30 slots at 0.1-second intervals from the inspected
implementation. Those labels do not measure B2's travel time. A time-following
controller would need to track that timing explicitly; our candidate tracker
uses spatial lookahead instead and does not enforce waypoint arrival times.

## 3. What “assumed stationary” supplies to the model

State means numbers describing motion, not an operating-system state. The
inspected model receives current forward velocity, lateral velocity and turning
rate, together with movement and elapsed time since its semantic reference image:

| Input | Physical meaning | Unit |
|---|---|---|
| `vx`, `vy` | Current body-forward/body-left velocity | m/s |
| `yaw_rate` | Current rate of heading change | rad/s |
| `dx`, `dy` | Movement since the reference image, expressed in that reference frame | m |
| `delay` | Current action-image time minus semantic-reference image time | s |

The camera demo's assumed-stationary mode supplies zero velocity/displacement
instead of reading state from B2. Its synchronous call uses the same image for
semantic and action input, so their model delay input is zero. This input mode
does not measure or guarantee that the robot is actually stationary.

Replacing assumed values means implementing a real data path: receive robot
velocity/pose, establish their units, axes and timestamps, pair the state with
the camera image, and calculate displacement from the stored reference pose.
A successful independent state subscription does not perform that integration.
The reference pose must belong to the actual semantic result in use, even while
a newer result is being computed.

## 4. How a path becomes speed and steering

A high-level command requests `(vx, vy, yaw_rate)`. It does not request a number
of steps. A path tracker selects a point ahead of the robot and steers toward
it. Our existing offline tracker uses a simple curvature rule often called
pure pursuit. For a selected point `(x, y)`:

$$
\kappa=\frac{2y}{x^2+y^2},\qquad \omega=v\kappa.
$$

Here x/y are metres, curvature kappa is inverse metres, forward speed v is m/s,
and turning rate omega is rad/s. Positive y gives a left turn in this convention.
For a hypothetical target `(1.0, 0.2)`, curvature is approximately 0.385/m.
Choosing v = 0.10 m/s gives omega approximately 0.0385 rad/s before smoothing.
The speed is an explicit controller choice, not a number automatically inferred
by dividing one path coordinate by the model's entire inference time.

In the current `PathTracker`, the configured cruise speed supplies v. A turning
limit can reduce it on tight curves; acceleration limits restrict changes from
the previous candidate command. Sideways velocity is always zero. These are
implementation choices, not a general limitation of B2. The tracker does not
implement arrival-time tracking, goal stopping, obstacle clearance or a speed
error controller. It computes a candidate only and has no network sender.

## 5. Where feedback enters

Feedback means measuring what happened and using it to revise the next request.
A future navigation loop must repeatedly observe the latest image and robot
motion, compute a path in the updated robot frame, and calculate another speed
request. After the robot turns, an old body-relative point cannot be reused as
though the body had not moved. It must be replaced by a new plan or transformed
using measured motion and the original reference.

There are two levels of feedback:

- Navigation feedback uses camera/state observations to revise the path and
  direction. A tracking error can be the target's lateral offset or heading
  error. A speed controller could also compare requested and measured speed.
- Locomotion feedback is handled by the robot's existing walking system as it
  controls body/joint behavior. Its internal algorithm is not implemented here.

Our offline tracker checks state validity/freshness but does **not** currently
calculate a requested-minus-measured-speed correction. Its acceleration limiter
uses the previous candidate command, not the actual measured acceleration.
It would be inaccurate to call that a completed B2 feedback controller.
Independent request expiry and verified robot stopping are also required: a
zero value in Python cannot cancel an old request unless it is actually sent
and handled by the receiver.

## 6. What happens during a ten-second inference

A single blocking loop that captures an image, waits ten seconds for the whole
model, and only then calculates a command cannot provide frequent reactions.
If it holds an old movement request during that wait, the robot may keep moving
without an updated decision. If it explicitly stops during every wait, it
produces stop-and-go behavior. Neither is continuous reactive navigation.
The current synchronous image demo is not a commissioned movement loop.

TIC-VLA's intended asynchronous design separates two jobs. *Asynchronous* means
one job need not wait for the other to finish:

```text
Slow job: image/instruction -> VLM reasoning -> saved semantic features
Fast job: latest image + latest measured state + saved features + their age
          -> action expert -> new path -> tracker -> bounded command
```

A VLM is the image/language part of the model. Its saved semantic features are
numerical arrays representing the interpreted scene/task, not just its printed
text. The fast action expert uses those arrays with a new observation. While
a new slow job runs, the most recent completed features remain available.
Features carry the time and pose of their input so that the action expert can
account for their age and the robot's intervening movement. Reusing features
is different from replaying an old path without looking at the latest image.

For example, once features for image time 0 are available, action calculations
for times 10.0 and 10.2 can use different current images and motion estimates
with those same features. Their delay inputs differ. When features from a later
reference finish, both the feature arrays and their reference metadata change
together. Before the first result exists, or after a result becomes unusable,
the controller needs an explicit waiting/stopping policy.

## 7. Why asynchronous execution is not yet a timing guarantee

The slow and fast jobs still share a GPU. Running them in separate threads does
not guarantee that the fast job finishes on time. Measure image acquisition,
state delivery, scheduling, feature extraction, action decoding and command
handling as a complete loop. A lower-level command/expiry process must not block
behind language generation.

The [paper](https://arxiv.org/html/2602.02459v2) evaluates an asynchronous policy
on different hardware. Its reported policy rate is not a measured Jetson rate.
A shadow test computes and records predictions without commanding the robot,
allowing timing behavior to be inspected first. See [the experiment record](../records/async-shadow.md)
and [current status](../status.md) for measurements and unconnected components.

Before continuous motion, require current image/state delivery, useful path
updates at a measured cadence, defined behavior when features expire, and an
independent command deadline. Do not make ten-second-old data valid by simply
raising a freshness threshold. “The model loads” and “the control loop meets
its timing requirements” are different completion conditions.
