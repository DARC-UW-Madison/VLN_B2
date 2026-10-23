"""Observation and offline evaluation commands. No motor client is imported."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

from .control import Limits, PathTracker
from .recording import read_observation, write_json, write_observation
from .types import Frame, Plan, RobotState, Waypoint


def _read_json(path: str) -> dict:
    with Path(path).open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("Expected an object with schema_version 1")
    return value


def _unused_output(path: str) -> Path:
    target = Path(path)
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite {target}")
    return target


def _replay(args: argparse.Namespace) -> dict:
    record = _read_json(args.input)
    limits = Limits(**_read_json(args.limits)["limits"])
    tracker = PathTracker(limits)
    samples = record["samples"]
    if not isinstance(samples, list) or not samples:
        raise ValueError("Replay requires a nonempty samples list")
    decisions = []
    for sample in samples:
        frame = Frame(
            path="synthetic", received_at=sample["image_received_at"],
            captured_at=sample.get("image_captured_at"),
            timestamp_verified=sample.get("image_captured_at") is not None,
        )
        state = RobotState(sample["state_received_at"], 0, 0, 0, 0, 0, 0,
                           frame_id="synthetic", velocity_frame="body")
        plan = Plan(tuple(Waypoint(*point) for point in sample["points"]),
                    sample["plan_created_at"], sample["plan_observation_at"], "synthetic")
        decision = tracker.evaluate(frame, state, plan, sample["now"])
        decisions.append({"now": sample["now"], **asdict(decision)})
    return {"schema_version": 1, "mode": "synthetic_replay", "motion_sent": False,
            "limits": asdict(limits), "decisions": decisions}


def _camera(args: argparse.Namespace) -> dict:
    from .hardware import ZedCamera

    target = _unused_output(args.output)
    if target.suffix.lower() not in {".jpg", ".jpeg"}:
        raise ValueError("ZED capture output must use a .jpg or .jpeg extension")
    sidecar = _unused_output(str(target) + ".json")
    target.parent.mkdir(parents=True, exist_ok=True)
    camera = ZedCamera()
    try:
        camera.open()
        frame = camera.capture(str(target))
    finally:
        camera.close()
    result = {"schema_version": 1, "mode": "camera_probe", "motion_sent": False,
              "frame": asdict(frame)}
    write_json(sidecar, result)
    return result


def _duration(value: str) -> float:
    seconds = float(value)
    if not math.isfinite(seconds) or not 0 < seconds <= 60:
        raise argparse.ArgumentTypeError("seconds must be between 0 and 60")
    return seconds


def _reader(args: argparse.Namespace):
    from .hardware import UnitreeStateReader

    return UnitreeStateReader(args.interface, args.domain_id, args.topic)


def _state(args: argparse.Namespace) -> dict:
    reader = _reader(args)
    try:
        reader.open()
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline:
            time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        latest = reader.latest()
        return {"schema_version": 1, "mode": "state_probe", "motion_sent": False,
                "stats": reader.stats(), "state": asdict(latest) if latest else None}
    finally:
        reader.close()


def _record(args: argparse.Namespace) -> dict:
    from .hardware import ZedCamera

    target = _unused_output(args.output_dir)
    reader = _reader(args)
    camera = ZedCamera()
    target.mkdir(parents=True)
    try:
        reader.open()
        camera.open()
        deadline = time.monotonic() + 5
        while reader.latest() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if reader.latest() is None:
            raise RuntimeError("No finite B2 state received within five seconds")
        frame = camera.capture(str(target / "frame.jpg"))
        state = reader.latest()
        if state is None or abs(state.received_at - frame.received_at) > 0.2:
            raise RuntimeError("Image/state receipt skew exceeds 0.2 seconds; retry in a new directory")
        state = replace(state, velocity_frame=args.velocity_frame, frame_id=args.position_frame)
        write_observation(target / "observation.json", frame, state)
        return {"schema_version": 1, "mode": "observation_record", "motion_sent": False,
                "manifest": str(target / "observation.json"), "stats": reader.stats(),
                "capture_time_verified": frame.timestamp_verified}
    finally:
        try:
            camera.close()
        finally:
            reader.close()


def _infer(args: argparse.Namespace) -> dict:
    if not isinstance(args.instruction, str) or not args.instruction.strip():
        raise ValueError("A nonempty navigation instruction is required")
    frame, state = read_observation(args.observation)
    if args.velocity_frame:
        state = replace(state, velocity_frame=args.velocity_frame)
    if state.velocity_frame not in {"body", "base_link"}:
        raise ValueError(
            "Observation velocity frame is unknown or unsupported; verify the SDK convention "
            "and use --velocity-frame body or base_link only after confirming it"
        )
    if Path(frame.path).stat().st_size == 0:
        raise ValueError("Observation image is empty")
    from .inference import TicVlaPredictor

    predictor = TicVlaPredictor(args.base_model, args.checkpoint,
                                device=args.device, upstream_root=args.upstream_root)
    predictor.load()
    # Replay starts a new host-clock interval; recorded clocks are retained separately.
    started = time.monotonic()
    plan = predictor.predict([frame.path], args.instruction.strip(), state, started)
    return {"schema_version": 1, "mode": "offline_synchronous_inference",
            "motion_sent": False, "plan": asdict(plan), "model": predictor.describe(),
            "inference_seconds": time.monotonic() - started,
            "recorded_frame": asdict(frame), "recorded_state": asdict(state),
            "timing_note": "Plan timing is rebased for replay; this is not a live observation."}


def _add_state_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--interface", required=True, help="Explicit B2 network interface")
    parser.add_argument("--domain-id", type=int, default=0)
    parser.add_argument("--topic", choices=["auto", "rt/sportmodestate", "rt/lf/sportmodestate"],
                        default="auto")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    replay = commands.add_parser("replay", help="Evaluate synthetic paths without hardware or models")
    replay.add_argument("--input", default="examples/replay.json")
    replay.add_argument("--limits", default="examples/commissioning.json")
    replay.add_argument("--output")
    replay.set_defaults(run=_replay)
    camera = commands.add_parser("camera", help="Capture one ZED left image; no motor output")
    camera.add_argument("--output", required=True)
    camera.set_defaults(run=_camera)
    state = commands.add_parser("state", help="Subscribe to B2 state; no motor output")
    _add_state_options(state)
    state.add_argument("--seconds", type=_duration, default=3.0)
    state.add_argument("--output")
    state.set_defaults(run=_state)
    record = commands.add_parser("record", help="Save one image/state observation; no motor output")
    _add_state_options(record)
    record.add_argument("--output-dir", required=True)
    record.add_argument("--velocity-frame", choices=["unknown", "body", "base_link"], default="unknown",
                        help="Set body/base_link only after verifying the SDK velocity convention")
    record.add_argument("--position-frame", default="unknown")
    record.set_defaults(run=_record)
    infer = commands.add_parser("infer", help="Run synchronous offline inference from existing local files")
    infer.add_argument("--observation", required=True)
    infer.add_argument("--instruction", required=True)
    infer.add_argument("--base-model", required=True)
    infer.add_argument("--checkpoint", required=True)
    infer.add_argument("--upstream-root")
    infer.add_argument("--device", default="cuda:0")
    infer.add_argument("--velocity-frame", choices=["body", "base_link"],
                       help="Override only after verifying the SDK velocity convention")
    infer.add_argument("--output")
    infer.set_defaults(run=_infer)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command != "camera" and getattr(args, "output", None):
            _unused_output(args.output)
        result = args.run(args)
        if args.command != "camera" and getattr(args, "output", None):
            write_json(args.output, result)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 2 if args.command == "state" and result["state"] is None else 0
    except KeyboardInterrupt:
        print("Interrupted; no motor output was enabled.", file=sys.stderr)
        return 130
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, AttributeError, ImportError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
