# Development and experiments

[日本語](development.ja.md) · [Home](../README.md)

This guide defines the route to a reproducible B2 experiment. Preparation tools
are implemented, but target hardware, GPU inference, and robot motion remain
unvalidated. Use [onsite preparation](onsite.md) for the current commands; the
stages below describe what evidence is needed before advancing.

## Run local checks first

From the repository root with Python 3.10 or later:

```sh
PYTHONPATH=src python3 -m b2_tic_vla replay
PYTHONPATH=src python3 -m unittest discover -s tests -v
git diff --check
```

The bundled replay evaluates three synthetic samples: two accepted candidate
commands followed by a stale-image rejection with a zero command. It runs no
neural model, connects to no hardware, and sends no motion commands. Acceptance
means the configured software checks passed, not that a path is clear or safe
for the B2. The example limits need separate approval and measurement before
any real use. Tests exercise local logic with synthetic data and mocked vendor
interfaces; they do not validate the actual drivers or trained model.

### Preparation verification

On 2026-10-23, the local development host (macOS, Python 3.14.7) passed 79
standard-library tests, synthetic CLI replay, bytecode compilation, and source
syntax parsing against Python 3.10 (package/tests) and Python 3.8 (standalone
inspector). Syntax parsing is not execution on those older interpreters.
The inspector also ran on that host, including creation of a missing output
directory; this was not a Jetson inventory. All 20 Markdown files parsed as GFM
with matching translations, valid local links/fragments, and required Japanese
punctuation. Source scans found no secrets. Recheck Git history before sharing.
Ruff was unavailable and could not be installed in this environment, so its
configured lint/format checks have not run. No container build, GPU prediction,
or real camera/robot probe has been validated.

## 1. Understand the system

Read the [architecture](architecture.md) and [project status](status.md).
A checkpoint is a saved set of model parameters. Inference uses those parameters
to produce a prediction; it does not train the model. A trajectory specifies
positions over time, while a velocity command specifies how fast to move now.
The adapter must connect those representations using verified units and frames.

Do not equate a plausible plotted trajectory with successful navigation. The
robot must execute it, react to new observations, and reach the intended goal.
The stages below isolate those questions before combining them.

## 2. Identify the actual environment

Record the following in a reviewed environment specification before installing
model dependencies. Keep addresses and access credentials in laboratory storage.
Use the [deployment information guide](deployment-intake.md) for detailed
questions, read-only inspection commands, and an initial response template.

| Area | Required information | Why it matters |
| --- | --- | --- |
| Robot | B2 variant, firmware, permitted high-level API, stop and override behavior | Establish the control contract |
| Compute | CPU architecture, GPU model and memory, OS, driver, CUDA or JetPack | Select compatible inference packages |
| Camera | Driver, image format, resolution, rate, timestamps, calibration and mounting transform | Match model observations to the robot |
| State | Available velocity, position and orientation, frames, rate and timestamps | Reconstruct motion during inference |
| Transport | SDK revision, interface, clock alignment, measured delay | Prevent mismatched or stale observations |

The standalone inspector uses Python 3.8 or later with no third-party packages:

```sh
python3 tools/inspect_target.py
```

It reads installed system information and reports unknown, unavailable, and
unchecked items explicitly. It does not install packages, contact a remote
service, start sensors, or verify GPU container operation. Network addresses
are excluded unless explicitly requested. Even the default report may contain
laboratory information; review it before sharing. This tool has not been run
on the target. Do not infer a B2 configuration from another robot's setup guide.
Confirm whether ROS 2 is needed before choosing a distribution.

**Completion:** a reviewer can identify the hardware and software without
accessing a private chat, and each unknown has an explicit next check.

## 3. Reproduce model inference offline

The implemented `infer` command loads existing local files and calls the
upstream package's synchronous prediction API for a recorded observation. It
uses zero semantic-cache delay and does not reproduce the paper's asynchronous
execution. Its output is XY positions in the current robot frame, spaced at
0.1-second intervals; do not cumulatively sum those positions. It checks the
checkpoint architecture and uses strict parameter loading. Compatibility with
the actual downloaded checkpoint has not been demonstrated.

Replay starts a new host-clock interval. Original recording timestamps remain
source metadata; they are not evidence that a replayed image is a fresh live
observation. The output is a plan, not a command sent to the robot. See
[onsite preparation](onsite.md) for required local files and command arguments.

Resolve the [third-party conditions](../THIRD_PARTY.md) first. Record the upstream
commit, model repository revisions, checkpoint checksum, dependency versions,
precision, and input preprocessing. Obtain external materials separately from
this repository through their official distribution tools.

Use a small recording approved for research. Preserve image capture times and
matching state samples. Inspect their coordinate frames and units. Load the
checkpoint, check missing or unexpected parameters, and confirm the action
shape and meaning. A checkpoint mismatch is a failed setup, not a warning to ignore.

Overlay the predicted trajectory on the observations. Measure initialization,
steady-state inference, and observation age separately. Record GPU memory use.
Test a missing image, missing state, a delayed result, and invalid numerical
output. The program should report the failure and produce no executable command.

**Completion:** another researcher can reproduce predictions from the specified
inputs and revisions. No robot motion interface is connected.

## 4. Observe live predictions without commanding motion

The `camera`, `state`, and `record` commands provide observation acquisition.
`record` saves one image and a received state sample, checking a receipt-time
skew of at most 0.2 seconds. This is not hardware synchronization: vendor capture
times remain unverified, and frames remain unknown unless explicitly confirmed.
Do not relabel an unknown velocity frame just to make inference accept it.
Continuous live prediction, atomic asynchronous cache updates, and a complete
real-time observation/control loop are still to be implemented.

Connect the actual camera and state reader. Keep the command sender disabled.
Compare stationary, straight-motion, and rotation observations collected through
an approved manual procedure. Verify image/state alignment, camera-to-body
transforms, cache timestamps, and the age of predictions.

Include slow inference and a temporarily unavailable sensor. Check that the
system reports the expected state rather than presenting stale output as current.
The inspection output should show capture time, prediction time, frame and units,
the proposed command, and why that command would be accepted or rejected.

**Completion:** recorded evidence demonstrates correct transformations and
command rejection. Nothing in this stage establishes autonomous driving performance.

## 5. Validate the command path, then evaluate navigation

The repository currently has no motor command sender. The implemented
`PathTracker` produces candidate velocities for observation-only evaluation:
forward motion and yaw, with zero lateral velocity. It checks data validity,
freshness, and configured limits. It does not verify obstacle clearance or
provide a live watchdog or emergency stop. Integration with the B2 high-level
motion interface is a separate future stage.

Before enabling model-driven commands, agree on the test area, operator control,
speed and acceleration limits, stopping distance, and recovery procedure.
Verify the SDK return behavior and command-loss behavior on the actual firmware.
Use a command path independent of model inference to expire commands and stop.
An SDK call returning successfully is not proof that the robot has stopped.

Start with controlled tests of the command interface and tracker. Proceed to
short navigation tasks only after those tests pass. Keep configuration changes
separate from evaluation: define the tasks, trial count, limits, and success
criteria before running the comparison. Record every attempted trial, including
manual interventions, faults, collisions, and unsuccessful runs.

Measure goal completion, interventions, path length, latency distributions,
stopping behavior, and resource use. Define each metric and its denominator.
Compare against an explicitly specified baseline under the same conditions;
do not substitute published results from a different robot or environment.

**Completion:** the report contains methods, complete trial accounting, results,
failure analysis, and limits on what the evidence supports.

## Keeping a reproducible record

For each experiment, record:

- The question, hypothesis, comparison, and predefined acceptance criteria.
- Code commit; model/checkpoint revisions and checksums; package and firmware
  versions; hardware, calibration, configuration, and random seeds where applicable.
- Input dataset version, instructions, procedure, timestamps, and trial counts.
- Measured results, failures, deviations, analysis method, and uncertainty.
- Evidence location in approved storage and its access restrictions; a public
  report must not expose private storage addresses or identifying recordings.
- Conclusion, limitations, and the next experiment justified by the result.

Store raw recordings, maps, model files, and run logs in approved laboratory
storage. Commit only material cleared for sharing, such as a sanitized report,
configuration example, or a small synthetic fixture. Ignore patterns are a
convenience, not a guarantee that a new file is suitable for publication.

## When a check fails

| Observation | Next investigation |
| --- | --- |
| Checkpoint keys or tensor shapes disagree | Compare the exact code revision, model config, and checkpoint; stop integration |
| A straight route turns or appears mirrored | Check axes, yaw sign, camera transform, and increment composition |
| Predictions look delayed or discontinuous | Trace capture times, clock alignment, cache replacement, and queue age |
| The SDK accepts commands but the robot behaves differently | Check firmware, control mode, units, and command ownership under the approved procedure |
| Results cannot be repeated | Compare revisions, inputs, calibration, seeds, and trial definitions before tuning |

Write the cause and verification of a fix in the relevant guide. Update both
languages and [project status](status.md) when the next stage becomes possible.
