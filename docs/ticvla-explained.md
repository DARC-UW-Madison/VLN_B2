# Understanding TIC-VLA

[日本語](ticvla-explained.ja.md) · [Home](../README.md)

This is an independent explanation, not an experimental report. Sources were
inspected on 2026-10-22; default-branch code can change. Examples are illustrative.
The target robot is B2, without wheels.

## Task and components

VLA means vision, language, and action. Here the task is navigation: observations
and an instruction become a local motion plan. Walking control remains a
separate responsibility. A model checkpoint stores learned parameters; running
inference does not automatically update them.

The [project overview](https://ucla-mobility.github.io/TIC-VLA/) describes a slow
vision-language reasoner and a fast action expert sharing a vision encoder.
The fast branch receives a current image, robot state, cached semantic features,
and their timing context. It therefore has current visual evidence even while
new semantic reasoning is unfinished.

```text
Historical images + instruction -> VLM -> cached semantic features
                                                 |
Current image -> vision encoder -----------------+--> action expert
Robot state + cache age + motion since reference -+         |
                                                     local plan
                                                         |
                                               trajectory tracking
                                                         |
                                            robot walking controller
```

## Reasoning, features, and action prediction

InternVL3-1B is the upstream VLM. Images are encoded into numerical features;
language generation provides scene/task reasoning. An annotation such as
"a pedestrian is crossing" is generated content, not a verified physical fact.
The [VLM wrapper](https://github.com/ucla-mobility/TIC-VLA/blob/main/DynaNav/ticvla_vlm.py)
shows this image-and-language interface.

Transformer KV caches are numerical attention states. The inspected
[action model](https://github.com/ucla-mobility/TIC-VLA/blob/main/ticvla/models/ticvla.py)
uses the final layer's value features, projects them and current visual features,
and combines them with encoded state through cross-attention. Learned action
queries represent future output slots. This is a learned numerical prediction,
not a hand-written parser turning reasoning sentences into steering commands.

## Why time is an input

Suppose an image is captured at 10 s, its reasoning becomes available at 13 s,
and control uses that result at 14 s. The semantic information is 4 s old, not
1 s old. The robot may also have translated and turned during those 4 s.
Cache age and reference motion provide context for using the old information.
They do not reveal what an unseen pedestrian did afterward.

In an asynchronous loop, reuse the latest completed cache while computing its
replacement. Keep each cache paired with its own reference timestamp and pose.
The [runtime wrapper](https://github.com/ucla-mobility/TIC-VLA/blob/main/DynaNav/ticvla.py)
implements polling and background generation, with a blocking wait for the first
cache. Motion should remain disabled through initialization. One GPU can run
both branches, but asynchronous scheduling does not eliminate compute contention.

## Outputs and closed-loop execution

The paper and current implementation must be distinguished. The
[paper](https://arxiv.org/html/2602.02459v2) describes three-component motion
increments followed by integration. Current package code instantiates a
two-component head and returns future XY offsets from the current frame without
a cumulative sum. Its [training configuration](https://github.com/ucla-mobility/TIC-VLA/blob/main/configs/train_action.yaml)
uses 30 future slots. Pin the code and inspect the checkpoint before choosing a decoder.

A relative point such as (1.0 m, 0.2 m) is a location, not a velocity.
A tracking controller uses the local path to choose translation and yaw commands.
The [Spot simulation adapter](https://github.com/ucla-mobility/TIC-VLA/blob/main/DynaNav/behavior/spot_test_ticvla.py)
illustrates lookahead-based tracking and smoothing. Predicting a future path does
not require executing that whole path unchanged: observe again and replace the
near-term command. That feedback is what makes execution closed-loop.

## How the model is learned

1. **VLM supervision:** learn navigation reasoning and waypoint text from labeled
   recordings. The [annotation pipeline](https://github.com/ucla-mobility/TIC-VLA/blob/main/data/s03_batch_annotate.py)
   uses GPT-5 to prepare labels; that is separate from onboard inference.
2. **Imitation:** learn a motion prediction from demonstrated trajectories.
   The [dataset loader](https://github.com/ucla-mobility/TIC-VLA/blob/main/ticvla/data/policy_data.py)
   samples semantic delays up to 10 s while retaining the current action image.
   The [trainer](https://github.com/ucla-mobility/TIC-VLA/blob/main/ticvla/training/train.py)
   freezes the VLM and compares predicted XY points with targets using Smooth L1.
3. **Reinforcement learning:** improve action behavior through simulated outcomes,
   using PPO. The [RL implementation](https://github.com/ucla-mobility/TIC-VLA/blob/main/rl/fine_tuning/train_rl.py)
   trains selected action-expert parameters and a training-time value estimator.
   Its [policy definition](https://github.com/ucla-mobility/TIC-VLA/blob/main/rl/fine_tuning/ticvla.py)
   currently freezes the VLM and updates only the final action cross-attention block. The
   [reward definition](https://github.com/ucla-mobility/TIC-VLA/blob/main/rl/env/rewards.py)
   rewards arrival/progress and penalizes collisions and unsuitable speed.

Imitation observes demonstrations; a deployed policy encounters the consequences
of its own deviations. Closed-loop training addresses that difference. Labels
and simulation may use future or privileged information during training; that
does not make those observations available to the deployed policy.
Ordinary deployment uses the learned weights without continuing PPO on the B2.

The paper includes a heading offset in its latency interface; the inspected
package action input instead uses velocities, XY displacement and delay without
a separate heading-offset scalar. Preserve this distinction when reproducing it.

## Evaluation and B2 integration

DynaNav is an evaluation/training environment, not a process that must run on
the robot. It provides repeatable dynamic navigation tasks. A reported success
rate applies to its task definition and tested hardware; it is not a guarantee
of collision-free operation or successful B2 transfer.

Our integration work is to supply timestamped observations/state, maintain
consistent cache metadata, run the compatible model, convert its output into
bounded B2 commands, and verify stopping and operator control. Camera geometry,
body clearance, tracking response and compute latency need measurement.
Depth, LiDAR, SLAM or an independent obstacle monitor may support the surrounding
system; they are not interchangeable with the model's RGB/state inputs.

See [architecture](architecture.md) for the proposed adapter and
[development](development.md) for staged validation. No B2 inference or motion
has been demonstrated in this repository.
