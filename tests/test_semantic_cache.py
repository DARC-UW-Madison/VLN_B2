"""Exercise cache/reference races and freshness without models, workers or devices."""

from dataclasses import replace
import math
import unittest

from b2_tic_vla.semantic_cache import CacheLimits, Observation, SemanticCache
from b2_tic_vla.types import Frame, RobotState


def observation(at, x=0., y=0., yaw=0.):
    return Observation(Frame("immutable-frame.jpg", at, captured_at=at, timestamp_verified=True),
                       RobotState(at, x, y, yaw, .1, .0, .2, frame_id="odom", velocity_frame="body"),
                       "Go ahead", state_timing_verified=True, pose_frame_verified=True,
                       state_aligned_at=at)


class SemanticCacheTests(unittest.TestCase):
    def setUp(self):
        self.cache = SemanticCache()
        self.limits = CacheLimits(20., .5, .5, .2)

    def publish(self, obs=None, completed=110.):
        request = self.cache.begin(obs or observation(100.), 100.)
        self.assertTrue(self.cache.publish(request, object(), completed))
        return request

    def test_new_request_does_not_change_published_pose_time_or_payload(self):
        request = self.publish(observation(100., x=1., y=2., yaw=math.pi / 2))
        before = self.cache.select(observation(110., x=1., y=3.), 110.1, self.limits).context
        self.cache.begin(observation(110., x=99., y=99.), 110.)
        after = self.cache.select(observation(110., x=1., y=3.), 110.1, self.limits).context
        self.assertIs(before.snapshot, after.snapshot)
        self.assertIs(after.snapshot.request, request)
        self.assertAlmostEqual(after.dx_m, 1.)
        self.assertAlmostEqual(after.dy_m, 0.)
        self.assertAlmostEqual(after.semantic_age_s, 10.1)
        self.assertAlmostEqual(after.observation_delay_s, 10.)
        self.assertEqual(after.state_features[:3], (.1, .0, .2))

    def test_superseded_or_reset_inflight_result_cannot_publish(self):
        first = self.cache.begin(observation(100.), 100.)
        second = self.cache.begin(observation(101.), 101.)
        self.assertTrue(self.cache.publish(second, object(), 110.))
        self.assertFalse(self.cache.publish(first, object(), 111.))
        snapshot = self.cache.select(observation(110.), 110.1, self.limits).context.snapshot
        self.assertTrue(self.cache.is_current(snapshot))
        third = self.cache.begin(observation(111.), 111.)
        self.cache.reset()
        self.assertFalse(self.cache.publish(third, object(), 112.))
        self.assertFalse(self.cache.is_current(snapshot))
        self.assertEqual(self.cache.select(observation(112.), 112., self.limits).reason,
                         "no_semantic_cache")

    def test_age_includes_inference_time_even_when_publication_is_recent(self):
        self.publish(completed=110.)
        result = self.cache.select(observation(110.), 110.1, replace(self.limits, max_semantic_age_s=5.))
        self.assertEqual(result.reason, "stale_semantic_cache")

    def test_unknown_clock_is_explicitly_shadow_only_and_uses_consistent_receipts(self):
        old = observation(100.)
        old = replace(old, frame=replace(old.frame, captured_at=None, timestamp_verified=False))
        self.publish(old)
        current = observation(110.)
        self.assertEqual(self.cache.select(current, 110.1, self.limits).reason,
                         "unverified_clock_or_pose_frame")
        context = self.cache.select(current, 110.1, self.limits, shadow_only=True).context
        self.assertTrue(context.shadow_only)
        self.assertEqual(context.timing_basis, "receipt_lower_bound")
        self.assertAlmostEqual(context.observation_delay_s, 10.)

    def test_instruction_pose_and_freshness_are_independent_gates(self):
        self.publish()
        current = observation(110.)
        cases = [
            (replace(current, instruction="Turn left"), "instruction_changed"),
            (replace(current, state=replace(current.state, frame_id="different")),
             "pose_frame_mismatch_or_unknown"),
            (replace(current, state=replace(current.state, received_at=109.), state_aligned_at=109.),
             "stale_state"),
            (replace(current, frame=replace(current.frame, received_at=109., captured_at=109.)),
             "stale_observation"),
        ]
        for value, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(self.cache.select(value, 110.1, self.limits).reason, reason)

    def test_fresh_receipts_do_not_hide_misaligned_or_old_source_samples(self):
        old = observation(100.)
        old = replace(old, frame=replace(old.frame, captured_at=90.))
        self.publish(old)
        self.assertEqual(self.cache.select(observation(110.), 110.1, self.limits).reason,
                         "image_state_capture_skew")
        self.cache.reset()
        self.publish()
        current = observation(110.)
        current = replace(current, frame=replace(current.frame, captured_at=109.4),
                          state_aligned_at=109.4)
        self.assertEqual(self.cache.select(current, 110.1, self.limits).reason,
                         "stale_state_sample")

    def test_invalid_time_limit_and_overflowing_geometry_fail_closed(self):
        with self.assertRaises(ValueError):
            CacheLimits(float("nan"), .5, .5, .2)
        request = self.cache.begin(observation(100.), 100.)
        with self.assertRaises(ValueError):
            self.cache.publish(request, object(), 99.)
        self.cache.publish(request, object(), 110.)
        self.assertEqual(self.cache.select(observation(111.), 110.1, self.limits).reason,
                         "timestamp_in_future")
        self.cache.reset()
        self.publish(observation(100., x=-1e308))
        self.assertEqual(self.cache.select(observation(110., x=1e308), 110.1, self.limits).reason,
                         "invalid_relative_geometry")


if __name__ == "__main__":
    unittest.main()
