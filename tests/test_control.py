"""Exercise shadow tracking geometry and rejection behavior without hardware."""

import math
import unittest
from dataclasses import replace

from b2_tic_vla.control import Limits, PathTracker
from b2_tic_vla.types import Frame, Plan, RobotState, Velocity, Waypoint


def observation(now=10.0, points=None):
    frame = Frame("unused.jpg", now, captured_at=now, timestamp_verified=True)
    state = RobotState(now, 0, 0, 0, 0, 0, 0, velocity_frame="body")
    plan = Plan(
        points if points is not None else (Waypoint(0.4, 0.1, 0.5),),
        created_at=now, observation_at=now, source="test",
    )
    return frame, state, plan


class PathTrackerTests(unittest.TestCase):
    def test_straight_path_starts_with_bounded_acceleration_and_no_lateral_motion(self):
        frame, state, plan = observation(points=(Waypoint(0.5, 0, 0.5),))
        decision = PathTracker().evaluate(frame, state, plan, 10)
        self.assertTrue(decision.accepted)
        self.assertTrue(decision.capture_time_verified)
        self.assertAlmostEqual(decision.command.vx, 0.02)
        self.assertEqual(decision.command.vy, 0)
        self.assertEqual(decision.command.yaw_rate, 0)

    def test_left_and_right_curves_have_matching_yaw_signs(self):
        for sign in (1, -1):
            args = observation(points=(Waypoint(0.4, sign * 0.2, 0.5),))
            command = PathTracker().evaluate(*args, 10).command
            self.assertGreater(sign * command.yaw_rate, 0)

    def test_repeated_tight_curve_respects_speed_yaw_and_acceleration_caps(self):
        limits = Limits(cruise_speed_mps=0.2)
        tracker = PathTracker(limits)
        previous = Velocity()
        for index in range(30):
            now = 10 + 0.1 * index
            frame, state, plan = observation(now, (Waypoint(0.01, 0.2, 0.5),))
            result = tracker.evaluate(frame, state, plan, now)
            self.assertTrue(result.accepted)
            command = result.command
            self.assertLessEqual(command.vx, limits.max_forward_mps)
            self.assertLessEqual(abs(command.yaw_rate), limits.max_yaw_rps)
            self.assertLessEqual(abs(command.vx - previous.vx), limits.max_accel_mps2 * 0.1 + 1e-12)
            self.assertLessEqual(abs(command.yaw_rate - previous.yaw_rate),
                                 limits.max_yaw_accel_rps2 * 0.1 + 1e-12)
            self.assertEqual(command.vy, 0)
            previous = command

    def test_unknown_capture_time_is_explicitly_shadow_only(self):
        frame, state, plan = observation()
        frame = replace(frame, captured_at=None, timestamp_verified=False)
        result = PathTracker().evaluate(frame, state, plan, 10)
        self.assertTrue(result.accepted)
        self.assertFalse(result.capture_time_verified)
        self.assertEqual(result.reason, "shadow_only_capture_time_unknown")

    def test_time_and_freshness_failures_return_zero_commands(self):
        frame, state, plan = observation()
        cases = [
            (replace(frame, received_at=float("nan")), state, plan, "invalid_timestamp"),
            (frame, replace(state, received_at=10.1), plan, "timestamp_in_future"),
            (frame, state, replace(plan, created_at=9.9), "plan_predates_observation"),
            (replace(frame, captured_at=None), state, plan, "missing_verified_capture_time"),
            (replace(frame, captured_at=10.01), state, plan, "invalid_capture_time"),
            (replace(frame, captured_at=9.4), state, plan, "stale_image"),
            (frame, replace(state, received_at=9.4), plan, "stale_state"),
            (frame, state, replace(plan, created_at=9.4, observation_at=9.3), "stale_plan"),
            (frame, state, replace(plan, observation_at=9.4), "stale_plan_observation"),
            (replace(frame, timestamp_verified="yes"), state, plan, "invalid_capture_verification"),
        ]
        for image, robot, path, reason in cases:
            with self.subTest(reason=reason):
                result = PathTracker().evaluate(image, robot, path, 10)
                self.assertFalse(result.accepted)
                self.assertEqual(result.command, Velocity())
                self.assertEqual(result.reason, reason)

    def test_image_state_and_plan_skew_are_checked_independently(self):
        frame, state, plan = observation()
        limits = Limits(max_timestamp_skew_s=0.1)
        cases = [
            (frame, replace(state, received_at=9.8), plan, "state_image_skew"),
            (frame, state, replace(plan, observation_at=9.8), "plan_image_mismatch"),
        ]
        for image, robot, path, reason in cases:
            result = PathTracker(limits).evaluate(image, robot, path, 10)
            self.assertEqual(result.reason, reason)
            self.assertEqual(result.command, Velocity())

    def test_malformed_state_and_paths_are_rejected(self):
        frame, state, plan = observation()
        cases = [
            (replace(state, vx=float("inf")), plan, "invalid_state"),
            (replace(state, velocity_frame="unknown"), plan, "unconfirmed_velocity_frame"),
            (state, replace(plan, frame_id="map"), "unsupported_plan_frame"),
            (state, replace(plan, points=()), "empty_plan"),
            (state, replace(plan, points=(Waypoint(-1, 0, 1),)), "no_forward_target"),
            (state, replace(plan, points=(Waypoint(1, float("nan"), 1),)), "invalid_waypoint"),
            (state, replace(plan, points=(Waypoint(1, 0, 0),)), "invalid_waypoint_timing"),
            (state, replace(plan, points=(Waypoint(1, 0, 1), Waypoint(2, 0, 0.5))),
             "invalid_waypoint_timing"),
        ]
        for robot, path, reason in cases:
            with self.subTest(reason=reason):
                result = PathTracker().evaluate(frame, robot, path, 10)
                self.assertFalse(result.accepted)
                self.assertEqual(result.command, Velocity())
                self.assertEqual(result.reason, reason)

    def test_large_finite_geometry_never_produces_nan(self):
        args = observation(points=(Waypoint(1e308, 1e308, 1),))
        result = PathTracker().evaluate(*args, 10)
        self.assertTrue(result.accepted)
        self.assertTrue(math.isfinite(result.command.vx))
        self.assertTrue(math.isfinite(result.command.yaw_rate))
        args = observation(points=(Waypoint(1.7e308, 1.7e308, 1),))
        result = PathTracker().evaluate(*args, 10)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason, "invalid_waypoint_geometry")
        args = observation(points=(Waypoint(10 ** 1000, 0, 1),))
        self.assertEqual(PathTracker().evaluate(*args, 10).reason, "invalid_waypoint")

    def test_clock_regression_rejects_and_resets_command(self):
        tracker = PathTracker()
        self.assertTrue(tracker.evaluate(*observation(), 10).accepted)
        result = tracker.evaluate(*observation(9.9), 9.9)
        self.assertEqual(result.reason, "clock_went_backwards")
        self.assertEqual(result.command, Velocity())

    def test_long_pause_does_not_allow_large_acceleration_jump(self):
        tracker = PathTracker()
        first = tracker.evaluate(*observation(10), 10)
        second = tracker.evaluate(*observation(100), 100)
        self.assertAlmostEqual(second.command.vx - first.command.vx, 0.02)

    def test_rejection_clears_previous_command(self):
        tracker = PathTracker()
        tracker.evaluate(*observation(10), 10)
        frame, state, plan = observation(10.1)
        rejected = tracker.evaluate(frame, state, replace(plan, points=()), 10.1)
        self.assertEqual(rejected.command, Velocity())
        next_result = tracker.evaluate(*observation(10.11), 10.11)
        self.assertAlmostEqual(next_result.command.vx, 0.002)

    def test_invalid_limits_are_rejected(self):
        for value in (0, -1, True, "fast", float("nan"), float("inf"), 10 ** 1000):
            with self.subTest(value=str(value)[:30]), self.assertRaises(ValueError):
                Limits(max_forward_mps=value)
        with self.assertRaises(ValueError):
            Limits(max_forward_mps=0.05, cruise_speed_mps=0.1)


if __name__ == "__main__":
    unittest.main()
