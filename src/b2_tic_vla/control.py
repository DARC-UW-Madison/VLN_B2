"""Testable path tracking and data validation, with no hardware imports or I/O."""

from __future__ import annotations

import math
from dataclasses import dataclass, fields

from .types import Frame, Plan, RobotState, Velocity


@dataclass(frozen=True)
class Limits:
    """Example commissioning limits, not validated B2 operating limits."""

    max_forward_mps: float = 0.20
    max_yaw_rps: float = 0.30
    max_accel_mps2: float = 0.20
    max_yaw_accel_rps2: float = 0.50
    cruise_speed_mps: float = 0.10
    lookahead_m: float = 0.40
    max_observation_age_s: float = 0.50
    max_state_age_s: float = 0.50
    max_plan_age_s: float = 0.50
    max_timestamp_skew_s: float = 0.20

    def __post_init__(self) -> None:
        for item in fields(self):
            value = getattr(self, item.name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{item.name} must be a number")
            try:
                valid = math.isfinite(value) and value > 0
            except OverflowError:
                valid = False
            if not valid:
                raise ValueError(f"{item.name} must be finite and positive")
        if self.cruise_speed_mps > self.max_forward_mps:
            raise ValueError("cruise_speed_mps exceeds max_forward_mps")


@dataclass(frozen=True)
class Decision:
    command: Velocity
    accepted: bool
    reason: str
    capture_time_verified: bool


def _finite(*values: float) -> bool:
    try:
        return all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            for value in values
        )
    except OverflowError:
        return False


def _slew(target: float, previous: float, rate: float, dt: float) -> float:
    return previous + max(-rate * dt, min(rate * dt, target - previous))


class PathTracker:
    """Forward-only lookahead tracker. Lateral velocity is always zero.

    All times must share a host monotonic clock. Receipt freshness is checked
    independently from capture freshness. An accepted shadow prediction with
    unknown capture timing is not cleared for physical motion.
    """

    def __init__(self, limits: Limits | None = None) -> None:
        self.limits = limits or Limits()
        self._previous = Velocity()
        self._last_time: float | None = None

    def _reject(self, reason: str, now: float) -> Decision:
        self._previous = Velocity()
        self._last_time = now if _finite(now) else None
        return Decision(Velocity(), False, reason, False)

    def evaluate(self, frame: Frame, state: RobotState, plan: Plan, now: float) -> Decision:
        lim = self.limits
        times = (now, frame.received_at, state.received_at, plan.created_at, plan.observation_at)
        if not _finite(*times):
            return self._reject("invalid_timestamp", now)
        if any(value > now + 0.001 for value in times[1:]):
            return self._reject("timestamp_in_future", now)
        if plan.created_at < plan.observation_at:
            return self._reject("plan_predates_observation", now)
        if not isinstance(frame.timestamp_verified, bool):
            return self._reject("invalid_capture_verification", now)
        if frame.timestamp_verified and frame.captured_at is None:
            return self._reject("missing_verified_capture_time", now)
        if frame.captured_at is not None and (
            not _finite(frame.captured_at)
            or frame.captured_at > frame.received_at + 0.001
        ):
            return self._reject("invalid_capture_time", now)
        observation_time = (
            frame.captured_at if frame.timestamp_verified else frame.received_at
        )
        if now - observation_time > lim.max_observation_age_s:
            return self._reject("stale_image", now)
        if now - state.received_at > lim.max_state_age_s:
            return self._reject("stale_state", now)
        if now - plan.created_at > lim.max_plan_age_s:
            return self._reject("stale_plan", now)
        if now - plan.observation_at > lim.max_observation_age_s:
            return self._reject("stale_plan_observation", now)
        if abs(plan.observation_at - observation_time) > lim.max_timestamp_skew_s:
            return self._reject("plan_image_mismatch", now)
        if abs(state.received_at - frame.received_at) > lim.max_timestamp_skew_s:
            return self._reject("state_image_skew", now)
        if not _finite(state.x, state.y, state.yaw, state.vx, state.vy, state.yaw_rate):
            return self._reject("invalid_state", now)
        if state.velocity_frame not in {"body", "base_link"}:
            return self._reject("unconfirmed_velocity_frame", now)
        if plan.frame_id != "base_link":
            return self._reject("unsupported_plan_frame", now)
        if not plan.points:
            return self._reject("empty_plan", now)
        previous_offset = 0.0
        for point in plan.points:
            if not _finite(point.x, point.y, point.time_from_now):
                return self._reject("invalid_waypoint", now)
            if not math.isfinite(math.hypot(point.x, point.y)):
                return self._reject("invalid_waypoint_geometry", now)
            if point.time_from_now <= previous_offset:
                return self._reject("invalid_waypoint_timing", now)
            previous_offset = point.time_from_now
        if self._last_time is not None and now < self._last_time:
            return self._reject("clock_went_backwards", now)

        forward = [point for point in plan.points if point.x > 0.001]
        if not forward:
            return self._reject("no_forward_target", now)
        target = next(
            (p for p in forward if math.hypot(p.x, p.y) >= lim.lookahead_m), forward[-1]
        )
        # Normalize before dividing again: x*x+y*y and 2*y can overflow even
        # when the coordinates and their Euclidean distance are finite.
        distance = math.hypot(target.x, target.y)
        curvature = 2.0 * (target.y / distance) / distance
        vx = min(lim.cruise_speed_mps, lim.max_forward_mps)
        if abs(curvature) > 1e-9:
            vx = min(vx, lim.max_yaw_rps / abs(curvature))
        yaw_rate = max(-lim.max_yaw_rps, min(lim.max_yaw_rps, vx * curvature))
        # Do not let a long pause create an unlimited first-step acceleration.
        dt = min(0.10, now - self._last_time) if self._last_time is not None else 0.10
        vx = _slew(vx, self._previous.vx, lim.max_accel_mps2, dt)
        yaw_rate = _slew(yaw_rate, self._previous.yaw_rate, lim.max_yaw_accel_rps2, dt)
        if not _finite(vx, yaw_rate):
            return self._reject("invalid_command", now)
        command = Velocity(vx=vx, vy=0.0, yaw_rate=yaw_rate)
        self._previous = command
        self._last_time = now
        reason = "accepted" if frame.timestamp_verified else "shadow_only_capture_time_unknown"
        return Decision(command, True, reason, frame.timestamp_verified)
