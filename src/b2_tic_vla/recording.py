"""Portable observation manifests; raw hardware records stay outside Git."""

from __future__ import annotations

import json
import math
import os
from dataclasses import asdict
from pathlib import Path

from .types import Frame, RobotState


def write_json(path: str | Path, value: object) -> None:
    target = Path(path)
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite {target}")
    # Validate serialization before creating a file, so invalid numbers cannot
    # leave a truncated manifest that resembles a finished observation.
    content = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(content)


def _number(value: object, field: str) -> None:
    try:
        valid = (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"Observation {field} must be a finite number")


def _text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Observation {field} must be a non-empty string")


def _validate(frame: Frame, state: RobotState) -> None:
    _text(frame.path, "frame.path")
    _number(frame.received_at, "frame.received_at")
    _number(state.received_at, "state.received_at")
    for name in ("x", "y", "yaw", "vx", "vy", "yaw_rate"):
        _number(getattr(state, name), f"state.{name}")
    for name in ("frame_id", "velocity_frame"):
        _text(getattr(state, name), f"state.{name}")
    if not isinstance(frame.timestamp_verified, bool):
        raise ValueError("Observation frame.timestamp_verified must be a boolean")
    if frame.timestamp_verified and frame.captured_at is None:
        raise ValueError("Verified capture timing requires frame.captured_at")
    if frame.captured_at is not None:
        _number(frame.captured_at, "frame.captured_at")
        if frame.captured_at > frame.received_at + 0.001:
            raise ValueError("Observation capture time is later than receipt time")
    for label, item in (("frame", frame), ("state", state)):
        if item.source_timestamp is not None:
            _number(item.source_timestamp, f"{label}.source_timestamp")
            _text(item.source_clock, f"{label}.source_clock")
        elif item.source_clock is not None:
            _text(item.source_clock, f"{label}.source_clock")


def write_observation(path: str | Path, frame: Frame, state: RobotState) -> None:
    """Store receipt/capture times separately; receipt is not exposure time."""
    _validate(frame, state)
    target = Path(path)
    image_path = Path(frame.path).resolve()
    if not image_path.is_file():
        raise ValueError("Observation image does not exist")
    frame_record = asdict(frame)
    frame_record["path"] = os.path.relpath(image_path, target.resolve().parent)
    write_json(
        target,
        {"schema_version": 1, "frame": frame_record, "state": asdict(state)},
    )


def read_observation(path: str | Path) -> tuple[Frame, RobotState]:
    target = Path(path)
    with target.open(encoding="utf-8") as handle:
        record = json.load(handle)
    if not isinstance(record, dict):
        raise ValueError("Observation manifest must be a JSON object")
    if type(record.get("schema_version")) is not int or record["schema_version"] != 1:
        raise ValueError("Unsupported observation schema_version")
    if not isinstance(record.get("frame"), dict) or not isinstance(record.get("state"), dict):
        raise ValueError("Observation requires frame and state objects")
    frame_data = dict(record["frame"])
    _text(frame_data.get("path"), "frame.path")
    image_path = (target.parent / frame_data["path"]).resolve()
    if not image_path.is_file():
        raise ValueError("Observation image does not exist")
    frame_data["path"] = str(image_path)
    try:
        frame = Frame(**frame_data)
        state = RobotState(**record["state"])
    except TypeError as exc:
        raise ValueError(f"Observation fields do not match the schema: {exc}") from exc
    _validate(frame, state)
    return frame, state
