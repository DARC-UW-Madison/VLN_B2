"""Atomic semantic-cache references and input gates; no workers, SDK or motor I/O."""

from __future__ import annotations

from dataclasses import dataclass, fields
import math
import threading
from typing import Any

from .types import Frame, RobotState


def _finite(*values):
    try:
        return all(isinstance(v, (float, int)) and not isinstance(v, bool)
                   and math.isfinite(v) for v in values)
    except OverflowError:
        return False


@dataclass(frozen=True)
class Observation:
    """Planar pose experiment; pose verification must include the yaw-only assumption."""

    frame: Frame
    state: RobotState
    instruction: str
    state_timing_verified: bool = False
    pose_frame_verified: bool = False


@dataclass(frozen=True)
class CacheLimits:
    """Explicit experimental limits; no default is an approved B2 operating limit."""

    max_semantic_age_s: float
    max_observation_age_s: float
    max_state_age_s: float
    max_pair_skew_s: float

    def __post_init__(self):
        if any(not _finite(getattr(self, f.name)) or getattr(self, f.name) <= 0
               for f in fields(self)):
            raise ValueError("Every cache limit must be finite and positive")


@dataclass(frozen=True)
class SemanticRequest:
    sequence: int
    observation: Observation
    requested_at: float


@dataclass(frozen=True)
class SemanticSnapshot:
    request: SemanticRequest
    payload: Any
    completed_at: float


@dataclass(frozen=True)
class ActionContext:
    snapshot: SemanticSnapshot
    semantic_age_s: float
    observation_delay_s: float
    dx_m: float
    dy_m: float
    state_features: tuple[float, float, float, float, float, float]
    timing_basis: str
    shadow_only: bool


@dataclass(frozen=True)
class CacheDecision:
    context: ActionContext | None
    reason: str


def _validate(observation):
    frame, state = observation.frame, observation.state
    if not isinstance(observation.instruction, str) or not observation.instruction.strip():
        raise ValueError("A nonempty instruction is required")
    if any(not isinstance(value, str) or not value.strip()
           for value in (state.frame_id, state.velocity_frame)):
        raise ValueError("Pose and velocity frame identifiers must be nonempty strings")
    if not _finite(frame.received_at, state.received_at, state.x, state.y, state.yaw,
                   state.vx, state.vy, state.yaw_rate):
        raise ValueError("Observation times, poses and velocities must be finite")
    for value in (frame.timestamp_verified, observation.state_timing_verified,
                  observation.pose_frame_verified):
        if type(value) is not bool:
            raise ValueError("Timing/frame verification flags must be booleans")
    if frame.timestamp_verified and frame.captured_at is None:
        raise ValueError("Verified image timing requires a capture time")
    if frame.captured_at is not None and (
        not _finite(frame.captured_at) or frame.captured_at > frame.received_at + 0.001
    ):
        raise ValueError("Image capture time must be finite and no later than receipt")


class SemanticCache:
    """Publish a payload with its original observation in one locked update.

    Payload ownership transfers to the snapshot: callers must not mutate its
    tensors. Each observation must name an immutable image file. Beginning a
    request leaves the published snapshot intact; superseded/reset requests
    cannot publish later. This class starts no threads or background service.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._sequence = 0
        self._pending = None
        self._snapshot = None

    def begin(self, observation: Observation, requested_at: float) -> SemanticRequest:
        _validate(observation)
        if not _finite(requested_at) or requested_at < max(
            observation.frame.received_at, observation.state.received_at
        ):
            raise ValueError("Request time must follow observation receipt on the host clock")
        with self._lock:
            self._sequence += 1
            self._pending = SemanticRequest(self._sequence, observation, requested_at)
            return self._pending

    def publish(self, request: SemanticRequest, payload: Any, completed_at: float) -> bool:
        if payload is None or not _finite(completed_at) or completed_at < request.requested_at:
            raise ValueError("A completed cache needs a payload and valid completion time")
        with self._lock:
            if request is not self._pending:
                return False
            self._snapshot = SemanticSnapshot(request, payload, completed_at)
            self._pending = None
            return True

    def reset(self):
        with self._lock:
            self._pending = self._snapshot = None

    def is_current(self, snapshot: SemanticSnapshot) -> bool:
        """Recheck after action computation; an independent command gate remains necessary."""
        with self._lock:
            return self._snapshot is snapshot

    def select(self, current: Observation, now: float, limits: CacheLimits,
               *, shadow_only: bool = False) -> CacheDecision:
        _validate(current)
        if type(shadow_only) is not bool or not _finite(now):
            raise ValueError("Provide a finite host time and boolean shadow mode")
        with self._lock:
            snapshot = self._snapshot
        if snapshot is None:
            return CacheDecision(None, "no_semantic_cache")
        reference = snapshot.request.observation
        frame, state = current.frame, current.state
        old_frame, old_state = reference.frame, reference.state
        if reference.instruction != current.instruction:
            return CacheDecision(None, "instruction_changed")
        if any(t > now + 0.001 for t in (
            frame.received_at, state.received_at, snapshot.completed_at,
            snapshot.request.requested_at,
        )):
            return CacheDecision(None, "timestamp_in_future")
        if now - frame.received_at > limits.max_observation_age_s:
            return CacheDecision(None, "stale_observation")
        if now - state.received_at > limits.max_state_age_s:
            return CacheDecision(None, "stale_state")
        if any(abs(o.frame.received_at - o.state.received_at) > limits.max_pair_skew_s
               for o in (reference, current)):
            return CacheDecision(None, "image_state_receipt_skew")
        if state.frame_id in {"", "unknown"} or state.frame_id != old_state.frame_id:
            return CacheDecision(None, "pose_frame_mismatch_or_unknown")
        if any(s.velocity_frame not in {"body", "base_link"} for s in (old_state, state)):
            return CacheDecision(None, "unconfirmed_velocity_frame")
        verified = all(o.frame.timestamp_verified and o.state_timing_verified
                       and o.pose_frame_verified for o in (reference, current))
        if not verified and not shadow_only:
            return CacheDecision(None, "unverified_clock_or_pose_frame")
        use_capture_time = old_frame.timestamp_verified and frame.timestamp_verified
        reference_at = old_frame.captured_at if use_capture_time else old_frame.received_at
        current_at = frame.captured_at if use_capture_time else frame.received_at
        age, delay = now - reference_at, current_at - reference_at
        if delay < 0 or age < 0:
            return CacheDecision(None, "observation_predates_cache_reference")
        if age > limits.max_semantic_age_s:
            return CacheDecision(None, "stale_semantic_cache")
        if now - current_at > limits.max_observation_age_s:
            return CacheDecision(None, "stale_capture")
        world_dx, world_dy = state.x - old_state.x, state.y - old_state.y
        c, s = math.cos(old_state.yaw), math.sin(old_state.yaw)
        dx, dy = c * world_dx + s * world_dy, -s * world_dx + c * world_dy
        if not _finite(dx, dy, age, delay):
            return CacheDecision(None, "invalid_relative_geometry")
        features = (state.vx, state.vy, state.yaw_rate, dx, dy, delay)
        context = ActionContext(snapshot, age, delay, dx, dy, features,
                                "verified_capture" if use_capture_time else "receipt_lower_bound",
                                shadow_only or not verified)
        if not self.is_current(snapshot):
            return CacheDecision(None, "cache_changed_during_selection")
        return CacheDecision(context, "shadow_only" if context.shadow_only else "metadata_accepted")
