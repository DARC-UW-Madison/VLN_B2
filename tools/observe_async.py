"""Bounded camera-file/cache concurrency experiment; assumed state and no motor I/O.

The observation duration starts after model loading. Native GPU calls cannot be
interrupted by cancelling a Python thread: shutdown stops new requests, resets
the cache, then waits for the last call. An external container supervisor must
enforce a 180-second process limit. This is not a live control-rate measurement,
navigation-quality evaluation, or validation of an operational cache-age limit.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import platform
import re
import stat
import time


STATE_SOURCE = "assumed stationary; no robot state"
MAX_IMAGE_BYTES = 32 * 1024 * 1024
MAX_MANIFEST_BYTES = 64 * 1024


def positive(value):
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise argparse.ArgumentTypeError("Provide a finite positive number")
    return result


def duration(value):
    result = positive(value)
    if result > 60:
        raise argparse.ArgumentTypeError("Observation duration must be at most 60 seconds")
    return result


def sha256_value(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("Expected a lowercase SHA256 digest")
    return value


def read_regular(path, limit):
    """Read bounded regular files without following a final symlink."""
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= limit:
            raise ValueError("Input must be a nonempty regular file within its size limit")
        if Path(path).is_symlink():
            raise ValueError("Symlink inputs are not accepted")
        data = stream.read(limit + 1)
        if not 0 < len(data) <= limit or len(data) != info.st_size:
            raise ValueError("Input changed while being read or exceeds its size limit")
        return data


def file_digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def finite_number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def load_observation(directory, instruction, seen, now):
    """Validate one atomic manifest; preserve camera timing verification verbatim.

    Only the producer owns publication. The consumer must mount this directory
    read-only; every image basename must remain immutable for the entire run.
    """
    from b2_tic_vla.semantic_cache import Observation
    from b2_tic_vla.types import Frame, RobotState

    manifest = json.loads(read_regular(directory / "latest.json", MAX_MANIFEST_BYTES))
    if not isinstance(manifest, dict):
        raise ValueError("Observation manifest must be an object")
    if (type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1
            or manifest.get("mode") != "camera_stream_observation_only"
            or manifest.get("producer_clock") != "host_monotonic"
            or manifest.get("motion_sent") is not False):
        raise ValueError("Unsupported observation schema, clock, mode or motion flag")
    values = manifest.get("frame")
    if not isinstance(values, dict) or set(values) != {f.name for f in fields(Frame)}:
        raise ValueError("Manifest must provide exactly the Frame fields")
    basename = values.get("path")
    if (not isinstance(basename, str) or not basename or basename in {".", ".."}
            or "/" in basename or "\\" in basename or "\x00" in basename
            or Path(basename).name != basename
            or Path(basename).suffix.lower() not in {".jpg", ".jpeg"}):
        raise ValueError("Image path must be a relative JPEG basename")
    if type(values.get("timestamp_verified")) is not bool:
        raise ValueError("Image timing verification must be a boolean")
    received = values.get("received_at")
    captured = values.get("captured_at")
    if not finite_number(received) or received < 0 or received > now + 0.001:
        raise ValueError("Image receipt must use the current host monotonic clock")
    if captured is not None and (not finite_number(captured) or captured < 0
                                 or captured > received + 0.001):
        raise ValueError("Image capture time must be finite and no later than receipt")
    if values["timestamp_verified"] and captured is None:
        raise ValueError("Verified image timing requires a capture time")
    source_at, source_clock = values.get("source_timestamp"), values.get("source_clock")
    if source_at is not None and not finite_number(source_at):
        raise ValueError("Source timestamp must be finite when supplied")
    if source_clock is not None and (not isinstance(source_clock, str) or not source_clock.strip()):
        raise ValueError("Source clock must be a nonempty string when supplied")
    expected = sha256_value(manifest.get("image_sha256"))
    image = directory / basename
    if image.is_symlink() or image.resolve() != directory / basename:
        raise ValueError("Image path must remain inside the observation directory")
    image_bytes = read_regular(image, MAX_IMAGE_BYTES)
    if not image_bytes.startswith(b"\xff\xd8"):
        raise ValueError("Expected JPEG image bytes")
    if hashlib.sha256(image_bytes).hexdigest() != expected:
        raise ValueError("Image SHA256 mismatch")
    identity = (expected, tuple((key, values[key]) for key in sorted(values)))
    if basename in seen and seen[basename] != identity:
        raise ValueError("An immutable image basename was reused or its metadata changed")
    seen[basename] = identity
    frame = Frame(**{**values, "path": str(image)})
    state = RobotState(received, 0., 0., 0., 0., 0., 0.,
                       frame_id="assumed_stationary_world", velocity_frame="body")
    return Observation(frame, state, instruction, state_timing_verified=False,
                       pose_frame_verified=False, state_aligned_at=None), expected


def observation_reason(observation, now):
    frame = observation.frame
    if now - frame.received_at > .5:
        return "stale_observation"
    if frame.timestamp_verified and now - frame.captured_at > .5:
        return "stale_capture"
    return None


def metadata(observation):
    return {"frame": observation.frame.path, "received_at": observation.frame.received_at,
            "captured_at": observation.frame.captured_at,
            "timestamp_verified": observation.frame.timestamp_verified,
            "state_timing_verified": observation.state_timing_verified,
            "pose_frame_verified": observation.pose_frame_verified,
            "state_aligned_at": observation.state_aligned_at,
            "pose_frame": observation.state.frame_id,
            "velocity_frame": observation.state.velocity_frame}


def context_metadata(context):
    if context is None:
        return None
    return {"sequence": context.snapshot.request.sequence,
            "reference": metadata(context.snapshot.request.observation),
            "completed_at": context.snapshot.completed_at,
            "semantic_age_s": context.semantic_age_s,
            "model_delay_s": context.observation_delay_s,
            "timing_basis": context.timing_basis, "shadow_only": context.shadow_only,
            "state_features": list(context.state_features)}


def check_immutable_image(observation, expected):
    if hashlib.sha256(read_regular(observation.frame.path, MAX_IMAGE_BYTES)).hexdigest() != expected:
        raise ValueError("Immutable image changed after manifest validation")


def semantic_work(predictor, ticket, expected, torch, owned_cache):
    """Capture only the explicit complete-conversation forward, never token steps."""
    torch.cuda.set_device("cuda:0")
    observation = ticket.observation
    check_immutable_image(observation, expected)
    captured = []

    def capture(module, args, kwargs, output):
        if kwargs.get("use_cache") is True and kwargs.get("return_dict") is True:
            captured.append(getattr(output, "past_key_values", None))

    model = predictor._model
    handle = model.vlm.register_forward_hook(capture, with_kwargs=True)
    stream = torch.cuda.Stream(device="cuda:0")
    started = time.monotonic()
    try:
        with torch.cuda.stream(stream), torch.inference_mode():
            predictor.predict([observation.frame.path], observation.instruction,
                              observation.state, observation.frame.received_at)
            if len(captured) != 1 or captured[0] is None:
                raise ValueError("Expected exactly one complete semantic-cache forward")
            payload, description = owned_cache(
                captured[0], torch, model.vlm.language_model.config.num_hidden_layers,
                model.action_expert.kv_cache_proj.in_features)
            stream.synchronize()
        return payload, {**description, "seconds": time.monotonic() - started}
    finally:
        handle.remove()


def action_work(predictor, observation, context, expected, torch, load_image):
    check_immutable_image(observation, expected)
    started = time.monotonic()
    stream = torch.cuda.Stream(device="cuda:0")
    with torch.cuda.stream(stream), torch.inference_mode():
        pixels = load_image(observation.frame.path, input_size=448, max_num=1).to(
            device="cuda:0", dtype=torch.bfloat16)
        model = predictor._model
        visual = model.vlm.extract_feature(pixels)
        visual = visual.reshape(-1, visual.shape[-1]).unsqueeze(0)
        state = torch.tensor(context.state_features, device="cuda:0",
                             dtype=torch.bfloat16).reshape(1, 6, 1)
        output = model.action_expert(visual, state, kv_cache=context.snapshot.payload)
        if (tuple(output.shape) != (1, predictor._horizon, 2)
                or not torch.isfinite(output).all().item()):
            raise ValueError("Action output has invalid shape or nonfinite coordinates")
        stream.synchronize()
    return predictor._horizon, time.monotonic() - started


def observe(args, predictor, torch, emit, report):
    from b2_tic_vla.semantic_cache import CacheLimits, SemanticCache
    from profile_model_runtime import owned_cache

    load_image = importlib.import_module("ticvla.models.ticvla").load_image
    cache = SemanticCache()
    limits = CacheLimits(args.max_semantic_age, .5, .5, .2)
    executor = ThreadPoolExecutor(max_workers=1)
    future, ticket = None, None
    seen, handled = {}, set()
    last_requested = None
    counts = report["counts"]
    started = time.monotonic()
    deadline = started + args.duration
    report["observation_started_at"] = started
    try:
        while time.monotonic() < deadline:
            if future is not None and future.done():
                completed, future = future, None
                payload, details = completed.result()
                counts["completed"] += 1
                accepted = cache.publish(ticket, payload, time.monotonic())
                if not accepted:
                    counts["discards"] += 1
                emit("semantic_completed", sequence=ticket.sequence,
                     reference=metadata(ticket.observation), published=accepted, cache=details)
            try:
                observation, expected = load_observation(
                    args.observations, args.instruction, seen, time.monotonic())
            except FileNotFoundError:
                if (args.observations / "latest.json").exists() or seen:
                    raise
                time.sleep(.02)
                continue
            basename = Path(observation.frame.path).name
            if basename in handled:
                time.sleep(.02)
                continue
            handled.add(basename)
            counts["observations"] += 1
            reason = observation_reason(observation, time.monotonic())
            if reason is not None:
                counts["skips"] += 1
                emit("action_skipped", current=metadata(observation), reason=reason)
                continue
            if future is None and basename != last_requested and time.monotonic() < deadline:
                ticket = cache.begin(observation, time.monotonic())
                future = executor.submit(semantic_work, predictor, ticket, expected, torch, owned_cache)
                last_requested = basename
                counts["requests"] += 1
                emit("semantic_requested", sequence=ticket.sequence,
                     reference=metadata(observation))
            decision = cache.select(observation, time.monotonic(), limits, shadow_only=True)
            before = context_metadata(decision.context)
            if decision.context is None:
                counts["skips"] += 1
                emit("action_skipped", current=metadata(observation), reason=decision.reason,
                     before=before)
                continue
            count, seconds = action_work(predictor, observation, decision.context,
                                         expected, torch, load_image)
            now_after = time.monotonic()
            after = cache.select(observation, now_after, limits, shadow_only=True)
            current_snapshot = cache.is_current(decision.context.snapshot)
            accepted = (current_snapshot and after.context is not None
                        and after.context.snapshot is decision.context.snapshot
                        and now_after < deadline)
            reason = (after.reason if not accepted else "shadow_action_completed")
            if not current_snapshot:
                reason = "cache_changed_during_action"
            elif now_after >= deadline:
                reason = "duration_ended_during_action"
            counts["actions" if accepted else "discards"] += 1
            emit("action_completed" if accepted else "action_discarded",
                 current=metadata(observation), before=before,
                 after=context_metadata(after.context), reason=reason,
                 action_seconds=seconds, finite_point_count=count,
                 semantic_request_in_flight=future is not None)
    finally:
        cache.reset()
        report["observation_finished_at"] = time.monotonic()
        emit("observation_stopped", reason="no_new_requests; cache_reset")
        # GPU kernels cannot be forcibly interrupted by Future.cancel().
        executor.shutdown(wait=True, cancel_futures=True)
        if future is not None:
            try:
                _, details = future.result()
                counts["completed"] += 1
                counts["discards"] += 1
                emit("semantic_discarded_after_shutdown", sequence=ticket.sequence,
                     reference=metadata(ticket.observation), cache=details)
            except Exception as error:
                counts["errors"] += 1
                emit("cleanup_error", error_type=type(error).__name__, error=str(error))


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--observations", type=Path, required=True)
    result.add_argument("--base-model", required=True)
    result.add_argument("--checkpoint", type=Path, required=True)
    result.add_argument("--expected-sha256", required=True)
    result.add_argument("--upstream-root", required=True)
    result.add_argument("--report-dir", type=Path, required=True)
    result.add_argument("--duration", type=duration, default=20.)
    result.add_argument("--max-semantic-age", type=positive, required=True,
                        help="Experimental seconds; does not validate an operating limit")
    result.add_argument("--assumed-stationary", action="store_true", required=True)
    result.add_argument("--shadow-only", action="store_true", required=True)
    result.add_argument("--instruction", default="Move straight ahead.")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    # mkdir without parents/exist_ok prevents accidental output reuse.
    args.report_dir.mkdir(mode=0o700)
    os.chmod(args.report_dir, 0o700)
    report = {"passed": False, "model_constructed": False, "state_source": STATE_SOURCE,
              "noRobot": True, "noMotion": True, "robot_connected": False,
              "motion_sent": False, "shadow_only": True, "assumed_stationary": True,
              "concurrencyExperimental": True, "navigation_quality_evaluated": False,
              "live_control_period_validated": False, "physical_delay_limit_validated": False,
              "duration_s": args.duration, "max_semantic_age_s": args.max_semantic_age,
              "state_timing_verified": False, "pose_frame_verified": False,
              "state_aligned_at": None,
              "cleanup_policy": "Wait for the last native GPU call; external 180-second supervisor required",
              "counts": {key: 0 for key in ("observations", "requests", "completed", "actions",
                                            "skips", "discards", "errors")}}
    events_fd = os.open(args.report_dir / "events.jsonl", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(events_fd, "w", encoding="utf-8") as stream:
        def emit(kind, **values):
            event = {"event": kind, "at": time.monotonic(), "state_source": STATE_SOURCE,
                     "noRobot": True, "noMotion": True, "motion_sent": False,
                     "shadow_only": True, "concurrencyExperimental": True, **values}
            stream.write(json.dumps(event, allow_nan=False) + "\n")
            stream.flush()

        try:
            if os.environ.get("HF_HUB_OFFLINE") != "1":
                raise ValueError("HF_HUB_OFFLINE=1 is required")
            if platform.system() != "Linux":
                raise ValueError("This experiment requires the reviewed Linux CUDA runtime")
            if args.checkpoint.suffix != ".safetensors":
                raise ValueError("Only the verified converted safetensors checkpoint is accepted")
            expected = sha256_value(args.expected_sha256)
            if file_digest(args.checkpoint) != expected:
                raise ValueError("Checkpoint SHA256 mismatch")
            if args.observations.is_symlink():
                raise ValueError("Observation directory must not be a symlink")
            args.observations = args.observations.resolve(strict=True)
            if not args.observations.is_dir():
                raise ValueError("Observation input must be a directory")
            if not args.instruction.strip():
                raise ValueError("A nonempty navigation instruction is required")
            import torch
            from b2_tic_vla.inference import TicVlaPredictor

            if not torch.cuda.is_available():
                raise ValueError("CUDA is required")
            torch.cuda.init()
            torch.cuda.set_device("cuda:0")
            started = time.monotonic()
            predictor = TicVlaPredictor(args.base_model, str(args.checkpoint),
                                        "cuda:0", args.upstream_root).load()
            torch.cuda.synchronize()
            report.update(model_constructed=True, model=predictor.describe(),
                          torch_version=torch.__version__, load_seconds=time.monotonic() - started,
                          checkpoint_sha256=expected)
            emit("model_loaded", load_seconds=report["load_seconds"])
            observe(args, predictor, torch, emit, report)
            report["passed"] = report["counts"]["actions"] > 0 and report["counts"]["errors"] == 0
            report["outcome"] = ("shadow_actions_observed" if report["passed"]
                                 else "failed_or_no_accepted_actions")
        except Exception as error:
            report["counts"]["errors"] += 1
            report.update(error_type=type(error).__name__, error=str(error), outcome="failed")
            emit("error", error_type=type(error).__name__, error=str(error))
        summary_fd = os.open(args.report_dir / "summary.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(summary_fd, "w", encoding="utf-8") as summary:
            json.dump(report, summary, indent=2, allow_nan=False)
            summary.write("\n")
    print(json.dumps({"passed": report["passed"], "state_source": STATE_SOURCE,
                      "noRobot": True, "noMotion": True, "counts": report["counts"]}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
