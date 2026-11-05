# How TIC-VLA turns images and instructions into a path

[日本語](ticvla-explained.ja.md) · [Documentation](../README.md) · [How it learns](ticvla-training.md) · [From a path to B2 control](control-loop.md)

> Document type: **Explanation**. This chapter follows the computation inside the model. It is not a launch procedure. Use the [camera tutorial](../how-to/live-camera-demo.md) to execute the prepared demo, and [status](../status.md) for current implementation boundaries.

Consider “Follow the passage and use the door on the left.” A camera supplies a picture, but a picture contains neither a motor command nor a list of coordinates. Software must extract useful visual information, relate it to the instruction, decide a nearby path, and convert that path into movement requests. This chapter explains the model calculation. The [control chapter](control-loop.md) continues through communication and physical movement.

Read the sections in order the first time. The examples use invented observations and numbers to expose the calculations; they are not recorded model responses or validated B2 settings.

## 1. What is installed when we install a model?

A **model** is a parameterized numerical function. Its **parameters**, also called weights, are arrays of numbers adjusted during training. At execution time the program combines those numbers with input arrays to produce output arrays. It does not search a collection of stored videos for the next command.

A simple layer computes $z=Wx+b$: input vector $x$ is multiplied by a learned matrix $W$ and shifted by a learned vector $b$. Real models repeat such operations with nonlinear functions and mechanisms for relating different parts of the input. The matrices encode learned behavior; the Python code defines how to apply them. Neither weights alone nor Python alone supplies the complete system.

| Piece | What it supplies | What it does not supply |
|---|---|---|
| Upstream TIC-VLA Python | Model structure, image/text preparation and prediction functions | B2 wiring or a commissioned movement controller |
| InternVL3-1B base assets | Pretrained image/language components, configuration and vocabulary | The complete navigation adaptation by themselves |
| TIC-VLA checkpoint | Learned navigation weights loaded into that structure | Camera drivers, timestamps or robot authentication |
| This repository's adapter | Verified local loading, input/output checks, records and display | A completed autonomous B2 runtime |
| Camera and robot interfaces | Actual observations and, separately, movement requests | Learned instruction understanding |

A **checkpoint** stores learned state. **Inference** applies that state to new inputs; it normally does not change the weights. Loading the checkpoint once and repeatedly inferring are different costs. Training is a separate program that computes errors and changes weights, explained in [the learning chapter](ticvla-training.md).

The [artifact reference](../reference/model-artifacts.md) identifies the local assets. Keeping vendor code and weights outside this public repository does not disconnect it from TIC-VLA: the adapter imports the separately prepared code and loads the separately prepared weights at runtime.

## 2. The problem addressed by the paper

**Vision-language navigation** means moving according to language while observing the world. **VLM**, vision-language model, processes images and text together. **VLA**, vision-language-action model, adds a learned action-producing component. Here “action” refers to navigation outputs; it does not imply direct control of every joint.

Language reasoning can take seconds. Meanwhile the robot and pedestrians move. Even a correct interpretation of a picture can become stale before use. Putting reasoning in another thread removes one software wait but does not tell the action model that its guidance describes an older situation.

TIC-VLA gives the action component the latest image and motion, an older numerical representation from the VLM, and explicit information about its age and intervening movement. It trains with delayed guidance too. This connection between execution and learning is the central mechanism. See the [paper, Sections 3.2–3.3](https://arxiv.org/html/2602.02459v2#S3).

For example, semantic guidance might indicate that the useful door is to the left. Three seconds later the robot may have passed it. New image input, elapsed time and measured displacement help interpret the old guidance. They cannot guarantee correct interpretation of every unseen change or recover a current picture that never arrived.

## 3. What enters one prediction?

The **semantic reference observation** is used by the slower VLM. The **current action observation** is used by the faster action component. Their timestamps can differ even though they use the same camera and share the same vision encoder.

| Input | Meaning | Representation |
|---|---|---|
| Instruction | Which route or destination to follow | Text |
| Semantic images | Scene at the reasoning reference, with earlier context if available | Ordered RGB images |
| Current image | Scene for this action update | One RGB image |
| Current motion | How the robot is moving now | Forward/lateral velocity and yaw rate |
| Motion since the semantic reference | Movement while reasoning was delayed | Relative displacement; exact fields depend on implementation |
| Age of semantic guidance | Age of its reference observation | Seconds |

**RGB** stores red, green and blue intensities at each pixel. A 1920 by 1080 picture contains 1920 × 1080 × 3 values before preprocessing. It has no explicit “door” field. A depth image instead stores estimated distance per pixel; LiDAR supplies ranges or a point cloud. The current adapter takes RGB, not ZED depth or Livox point clouds. Installing an RGB-D camera does not add depth to a model's inputs automatically.

Imagine a semantic reference at 50 s and images at 41, 44, 47 and 50 s. If the semantic result completes at 53 s, its latest image is already three seconds old. The action side at 53 s should use its own latest image. History supplies temporal context; it does not require waiting nine seconds between every action.

The simple demo supplies one saved image to both inputs and explicitly assumes zero motion. Its same-image delay is zero, while wall-clock computation time is nonzero. A stationary demonstration can inspect outputs this way; a moving robot cannot interpret this as a live zero-latency observation.

## 4. From pixels to visual features

An **encoder** converts an input into another numerical representation. A **feature vector** is a list of numbers whose learned pattern is useful for a later calculation. A **token** is one position in a sequence of representations; it need not be an English word.

The image path performs these operations:

1. Decode image bytes into RGB pixels.
2. Resize/preprocess the image into the pretrained encoder's expected layout. The inspected prediction path uses a 448-pixel input size; the camera need not capture at 448 pixels.
3. Convert intensities to the normalized numerical range expected during training.
4. Apply the learned vision network, producing visual tokens.
5. Pass the tokens to the language component or action component for the relevant observation.

The implementation is in the pinned [vision utilities](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/utils/vision.py) and [VLM loader](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/models/vlm.py). Resizing and normalization prepare numbers; they are not explicit obstacle detection or ground-distance measurement.

A **tensor** is a multidimensional numerical array. For example, `[1, L, H]` can mean one input example, $L$ visual tokens, and $H$ numbers per token. Dimensions describe arrangement, not whether a person was recognized correctly. The action expert projects visual features into a shared 512-dimensional representation before combining them with other inputs.

The same encoder weights can process two different images. Sharing weights does not make the exposures simultaneous or one feature extraction free. The scheduler still allocates GPU time to actual operations.

## 5. From images and an instruction to a VLM response

A **tokenizer** maps text to token identifiers using a fixed vocabulary. A token may be a word fragment, punctuation or a special marker. Each identifier selects a learned vector. Image markers specify where visual representations belong in the sequence; they do not send a JPEG to a motor controller.

The language network mixes representations of instruction tokens, image tokens and preceding response tokens. It predicts a probability distribution for the next response token, selects one according to a generation rule, appends it, and repeats. This is **autoregressive generation**. A long explanation can require many sequential operations even on a GPU.

The pinned [`TICVLA.predict`](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/models/ticvla.py#L509-L681) builds a navigation prompt, generates a response, and runs the full image/text conversation through the VLM to obtain numerical state for the action expert. The second pass extracts a representation of the completed conversation; it is not a second independent navigation answer.

The prompt asks for navigation evidence and textual targets at 3, 6 and 9 seconds, in $(x,y,\theta)$ format: two offsets and a heading angle. The response may describe a doorway, a person's apparent motion or task progress. This is model-generated text, not a verified object detector result or a complete transcript of internal computation.

**Chain of thought**, abbreviated **CoT**, names the explanatory text associated with this training/prompting format. Our display's “Generated VLM response” field shows the actual returned text unchanged. It helps compare what the model said with the image; a persuasive sentence does not establish that the metric path is correct.

The pinned predictor enables sampling during generation. Repeated runs on the same image can therefore differ. Save the actual response and input for reproducibility; rewriting an explanation afterwards would conceal what was produced.

## 6. What passes from the VLM to the action expert?

The main interface is numerical. It is not a parser looking for the word “left.” First consider **attention**.

An attention calculation forms a **query** for information to retrieve, **keys** for comparing context positions, and **values** carrying information from those positions. A common form is:

$$
\mathrm{Attention}(Q,K,V)=\mathrm{softmax}\left(\frac{QK^\mathsf{T}}{\sqrt d}\right)V.
$$

$Q$, $K$ and $V$ are matrices of vectors; $d$ is the key-vector dimension. $QK^\mathsf{T}$ gives comparison scores. Softmax converts them to nonnegative weights summing to one per query. Multiplication by $V$ combines information with those weights. These learned operations do not expose a list of human-readable reasons.

A **Transformer** is the sequence-processing architecture using attention and other learned transformations. A **KV cache** stores its key/value arrays, avoiding some repeated calculation during generation. TIC-VLA also uses completed VLM state as input to another network.

The inspected `ActionExpert._process_kv_cache` takes the **final layer's value array**, rearranges `[batch, heads, sequence, head_dimension]` into `[batch, sequence, heads × head_dimension]`, then projects vectors to 512 dimensions. This code expects the last product to be 128. Thus “uses KV cache” does not mean consuming every key and value from every layer. See [`ActionExpert`](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/models/ticvla.py#L90-L149).

The response and numerical representation both depend on the conversation. Replacing the representation with displayed text would change the action interface and require different code and validation.

## 7. How the action expert produces 30 coordinate pairs

The **action expert** is a smaller learned network for short-horizon navigation. A **horizon** is the future interval described by an output. It recalculates from current observations; reusing semantic features is not replaying an unchanged old path.

The inspected implementation:

1. Extracts current-image features and projects them to 512 dimensions.
2. Projects delayed VLM value features to the same dimension.
3. Encodes each scalar motion/delay input as a vector, adding learned position embeddings to distinguish the slots.
4. Concatenates those sequences into the context.
5. Creates 30 learned **action queries**, one per future output slot.
6. Applies cross-attention blocks so each query retrieves and combines context.
7. Uses an **MLP**, a multilayer perceptron of learned transformations and nonlinear functions, to convert each updated query into two numbers.

Queries are learned parameters, not measured future images. There is no loop commanding 30 physical steps inside this calculation. Shape `[1, 30, 2]` means one input example, 30 predicted positions and two coordinates per position.

| State slot | Meaning | Unit |
|---|---|---|
| `vx` | Current forward velocity | m/s |
| `vy` | Current leftward velocity | m/s |
| `yaw_rate` | Current heading-change rate | rad/s |
| `dx`, `dy` | Displacement since the semantic reference, in that reference frame | m |
| `delay` | Separation between action observation and semantic reference | s |

The model must be trained to interpret these slots. Reordering them, substituting absolute map position for displacement, or inserting degrees instead of radians changes its numerical problem. The [state contract](../reference/asynchronous-runtime.md) describes this repository's boundary.

## 8. Exactly what do path coordinates mean?

A **coordinate frame** defines an origin and axis directions. The inspected data preparation expresses future positions relative to the current robot: x forward and y left. The released package's output is interpreted in metres. $(1.0,0.2)$ means a candidate position 1 m forward and 0.2 m left of the reference pose, not a speed or pixel coordinate.

All points share that origin. For $(0.1,0)$, $(0.2,0)$ and $(0.3,0)$, the endpoint is 0.3 m forward. Summing them incorrectly yields 0.6 m. The package returns positions directly and our adapter does not accumulate them. The [data generator](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/data/s01_batch_json_generation.py) and [policy dataset](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/data/policy_data.py) establish this convention.

The code associates the 30 slots with 0.1-second spacing. Our adapter labels them 0.1 through 3.0 s. These are predicted times, not measured B2 arrivals. A controller following only the path's shape need not meet those times; tracking a timed trajectory requires explicit speed/timing control too.

Two display quantities answer different questions:

$$
d_{\mathrm{end}}=\sqrt{x_{30}^{2}+y_{30}^{2}},\qquad
L=\sum_{i=1}^{30}\|p_i-p_{i-1}\|,\quad p_0=(0,0).
$$

$d_{\mathrm{end}}$ is straight distance to the endpoint; $L$ is displayed polyline length. Neither measures distance actually walked. Use the plot's metre axes, since automatic screen scaling changes apparent line length.

How can RGB produce metres without depth? Training pairs appearance and motion with metric trajectories. The network learns statistical relationships; it does not become an exact range sensor. Changes in camera height, field of view, crop, mounting angle or robot shape can disrupt those relationships. The [control chapter](control-loop.md) develops the B2 checks.

## 9. Read the paper and released package separately

The paper, experiments, public code and a checkpoint are related evidence, not identical specifications. The source checked here is `9fa6f8b66b9e121d5df5df071297bba8e5353ebb`. Our loader verifies checkpoint keys and shapes rather than silently leaving unmatched layers untrained.

| Detail | Paper description | Inspected package/checkpoint path |
|---|---|---|
| Action output | Three-component motion increments accumulated to a trajectory | Direct XY positions; no cumulative sum |
| Action attention blocks | Six in Appendix A | Three in the loaded checkpoint |
| Motion metadata | Includes heading displacement | Five motion scalars plus delay; no separate heading-displacement slot |
| Semantic feature projection | Appendix describes another source width | Code expects final-layer value width 128 |
| Simplified prediction call | Paper describes asynchronous execution | Package `predict()` blocks until completion |

Paper-side entries are from [Appendix A](https://arxiv.org/html/2602.02459v2#A1); package-side entries come from [model source](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/ticvla/models/ticvla.py) and our [strict loader](../../src/b2_tic_vla/inference.py). They prevent using a figure as a drop-in interface specification. They do not establish when or why the release changed. We have not reproduced every training stage or established the downloaded checkpoint's exact training history.

Do not add a third coordinate, add three layers or integrate XY outputs merely to resemble the paper: those changes alter the checkpoint's meaning.

## 10. How slow and fast jobs proceed together

**Synchronous** execution waits for an operation before the next dependent operation. **Asynchronous** execution allows other useful work while that operation remains unfinished. **Concurrency** means progress over overlapping periods; it does not promise GPU kernels run at exactly the same instant.

A synchronous camera prediction follows:

```text
Read image A -> generate text -> extract conversation features
             -> decode path for A -> save/display -> next prediction
```

During text generation this job produces no new paths. A separate preview can refresh camera pictures, but that does not refresh the predicted path.

An asynchronous design keeps a complete **semantic snapshot**: features, returned text, reference image timestamp, reference robot pose and result identity. One job computes the next snapshot. Another repeatedly combines the last completed snapshot with a new image and motion state. Replacement happens as a unit after completion, so features cannot acquire another observation's timestamp.

In this invented example an older snapshot already exists, and a new semantic job uses the observation at 10.0 s and finishes at 13.0 s:

| Time | Semantic job | Action job |
|---|---|---|
| 10.0 s | Starts calculation for reference 10.0 s | Uses older completed snapshot and image/state 10.0 s |
| 10.2 s | Still calculating | Recomputes from image/state 10.2 s and the older snapshot |
| 12.8 s | Still calculating | Recomputes; the older snapshot has aged further |
| 13.0 s | Publishes snapshot with reference 10.0 s | Can switch to it; its age is already 3.0 s |
| 13.2 s | May compute the following snapshot | Uses image/state 13.2 s, reference 10.0 s and age 3.2 s |

For semantic reference time $t_r$, completion time $t_c$ and action observation time $t$:

$$
\Delta t=t-t_r=(t_c-t_r)+(t-t_c).
$$

The first term covers time until availability; the second covers reuse afterwards. Replacing the reference with completion time erases the first term. If the robot moved 0.4 m meanwhile, its displacement belongs to this same snapshot's reference frame.

No snapshot exists at startup. Later a snapshot can become too old or a job can fail. A controller needs explicit behavior for each case. Keeping the last guidance forever is not automatically justified by asynchronous execution.

Both jobs share Jetson resources. Threads, processes and CUDA streams schedule work; they do not guarantee deadlines. Measure image extraction, action decoding, state alignment and delivery together. Raising a timeout does not make them faster.

A **process** is a running program with its own address space. A **thread** is an execution path within a process; threads can share the same loaded model. A **CUDA stream** is an ordered queue of GPU operations. Separate streams allow the GPU runtime to schedule independent queues, but compute capacity and dependencies can still make operations wait. Two threads are therefore not two GPUs, and two containers are not automatically two separate models or two separate GPUs either.

The scheduling structure can be expressed with the following conceptual pseudocode. It omits error/expiry handling to expose the dependency, and is not an executable robot program:

```text
repeat while observation experiment is running:
    if semantic job finished:
        publish its complete result with its original reference
    obtain the newest image and associated measured motion
    if no semantic job is running:
        start a new semantic job; do not wait for completion here
    if a valid completed semantic snapshot exists:
        calculate age and displacement from that snapshot's reference
        calculate a new action path using the current image
        record the path
    else:
        record that no usable semantic context exists
```

“Do not wait” applies to the newly launched semantic job. The action calculation itself still takes time, and the program waits for its required result before recording that path. During this period the semantic thread may advance too. The next iteration obtains a newer image rather than automatically processing every queued old image. On completion, the new semantic result is made available for a subsequent action calculation; no partially filled tensor is published.

In our observation experiment the camera producer and model observer are separate containers. They exchange completed images and metadata through a dedicated SSD directory; the model side mounts it read-only. Within the model process, a worker thread and the main thread share loaded weights and use separate CUDA streams. This explains both levels of “parallel”: independent camera acquisition, and overlapping semantic/action work. The [deployment explanation](deployment-design.md) covers the container boundary in more detail.

## 11. What runs in this repository?

Two model paths exist; neither currently drives B2.

**Synchronous demonstration.** [`TicVlaPredictor`](../../src/b2_tic_vla/inference.py) loads reviewed local assets, calls the predictor, validates finite `[1, 30, 2]` output and creates a `Plan`. [`camera_demo.py`](../../tools/camera_demo.py) coordinates capture, prediction and HTML display. The blue path comes from the action tensor, not coordinates parsed from the response.

**Asynchronous observation experiment.** [`observe_async.py`](../../tools/observe_async.py) and [`semantic_cache.py`](../../src/b2_tic_vla/semantic_cache.py) maintain a semantic worker and current-observation action calculation. The worker currently obtains features through a synchronous call that also calculates an unused action; it is not an optimized reproduction of the paper runtime. It assumes stationary motion and sends no motor requests. The [experiment record](../records/async-shadow.md) reports completed actions alongside substantial startup/refresh gaps.

Separate B2 tools receive machine state. That does not connect state to model input automatically. Remaining work establishes units, frames and timestamps, replaces assumed motion with measurements, sustains useful action updates and implements a separately validated command path.

Continue with [how the weights are learned](ticvla-training.md), then [how a path becomes B2 movement requests](control-loop.md). Execution commands belong to procedures; this chapter explains what those commands cause.
