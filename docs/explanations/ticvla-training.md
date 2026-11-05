# How TIC-VLA learns navigation

[日本語](ticvla-training.ja.md) · [Documentation](../README.md) · [Model computation](ticvla-explained.md) · [B2 control](control-loop.md)

> Document type: **Explanation**. This chapter explains how weights are obtained and why training includes delayed observations. It does not instruct the reader to start training, download datasets or send laboratory recordings to a cloud service. All small numerical examples are constructed for explanation.

The [model chapter](ticvla-explained.md) follows inference from inputs to outputs. Here we ask where that behavior comes from. There are three distinct questions: how a model learns to describe navigation, how it learns a numeric path, and how it learns from the consequences of following its own predictions. Combining those questions into “the model was trained” hides the reason for TIC-VLA's stages.

## 1. Learning changes parameters; inference does not

Suppose a tiny predictor is $\hat y=wx$, with one parameter $w$. For input $x=2$ and desired output $y=1$, let $w=0.1$. It predicts 0.2. Define an error, or **loss**, $\mathcal L=\frac12(\hat y-y)^2$. Here the loss is 0.32.

The **gradient** tells how the loss changes as a parameter changes. In this example $\partial\mathcal L/\partial w=(wx-y)x=-1.6$. A **gradient-descent** update with learning rate $\eta=0.1$ gives $w\leftarrow w-\eta\nabla\mathcal L=0.26$. The next prediction is 0.52, closer to 1. The learning rate sets the size of this adjustment.

A neural network has many parameters rather than one. **Backpropagation** computes gradients through its layers using the chain rule. An **optimizer** uses those gradients to update selected parameters. TIC-VLA's supervised code uses AdamW, which maintains running gradient statistics and also applies weight decay. It is not simply the one-parameter update above, but the same distinction between prediction, error and update remains.

A **batch** contains multiple training examples used together. An **epoch** is a pass through the selected training data. A **checkpoint** saves learned weights and sometimes optimizer state and training progress. During normal Jetson inference we load weights and calculate outputs without this loss/backpropagation/update cycle. The robot does not gradually learn B2 dynamics merely by running a demo.

## 2. What is one demonstration example?

A **demonstration** records an expert's behavior. It can contain a human-operated robot's RGB images and measured poses, or observations and trajectories generated during simulated operation. The desired future trajectory supplies a target for learning; low-level motor torques are not required for learning relative navigation positions.

For a current observation time $t$, imagine a record containing:

| Part | Example role |
|---|---|
| Past images | What was visible before $t$ |
| Current image | What was visible at $t$ |
| Robot poses | Position and orientation at the recorded times |
| Future poses | Where the demonstration went after $t$ |
| Instruction | A route description consistent with that episode |
| Reasoning annotation | A short description of relevant situation, agents and next plan |

A **pose** combines position and orientation. To express a future position in the current robot frame, subtract the current world position and rotate into the current heading:

```math
p_{\mathrm{target},i}^{B_t}
=R(\psi_t)^\mathsf{T}\big(p_{t+i}^{W}-p_t^{W}\big),\qquad
R(\psi)=\begin{bmatrix}
\cos\psi&-\sin\psi \\
\sin\psi&\cos\psi
\end{bmatrix}.
```

$W$ denotes the trajectory's world frame, $B_t$ the robot frame at time $t$, $p$ a position in metres and $\psi$ a heading in radians. If a robot faces world +y and subsequently moves 1 m in world +y, its target is 1 m forward, not 1 m left. The rotation is what makes examples collected under different headings comparable.

The pinned [JSON generator](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/data/s01_batch_json_generation.py) distinguishes future offsets from history: future offsets refer to the current pose, whereas history entries can refer to successive previous poses. Treating both lists as the same kind of increments changes the labels.

The [policy dataset](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/data/policy_data.py) extracts up to 30 XY future offsets. Its compact velocity estimate uses the first future displacement divided by 0.1 s, with orientation differences for yaw rate. This is a training-data construction method. At deployment we need measured current motion and cannot ask for the next true pose before acting. Sensor noise and this estimator/deployment difference are reasons to validate B2 inputs.

## 3. Who writes the instructions and reasoning targets?

Raw navigation recordings do not necessarily include a natural-language description of what the operator intended. **Annotation** adds labels to such recordings. The upstream [data pipeline](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/README.md) separates creation of time windows, instructions and reasoning labels. The released data sources include SCAND, GND and DynaNav; this does not mean all training observations are Go2 or B2 observations.

The annotation code can use GPT-5 as a teacher to produce text from selected images and trajectory context. Because annotation happens after recording, the teacher may inspect future observations and the actual route. That helps describe what happened. The deployed student must predict from its permitted past/current inputs and cannot access those future images.

This distinction is easiest to see in a turn. The recording shows that the operator ultimately entered a left doorway. An annotation process can describe that route using the completed recording. During training the student sees the route instruction and available observations, and learns to produce corresponding outputs. During inference no completed future recording is available.

The pinned [VLM dataset](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/data/vlm_data.py#L238-L316) constructs two target forms: explanatory text followed by waypoint text, and waypoint text alone. The explanatory form includes explicit reasoning/answer markers. Those are supervised output formats; they are not proof that an annotation's explanation or a later generated explanation is correct.

Annotation quality matters. Inconsistent instructions, wrong poses, wrong unit conversion or labels referring to the wrong images teach inconsistent behavior. More annotation is not automatically better. A research extension should inspect label quality, avoid overlap between training and test episodes, and retain consent and dataset usage conditions for actual recordings.

Nothing in our prepared inference runtime needs an online GPT-5 request. Downloading a trained checkpoint and applying it locally differs from using a cloud model to prepare new training labels. This project has not run the annotation pipeline on private laboratory recordings.

## 4. Stage one: teach navigation language

**Supervised fine-tuning**, or **SFT**, adjusts a pretrained model using examples with desired answers. The pretrained InternVL component already supplies image/language representations. Navigation SFT adapts its responses to route instructions, relevant scene descriptions and waypoint text.

For a target sequence $y_1,\ldots,y_N$, a standard language loss is:

$$
\mathcal L_{\mathrm{text}}=-\frac1N\sum_{j=1}^{N}
\log p_{\phi}(y_j\mid y_{<j},\text{images},\text{instruction}).
$$

$\phi$ denotes trainable language parameters. $p_\phi$ is the probability assigned to the next correct token. $y_{<j}$ denotes preceding target tokens. During training those preceding tokens can be supplied from the correct answer, a technique called **teacher forcing**. During generation the model instead conditions on tokens it has produced itself.

If a target token receives probability 0.8, its negative log probability is about 0.223. At probability 0.2 the error is about 1.609. This pushes training toward assigning higher probability to the target tokens. A number written as text is still learned through its tokens at this stage; the loss is not a direct measurement of centimetres of trajectory error.

**Freezing** a component means excluding its parameters from updates, not skipping its computation. The pinned [`TICVLA_VLM`](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/models/vlm.py) fixes the vision component for this stage and trains the language side. The [training module](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/training/train.py) implements its loss and optimizer selection.

After this stage a model may produce useful navigation text and internal semantic features. It still needs an action expert trained to turn those features and current measurements into a numeric near-term path. Fluent language alone does not train that second mapping.

## 5. Stage two: imitate paths while guidance is delayed

**Imitation learning** trains a policy to match examples of desired behavior. A **policy** is a function from observations to actions. Here the trainable action expert predicts positions matching the demonstrated near-term route, while the VLM is fixed.

The important preparation is deliberately pairing different times. Suppose the current training image and target path belong to 20 s, but a sampled semantic reference is 16 s. The action expert receives current appearance/motion at 20 s, features associated with 16 s, a four-second delay and displacement since 16 s. The desired path still starts at the current 20 s pose. It must not reproduce the future path starting from 16 s.

The [policy dataset](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/data/policy_data.py#L285-L380) samples delays up to 10 seconds, limited by available history. It chooses delayed images/annotations and displacement information while retaining current action targets. It assumes a particular recording cadence; that indexing is a dataset convention, not a general-purpose live sensor synchronizer.

The **Smooth L1 loss** compares predicted and target numerical coordinates. With threshold $\beta>0$, its scalar form is:

```math
\ell_\beta(e)=
\begin{cases}
\frac{e^2}{2\beta}, & |e|<\beta, \\
|e|-\frac{\beta}{2}, & |e|\ge\beta.
\end{cases}
```

$e=\hat p-p$ is coordinate error in the numeric representation used for training. With $\beta=1$, error 0.2 gives loss 0.02; error 2 gives loss 1.5. Small errors have a quadratic penalty and larger errors a linear penalty. The optimizer reduces their mean over the selected batch and coordinates. A low average loss is useful evidence but does not itself prove collision-free behavior.

The pinned [`TICVLAActionLightningModule`](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/training/train.py#L140-L218) compares the **direct XY predictions** to target offsets and optimizes only action-expert parameters. It also reports average and final displacement error. Do not insert the paper's motion-increment integration into this source path: its output convention differs, as [the model chapter](ticvla-explained.md) explains.

Why train with delay instead of adding a `delay` number only at deployment? An extra number has no inherent operational meaning to the network. It must encounter examples showing what should change when old guidance is used after motion. Training teaches that association. Conversely, delay exposure over one range does not establish that arbitrary larger delays work on B2.

## 6. Stage three: learn from following the policy's own predictions

An imitation dataset mostly contains states visited by the expert. If a learned policy deviates, the next image may differ from every corresponding training image. Its own mistake changes the next input. This **distribution shift** is a central difference between predicting recorded paths and controlling a moving system.

**Reinforcement learning**, or **RL**, evaluates consequences of actions in an environment. A **rollout** is a sequence of observations, actions and rewards generated by running a policy. A **reward** scores an outcome; it is not another motor command. DynaNav is the research's simulation/evaluation setting, and the released [RL workflow](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/rl/README.md) uses an Isaac Lab environment for such interaction. A simulator supplies rendered observations, movement and contacts without using a physical B2.

For intuition, an educational reward could favor progress toward a goal, add a goal-reaching reward, penalize collisions and discourage undesirable speed. An agent that stops forever avoids collisions but makes no progress, so collision count alone cannot measure navigation quality. Exact reward terms and weights belong to the chosen environment; this example is not a proposed B2 reward configuration.

The released [`train_rl.py`](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/rl/fine_tuning/train_rl.py) collects interaction with asynchronously updated semantic features, delay metadata and displacement. It retains the semantic features associated with each collected step, so optimization can evaluate the same context instead of substituting a later cache.

The code uses **PPO**, Proximal Policy Optimization. Its **actor** selects actions; a **critic**, or value network, estimates expected future accumulated reward to help assess outcomes. A positive **advantage** means an action's outcome was better than the baseline estimate. PPO compares new and previous action probabilities and clips their ratio in its objective to discourage overly large updates from the same data. This is an optimization method, not a guarantee of safe physical behavior.

For example, if an action with positive advantage becomes much more probable after an update, clipping stops rewarding an arbitrarily large increase through that term. The policy is still tested by interacting again. Probability, reward and trajectory error are different quantities and should not be conflated.

The pinned [RL policy](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/rl/fine_tuning/ticvla.py#L318-L396) freezes the VLM and, within the action expert, trains the final cross-attention block. The [value model](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/rl/fine_tuning/model.py) and [PPO implementation](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/rl/fine_tuning/ppo.py) have their own trainable parameters. “RL fine-tunes the policy” does not mean that every weight of every component is updated.

A critic can use training-only information under a particular research design. That does not entitle the deployed actor to use an unavailable true goal coordinate or future observation. Inspect actual actor inputs separately from critic inputs. We do not infer the downloaded checkpoint's exact RL provenance from the existence of these scripts.

## 7. Why training, simulation and inference need different resources

Training keeps intermediate activations, gradients and optimizer state in addition to weights. Simulation also renders images and computes physical interactions. These operations can require much more memory and compute than loading a model for inference.

Training multiple simulated worlds **in parallel** is different from concurrently running a semantic worker and an action worker on one robot. The former collects many independent experiences per update; the latter handles different update rates in one observation/control loop. Both use the word “parallel,” but they solve different scheduling problems.

The public [VLM configuration](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/configs/train_vlm.yaml) and [action configuration](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/configs/train_action.yaml) are executable release examples. Their batch sizes and learning rates are not proof of the downloaded checkpoint's training recipe or identical to all paper settings. Reproducing a result requires a pinned recipe, data split, initialization, random seeds, software and evaluation, not merely a script named `train.py`.

Our present plan reuses learned weights on the external Jetson. It does not put a training server on the Mac or a training simulator inside B2. If research later needs B2-specific fine-tuning, select its data, objectives, resource budget and evaluation as a separate experiment.

## 8. What can be concluded from published and local results?

Several types of evidence answer different questions:

| Evidence | Question it answers | Question it does not answer |
|---|---|---|
| Training loss | How well the selected targets are fitted | Whether a physical robot completes a route |
| Recorded-data displacement error | Whether predicted points match held-out demonstrations | Whether mistakes are recovered in a closed loop |
| Simulated closed-loop evaluation | How the whole policy behaves in those simulated tasks | How every real camera and robot behaves |
| Published Go2 trials | Whether the authors' system worked under the stated conditions | Whether our different B2 integration is complete |
| Our strict load and camera demo | Whether reviewed assets execute and return finite points | Whether predictions are metrically correct or movement is controlled |

**Closed loop** means actions change the environment and the next observation is used to decide again. **Open-loop evaluation** predicts from a fixed recording without letting predictions change the next image. A good open-loop path can still fail after a small real deviation, which explains why the distinction matters for both learning and testing.

An **ablation** removes or changes one element to test its contribution. For this research, the useful questions include whether blocking reasoning hurts behavior, whether numeric semantic features help more than sparse textual targets, whether delay/motion inputs matter, and whether RL improves closed-loop operation. Such comparisons are stronger evidence for a mechanism than an attractive individual video, but remain bounded by their setup. See [the paper's experiments](https://arxiv.org/html/2602.02459v2#S4).

To read those results, distinguish the reported metrics:

| Metric | Meaning | Interpretation limit |
|---|---|---|
| NE, navigation error | Final distance from the goal, in metres | A small distance alone does not describe contacts along the route |
| SR, success rate | Fraction of episodes satisfying the task's success criterion | Depends on the goal threshold, time limit and intervention rules |
| SPL, success weighted by path length | Success discounted when the traveled route exceeds a shortest reference route | Requires evaluation reference geometry; does not imply the policy receives a map |
| CR, collision rate | Fraction of episodes with collisions under the benchmark definition | A stationary failing agent can have a low collision rate |

For intuition, a common SPL term is $S\,l/\max(l,p)$, where $S$ is 1 for success and 0 otherwise, $l$ is reference shortest length and $p$ is traveled length. A successful 4 m route with a 2 m shortest reference scores 0.5; a failed route scores zero. These are constructed examples, not paper episodes.

The paper's Table 1 reports SR 55.29% for its full simulated setting, compared with 32.94% for its synchronous variant. This supports examining the consequences of blocking reasoning in that benchmark. It also means substantial failures remain. The real-world RTX 4060 result of 85% comes from a different set of tasks and trials; it cannot be read as an improvement from 55.29% on the same test or as a B2 success probability.

The simulated policy has current observations while semantic updates arrive more slowly. Thus “10 Hz action, 0.5 Hz reasoning” describes different jobs, not a claim that the language model generates a full answer every tenth of a second. Ablations change components under particular operating conditions; a result must be read with its timing and control setup, not only its percentage.

For B2, changes in viewpoint, body size, achievable speed, motion estimation and communication can each produce a new distribution shift. The first response is to measure and locate it, not automatically to retrain. Incorrect axis conversion needs a software correction; a camera-dependent prediction bias may need calibration, a changed observation setup, or ultimately new training data. These are different hypotheses with different experiments.

## 9. What has this project actually reproduced?

We have prepared reviewed local code and weights, verified conversion/loading, and run image-to-path inference. We have not reproduced the complete supervised dataset, annotation process, all training stages, paper benchmark or Go2 deployment. The [model records](../records/model-runtime.md) and [current status](../status.md) identify executed checks.

The immediate B2 work is therefore **integration and evaluation of an existing model**, not training a B2 policy from scratch. Establish real state/image correspondence, record command-free predictions, compare output with the physical scene, and verify the control interface separately. If these measurements show a systematic limitation that requires learning, they supply a concrete research question and data requirements for the next experiment.

Continue with [the path-to-B2 control chapter](control-loop.md), which follows numerical predictions through tracking, communication, the existing walking controller and feedback.
