# Understanding TIC-VLA: from an image to movement

[日本語](ticvla-explained.ja.md) · [Documentation](../README.md) · [Camera demo](../how-to/live-camera-demo.md) · [Network](../how-to/field-network.md)

> Document type: **Explanation**.

Read this chapter before interpreting a path as a request to move B2. It explains
the computation, displayed outputs, and engineering between prediction and
walking. Numerical examples are invented teaching examples. Implementation
observations refer to source revision `9fa6f8b66b9e121d5df5df071297bba8e5353ebb`
and our adapter. The [paper, version 2](https://arxiv.org/html/2602.02459v2),
[project overview](https://ucla-mobility.github.io/TIC-VLA/), released package and
our B2 integration have different evidence boundaries.

## 1. Navigation and walking are different computations

Consider “Continue along the corridor and pass the person on the left.”
Navigation interprets the destination and scene, then chooses a local path.
Locomotion makes a particular robot follow velocity requests while maintaining
balance and coordinating joints. TIC-VLA supplies navigation predictions. B2's
existing locomotion handles the latter task through its supported interface.
Installing weights does not connect these tasks.

A **model** is a computation with learned numerical parameters. A **checkpoint**
stores those parameters; source code defines how to use them. **Inference** runs
that computation on inputs, normally leaving the parameters unchanged. Upstream
code, InternVL assets and the converted TIC-VLA checkpoint are separate from our
camera, recording, display and eventual control adapters. See [runtime flow](../reference/runtime-flow.md).

The external Jetson runs camera/model software. The onboard Intel development
PC accesses the native robot network. Mac provides editing, SSH and optional
display. These names do not establish where locomotion services are hosted;
[measured wiring](../how-to/field-network.md) records actual reachability.

## 2. Follow one observation through the model

An RGB image is an array of pixel values. A vision encoder turns image patches
into numerical vectors called visual tokens: learned features, not an obstacle
map. A tokenizer turns instructions into token IDs. The language component
processes image features and instructions to produce text and internal attention
features. A separate action expert predicts a local path.

```text
Image history + instruction --> slow VLM --> generated text
                                  |
                          cached numerical features
                                  |
Current RGB --> vision encoder ----+--> fast action expert --> future XY points
Current velocity + elapsed motion -+                               |
Semantic age ---------------------+                         path tracker
                                                                 |
                                                        bounded velocity request
                                                                 |
                                                       existing B2 locomotion
```

The two image inputs have different roles. Historical images provide context for
the slow VLM. A recent image lets the action expert see changes that occurred
while the VLM was busy. A shared encoder does not imply simultaneous exposures
or instantaneous computation. The simple camera demo supplies **one saved image
to both roles** and assumes zero robot velocity/displacement. It does not supply
measured B2 motion or the paper's complete historical observation sequence.

The paper's example uses four semantic images across a nine-second window,
three seconds apart. Relative to the semantic reference they are at -9, -6,
-3 and 0 seconds. When the result is delayed, that last image is itself older
than the action branch's current image. Our one-image demo omits that history.

## 3. What reasoning and KV cache mean here

The term is **chain of thought (CoT)**. TIC-VLA can generate navigation-related
text before its textual waypoint targets. The released
[prediction implementation](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/models/ticvla.py)
asks for relevant visual evidence and targets at 3, 6 and 9 seconds. The returned
text helps inspect what the model says about an input. It can be wrong,
incomplete, or dominated by coordinates. A fluent explanation is not measured
obstacle geometry or a complete account of internal computation.

An illustrative response might describe a person on the right and suggest a
leftward target. That sentence is a teaching example, not a recorded result.
We display actual returned text without translating, rewriting or inventing it.

Transformers also maintain numerical attention states called **keys and values**,
or a **KV cache**. These arrays contain more than the visible sentence. The
attention operation compares a query with keys to weight a combination of
values: a learned way of selecting relevant numerical context. This is not a
human-readable list of detected objects.
The inspected action expert rearranges and projects the final layer's **value**
features, combining them with current visual features and encoded scalar state
through attention. Learned action queries represent future output slots.
There is no rule such as “if the sentence contains left, turn left.”

The synchronous package generates a response, then processes the image/text
conversation to obtain features for action decoding. Saving the returned text
adds no second language-generation request. It does not make our synchronous
demo an asynchronous control system.

## 4. Two waypoint outputs must not be confused

| Output | Meaning in the inspected package | Display/use |
|---|---|---|
| VLM response | Scene/task description and possible `(x, y, theta)` targets at 3/6/9 s, anchored to the semantic observation | Generated VLM response panel |
| Action tensor | 30 predicted `(x, y)` positions relative to the current frame | Blue top-view path and coordinate table |
| Tracker result | Candidate `(vx, vy, yaw_rate)` computed from a selected point | Offline tools; not transmitted to B2 |

The blue line comes from the action tensor, not a parser of response text.
Its shape `[1, 30, 2]` means one sample, thirty positions, two axes. Strict loading
established 30 slots and three action layers. The package associates slots with
0.1-second spacing; our adapter labels them 0.1 through 3.0 seconds. These are
prediction labels, not measured B2 execution times.

The thirtieth point is a short-horizon endpoint, not necessarily the instruction's
final destination. In a future closed loop, a tracker would issue a short-lived
request, observe again and replace its near-term request with a newer plan.
Thirty predicted points do not mean “execute the entire line without observing.”

The paper describes a more general action/trajectory formulation and six action
layers; the inspected package/checkpoint use two-coordinate positions and three
layers. The paper's latency interface includes heading change, while the package
state has no separate heading-change scalar. Do not change a decoder to match a
figure without checking training targets and checkpoint compatibility.

## 5. Read distance and axes before direction

The package convention is **x forward, y left**, with lengths interpreted in
metres and yaw in radians. `(1.0, 0.2)` means a position one metre forward and
0.2 metre left of the prediction reference. It is not a speed, pixel coordinate,
GPS coordinate, or increment from the preceding blue point.

Positions `(0.1, 0)`, `(0.2, 0)`, `(0.3, 0)` end at 0.3 m forward. Cumulative
summation would incorrectly end at 0.6 m. The inspected
[dataset target construction](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/data/policy_data.py)
uses offsets from the current reference, and the package returns positions
directly. Our adapter performs no cumulative sum.

Endpoint distance is $\sqrt{x^2+y^2}$. Set $p_0=(0,0)$ and sum
$\sum_i\|p_i-p_{i-1}\|$ for the sampled polyline length. These answer different
questions: straight-line endpoint distance versus distance along displayed
samples. Neither measures actual robot travel. The viewer displays both,
endpoint coordinates and the final assumed sample time. The plot auto-scales;
a longer line on screen alone does not imply more metres.

Textual `theta` targets are separate from the action tensor's two columns.
There is no third action column carrying a B2 turning request.

## 6. A coordinate frame needs a physical definition

A **frame** defines an origin and axis directions. A body frame moves with the
robot; a local world/odometry frame tracks its motion. A camera optical frame
often uses different axes. Writing `base_link` into a report does not establish
that a camera mount or SDK field matches that definition.

For a point in a verified planar body frame $B$, its world coordinate is

$$p_W = p_{WB} + R(\psi)p_B, \qquad
R(\psi)=\begin{bmatrix}\cos\psi&-\sin\psi\\\sin\psi&\cos\psi\end{bmatrix}.$$

Here $p_{WB}$ is robot reference position in metres and $\psi$ its yaw in radians.
At 90-degree yaw, one metre body-forward points along world +y. An old
body-relative path cannot be reused as if the robot had not turned. Each plan
needs its own reference pose and time.

Camera **intrinsics** describe projection, including focal lengths and lens
distortion. **Extrinsics** describe mounting translation and orientation.
Overlaying a ground path on a photograph requires transforming its points into
the camera frame and projecting with calibrated intrinsics, accounting for
resolution and crop. The current photo and top view are separate; no calibrated
overlay exists. A learned path is not automatically an optical-frame point cloud:
first establish its learned reference, then apply the appropriate transform.

Camera height, tilt, field of view, body size and gait vary across platforms.
Matching axis signs does not establish metric accuracy or transfer to B2. A metre
label is a model convention; physical distance and clearance need measurement.

## 7. Why time and elapsed motion are inputs

Suppose semantic images are anchored at 10 s, their result completes at 13 s,
and it is used at 14 s. Observation age is **4 s**, not 1 s. The robot may have
moved during those four seconds. New pixels, current velocity, semantic age and
elapsed motion help the action expert use an old representation.

The package encodes six scalars: `[vx, vy, yaw_rate, dx, dy, delay]`. The first
three describe current motion; `dx, dy` describe displacement since the semantic
reference in the training convention; delay is in seconds. They are not global
goal coordinates. Our synchronous adapter supplies `[vx, vy, yaw_rate, 0, 0]`
and delay 0. The camera demo also uses zero velocity: an explicit stationary
observation experiment, not measured motion.

Keep cache features, image time and reference pose together. Publish a completed
cache atomically while action uses the previous completed cache. Do not relabel
completion time as exposure time. Age and motion cannot reveal unseen changes;
current observation and bounded failure handling remain necessary.
The [asynchronous shadow experiment](../reference/asynchronous-runtime.md) exercised cache
handling with assumed stationary state and exposed availability gaps. Onboard
state reception was tested separately and is not integrated into this loop.
Monotonic clocks on different computers are not automatically comparable;
exposure, delivery delay and clock relationships need validation.

## Connecting prediction to control

[From positions to continuous control](control-loop.md) explains metric scale, state inputs, velocity/steering, feedback and inference delays in order.

## Training differs from use

The paper describes three stages:

1. **Language supervision.** Offline annotation uses GPT-5 to create navigation
   instructions and structured reasoning/targets from recordings, including
   future information. This is dataset preparation, not a cloud call from our
   Jetson. Language training learns the target token sequence with cross-entropy;
   the vision backbone is frozen during this stage.
2. **Imitation learning.** The released [supervised trainer](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/training/train.py)
   freezes the VLM and learns the action expert from demonstrated positions,
   using Smooth L1 loss. The dataset samples semantic delays up to 10 seconds,
   retaining current visual input. This teaches use of delayed guidance rather
   than only perfectly aligned observations.
3. **Reinforcement learning.** The [PPO training loop](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/rl/fine_tuning/train_rl.py)
   evaluates simulated closed-loop consequences and updates selected parameters.
   The inspected [RL policy](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/rl/fine_tuning/ticvla.py)
   freezes the VLM and trains the final action-attention block. A training-time
   value estimator helps optimize returns; it is not a B2 navigation command.
   Rewards account for progress/arrival, collision and speed. This addresses
   states encountered after the policy's own deviations from demonstrations.

Future recordings or privileged information can create training targets;
deployment cannot request future real camera frames. Reading training code does
not establish that this particular downloaded checkpoint completed every paper
stage. Our work has verified loading/inference, not reproduced that training.

Cross-entropy measures error in the predicted next-token probabilities. Smooth
L1 measures numerical position error, behaving quadratically near zero and
linearly for larger errors. PPO means Proximal Policy Optimization: a reinforcement
learning method that improves expected reward while constraining policy changes.
These are learning objectives/methods, not commands executed during inference.

The released [training data preparation](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/data/policy_data.py)
explains position offsets and state conventions. Inspecting data construction
matters as much as inspecting inference. Installing a checkpoint does not train
it on B2, and ordinary inference does not silently continue reinforcement
learning. DynaNav is a simulator/training/evaluation system, not a required
process on the deployed robot.
