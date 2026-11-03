# Operator tutorial: a short camera and predicted-path demo

[日本語](live-camera-demo.ja.md) · [Documentation](README.md) · [Initial setup](setup-from-scratch.md)

## 1. Goal and prerequisites

This is the **step-by-step operating manual** for the prepared external Jetson.
You will start the model once, watch the camera preview change, see repeated
predictions for saved input frames, and stop the run. B2 remains disconnected;
there is no motor-command function in this demo. No Internet, ROS 2, Mac Docker,
web server or SSH tunnel is needed. Remote viewing can use the already working
RDP desktop. Both GPU computation and camera acquisition run on Jetson.

Before starting, connect **one ZED 2i by USB 3**, close any other camera user,
and prepare the local inputs in [initial setup](setup-from-scratch.md). Defaults
match the existing research deployment: native ZED SDK 4.1.2, private API under
`local/camera-runtime/attempt-01/python`, matching settings under that attempt's
`settings`, the existing GPU image, reviewed external upstream source, approved
base-model snapshot and hash-verified derived safetensors. Nothing is installed
or downloaded when this demo starts. Do not run it as root.

This is an image-response demonstration with **assumed stationary state**, not a
navigation trial. Moving the handheld camera changes the visual input but does
not supply measured robot displacement or yaw. The path is uncalibrated and
cannot establish free space or correct instruction following. The live preview
and the older prediction input are deliberately displayed separately.

## 2. Terminal A: check existing inputs

Run these commands **on Jetson**, either in your SSH session or its GUI terminal:

```bash
cd ~/Developer/Projects/Robotics/b2/VLN_B2
sudo -v
python3 tools/camera_demo.py check
```

`sudo -v` authenticates in the terminal. Never put its password into a command,
configuration file or chat. The Python launcher stays under the research UID;
only the existing Docker engine is invoked through `sudo -n`.

A successful check prints `prepared_inputs_verified: true`, an immutable image
ID, actual camera device nodes, `model_loaded: false`, `camera_opened: false`
and `motion_sent: false`. It reads source/cache paths, hashes the 3.77 GB derived
checkpoint and identifies the single ZED through sysfs. It neither loads the
model nor opens the camera; successful calibration, GPU execution and actual
capture must still be established by the next step. Hashing can take a few seconds.

The device names are discovered again, not copied from yesterday's USB bus
numbers. No supported camera or multiple matching devices is an error; the
launcher does not guess an arbitrary `/dev/video0`. If you used different
private API/settings locations during initial setup, see section 8.

## 3. Terminal A: start camera and model

Use a **new** output directory; existing experiment folders are never reused:

```bash
python3 tools/camera_demo.py run \
  --output local/live-camera-demo-03 \
  --duration 60 \
  --instruction "Move straight ahead."
```

The launcher prints a `file:///.../index.html` address. Keep this terminal open.
The command is a foreground, bounded run, not a service. It starts two temporary
containers: a camera recorder targeting one JPEG/s and a predictor that loads
TIC-VLA once, then selects a new recent frame for each synchronous prediction.
It creates an HTML page immediately, including loading/waiting/error states.

The 60-second budget includes model loading for the predictor. Camera recording
lasts up to 60 seconds after camera open. A prediction already in progress can
finish after the input window; native calls have independent container deadlines
of 120 seconds and a 125-second supervisor bound. These are upper bounds, not
expected latency. Normally the whole demo ends shortly after one minute.

The first result needs model loading **plus** inference: earlier measurements
were about 13 seconds each. Allow roughly 25–35 seconds rather than expecting an
immediate path. Subsequent predictions reuse the loaded model but repeat the
synchronous semantic calculation, so their path updates can still take about
10–15 seconds. This demonstration is not the faster cache-reuse experiment and
does not claim a video-rate path stream. Actual timing depends on the run.

## 4. Terminal B on the RDP desktop: open the display

Open a second terminal **inside the Jetson GUI**, then run:

```bash
cd ~/Developer/Projects/Robotics/b2/VLN_B2
xdg-open "$PWD/local/live-camera-demo-03/index.html"
```

Alternatively paste the address printed in terminal A into the **Jetson's**
browser. A normal SSH shell may lack a desktop display session, so `xdg-open`
there need not work. You do not need to configure Mac, run a tunnel, expose a
port or enable a web server. The page is a local file that refreshes every two
seconds while the supervisor is running.

Updated predictions also show **Generated VLM response**, endpoint coordinates,
straight-line endpoint distance and sampled path length. The returned text is
stored in `model.vlm_response`; it is not parsed to draw the blue action path.
Scroll within the embedded report or open the full report to read it. Start a
new output directory after updating: old reports cannot reconstruct discarded
text. For a guided reading exercise, use [Understanding TIC-VLA](ticvla-explained.md).

On the prepared Jetson, the completed recorded-image example can also be opened
from a GUI terminal, without loading the model again:

```bash
cd ~/Developer/Projects/Robotics/b2/VLN_B2
xdg-open "$PWD/local/model-response-validation-01/results/prediction.html"
```

This optional example exists on the prepared target; a fresh installation must
generate its own report. The live commands in this tutorial use a new `03`
directory. If that directory already exists, select another unused number.

The page presents:

1. **Stage and instruction.** Loading model, waiting for a new image, predicting,
   finished, stopped or failed. Absence of a path during loading is expected.
2. **Current camera preview.** Target one acquired image/s, browser refresh every
   two seconds, with frame name and host receipt age. Capture-clock alignment
   remains unverified; a frozen/old frame is not silently labelled new.
3. **Last completed prediction and its exact input.** A saved input photo beside
   its model-relative path, with input frame identity and inference duration.
   The current preview may already depict a different scene.
4. **Full report link.** Open it in another tab for all 30 coordinates without
   the demo page's refresh resetting your scroll position.

The report's red dot is the assumed origin; blue points are future relative
positions in metres. x forward points up and y left points left. The model's XY
positions are **not cumulatively summed**. Point times use an assumed 0.1-second
interval, not a verified B2 control period. The path is not projected onto the
photo because camera-to-B2 geometry has not been measured.

## 5. A short demonstration you can perform

Place the camera securely and look at a static scene. Once its first path has
appeared, gently point it toward a different view and hold it still for the
next prediction. A small change in yaw is enough; avoid unplugging the cable or
rapidly swinging the device. Keep the same instruction for this comparison.

First confirm that the **preview image changes**. Then wait for the completed
prediction's **input frame identifier and photo** to change. Compare its path
and coordinates with the previous saved report. A line should not be claimed
to have responded to the new scene while the displayed prediction still names
the old input. You may only fit two or three results into a short run.

Use a new run directory to repeat with another instruction. Path differences
alone do not prove instruction following: the upstream model can sample outputs,
and camera motion has no corresponding real odometry in this test. A path that
looks implausible is useful evidence to retain, not a reason to bypass checks.
Nothing in these actions can send a robot command.

## 6. Stop and retain results

Wait for automatic completion, or press the following in **terminal A**:

```text
Ctrl+C
```

The supervisor removes only its two named containers and waits for its client
processes. The final page says the run ended and stops refreshing. Images,
reports, logs and the final page are retained. Closing the browser only closes
the viewer; it does not stop inference. Closing the terminal is not the
recommended stop action. If cleanup fails, the command reports failure rather
than claiming that everything stopped.

Inspect the completion record and running-container list if needed:

```bash
python3 -m json.tool local/live-camera-demo-03/summary.json
python3 -m json.tool local/live-camera-demo-03/predictions/status.json
sudo docker ps --format '{{.Names}}'
```

A natural successful run has `outcome: "finished"`, empty `cleanup_errors`, and
at least one completed prediction with `passed: true`. `stopped_by_operator`
means you interrupted it; it may have completed no predictions yet. Both cases
record `motion_sent: false` and `robot_connected: false`. The two names beginning
`b2-demo-camera-` / `b2-demo-predict-` for this run should be absent afterwards.
Do not remove unrelated containers. This is termination of computation, not a
robot emergency stop; there is no robot connection in this demo.

| Output under the chosen `local/` directory | Contents |
|---|---|
| `index.html` | Updating preview/result display while running; final saved display after stop |
| `camera/frames/frame-*.jpg`, `frame-*.json` | Immutable captured images and timing/digest metadata |
| `camera/frames/latest.json`, `summary.json` | Atomic latest camera reference and camera completion record |
| `predictions/prediction-*.jpg` | Exact immutable input copy for each inference |
| `predictions/prediction-*.json`, `*.html` | Plan, timing/provenance and standalone input/path display |
| `predictions/status.json` | Current/final predictor stage, completed count and last result identity |
| `invocation.json`, `camera.log`, `predict.log`, `summary.json` | Actual image/commands, diagnostics and supervisor outcome |

Keep these private: the HTML embeds room images and can contain people/screens.
A camera changing at one JPEG/s is not a 30 fps video recording. Inference and
startup times are separate from that acquisition target.

## 7. What command actually controls B2?

**There is no robot-command CLI yet.** `check` inspects inputs; `run` captures,
predicts and displays; Ctrl+C stops those processes. Neither the local file
viewer nor the path report is a control panel. Do not add a fictitious "drive"
command to a manual or run a vendor movement example as the next shortcut.

After this demo, use [the field card](field-card.md) for Ethernet and receive-only
state inspection with the separate Unitree environment. Real frames, clock/state
alignment, control authority, remote priority, receiver command-loss behavior,
a guarded sender and independent stop/expiry checks remain before motion.
When that interface is implemented and verified, the operating manual must add
its exact prerequisites, start/control/stop commands and expected responses.
Until then, prediction and physical control remain separate stages.

## 8. Troubleshooting and alternate private camera paths

| Symptom | Action |
|---|---|
| Check cannot inspect Docker | Run `sudo -v` as the research user; verify the existing image/storage |
| Camera absent/ambiguous | Connect one ZED 2i; check USB 3 cable/power and device identity |
| Preview stays empty | Inspect `camera.log`; close other camera users and check matching calibration |
| Preview changes, no path yet | Allow load plus inference; read stage and `predict.log` |
| Path does not change | Check completed count and exact input frame; do not compare it with an unrelated newer preview |
| Failed run | Keep logs/status, fix the cause and choose a new output directory |
| Browser does not refresh a local file | Reload manually; the terminal/status file remains authoritative |
| New run refused | Use a new name, preserving previous evidence |

For a private prefix/settings pair created by the fresh-setup guide, pass both
paths explicitly to **check and run**:

```bash
python3 tools/camera_demo.py check \
  --camera-api local/camera-runtime/rebuild-01/python \
  --settings-dir local/camera-settings-01
python3 tools/camera_demo.py run \
  --camera-api local/camera-runtime/rebuild-01/python \
  --settings-dir local/camera-settings-01 \
  --output local/live-camera-demo-02 --duration 60 \
  --instruction "Move straight ahead."
```

No configuration is saved globally. The old single-image procedure remains
available in [recorded-image prediction](run-camera-demo.md) for controlled
step-by-step debugging. Exact model/source/software provenance and the broader
readiness boundary are in [the milestone](milestone-2026-11-03.md).

## 9. Recorded acceptance on the prepared Jetson

Source `9fe752c`, the existing reference GPU image and approved local assets
completed a real-camera run on 2026-11-03. The producer captured **60/60 frames**
at its one-image/s target. The model loaded **once in 11.235 s** and completed
**five predictions**, all with 30 points, using frames 13, 26, 36, 46 and 57.
Inference took **12.617, 10.435, 10.243, 11.034 and 10.446 seconds**. Each report
retains its exact input image/digest and a standalone HTML display.

Both containers exited 0, the supervisor reported `finished`, cleanup errors
were empty and no run container remained. The final display was rendered and
visually inspected. **177 tests passed on Mac and Jetson**. This verifies the
prepared workflow, not correct navigation or a paper-level reproduction. No
operator camera-reorientation experiment was recorded during that automated
check; perform the visual comparison in section 5 yourself.

A separate Ctrl+C test during an active run reported `stopped_by_operator`,
empty cleanup errors, no remaining containers and no refresh tag in the final
page. Container exit 137 in that interruption test reflects intentional forced
removal, not successful prediction completion or a diagnosed model crash.

The operator confirmed camera-image and predicted-path display on 2026-11-03,
and then reported attaching the powered B2. This confirms the viewer workflow,
not navigation quality, camera-motion compensation or real-state integration.
See [current first-connection findings](status.md).
