"""Explicit data contracts. Host timing fields use time.monotonic() seconds."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Frame:
    path: str
    received_at: float
    captured_at: float | None = None
    source_timestamp: float | None = None
    source_clock: str | None = None
    timestamp_verified: bool = False


@dataclass(frozen=True)
class RobotState:
    received_at: float
    x: float
    y: float
    yaw: float
    vx: float
    vy: float
    yaw_rate: float
    source_timestamp: float | None = None
    source_clock: str | None = None
    frame_id: str = "unknown"
    velocity_frame: str = "unknown"


@dataclass(frozen=True)
class Waypoint:
    x: float
    y: float
    time_from_now: float


@dataclass(frozen=True)
class Plan:
    points: tuple[Waypoint, ...]
    created_at: float
    observation_at: float
    source: str
    frame_id: str = "base_link"
    cache_reference_at: float | None = None


@dataclass(frozen=True)
class Velocity:
    vx: float = 0.0
    vy: float = 0.0
    yaw_rate: float = 0.0
