"""Manifest trust and bounded worker lifecycle, without a model or robot."""

from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from b2_tic_vla.semantic_cache import Observation
from b2_tic_vla.types import Frame, RobotState

SPEC = importlib.util.spec_from_file_location(
    "observe_async", Path(__file__).resolve().parents[1] / "tools/observe_async.py"
)
observer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(observer)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.image = self.root / "frame-000001.jpg"
        self.image.write_bytes(b"\xff\xd8mock jpeg")
        self.frame = Frame(self.image.name, 100., source_timestamp=20.,
                           source_clock="zed_image_unverified")
        self.manifest = {"schema_version": 1, "mode": "camera_stream_observation_only",
                         "producer_clock": "host_monotonic", "motion_sent": False,
                         "frame": asdict(self.frame),
                         "image_sha256": hashlib.sha256(self.image.read_bytes()).hexdigest()}
        self.seen = {}

    def load(self):
        (self.root / "latest.json").write_text(json.dumps(self.manifest))
        return observer.load_observation(self.root, "Move ahead.", self.seen, 100.1)

    def test_preserves_unverified_camera_time_and_assumed_state(self):
        observation, _ = self.load()
        self.assertIsNone(observation.frame.captured_at)
        self.assertEqual(observation.frame.source_timestamp, 20.)
        self.assertFalse(observation.frame.timestamp_verified)
        self.assertFalse(observation.state_timing_verified)
        self.assertFalse(observation.pose_frame_verified)
        self.assertIsNone(observation.state_aligned_at)
        self.assertEqual(observation.state.received_at, 100.)

    def test_rejects_mutation_of_previously_seen_image_or_metadata(self):
        self.load()
        self.image.write_bytes(b"\xff\xd8changed")
        self.manifest["image_sha256"] = hashlib.sha256(self.image.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.load()

    def test_rejects_hash_path_timing_and_schema_errors(self):
        original = json.loads(json.dumps(self.manifest))
        for field, value in (("path", "../outside.jpg"), ("path", "/outside.jpg"),
                             ("path", "frame.png"), ("timestamp_verified", 1),
                             ("timestamp_verified", True), ("received_at", float("nan")),
                             ("received_at", 110.), ("captured_at", 101.)):
            with self.subTest(field=field, value=value):
                self.manifest = json.loads(json.dumps(original))
                self.manifest["frame"][field] = value
                with self.assertRaises(ValueError):
                    self.load()
        for field, value in (("schema_version", True), ("motion_sent", True),
                             ("image_sha256", "0" * 64), ("producer_clock", "other_host")):
            self.manifest = json.loads(json.dumps(original))
            self.manifest[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.load()

    def test_rejects_symlink_image_and_changed_bytes_before_gpu_work(self):
        observation, digest = self.load()
        other = self.root / "other.jpg"
        other.write_bytes(self.image.read_bytes())
        self.image.unlink()
        self.image.symlink_to(other)
        with self.assertRaises(ValueError):
            self.load()
        with self.assertRaises(OSError):
            observer.check_immutable_image(observation, digest)


class Clock:
    now = 100.

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class LifecycleTests(unittest.TestCase):
    def run_observer(self, action_duration=0., worker_error=False):
        clock, events, executors = Clock(), [], []
        args = SimpleNamespace(max_semantic_age=2., duration=.35,
                               observations=Path("/unused"), instruction="Move ahead.")
        report = {"counts": {key: 0 for key in
                            ("observations", "requests", "completed", "actions", "skips",
                             "discards", "errors")}}

        class Future:
            def __init__(self):
                self.ready = clock.now + .08

            def done(self):
                return clock.now >= self.ready

            def result(self):
                clock.now = max(clock.now, self.ready)
                if worker_error:
                    raise RuntimeError("injected semantic failure")
                return object(), {"seconds": .08}

        class Executor:
            def __init__(self, max_workers):
                self.workers, self.futures, self.closed = max_workers, [], False
                executors.append(self)

            def submit(self, *unused):
                future = Future()
                self.futures.append(future)
                return future

            def shutdown(self, **kwargs):
                self.closed = kwargs

        def load(*unused):
            at = clock.now
            name = f"frame-{int((at - 100.) / .04):06d}.jpg"
            return Observation(Frame(name, at),
                               RobotState(at, 0., 0., 0., 0., 0., 0.,
                                          frame_id="assumed_stationary_world",
                                          velocity_frame="body"), args.instruction), "unused"

        def action(*unused):
            clock.now += action_duration
            return 30, action_duration

        fake_profile = SimpleNamespace(owned_cache=object())
        fake_model = SimpleNamespace(load_image=object())
        with patch.object(observer, "ThreadPoolExecutor", Executor), \
             patch.object(observer, "load_observation", side_effect=load), \
             patch.object(observer, "action_work", side_effect=action), \
             patch.object(observer.time, "monotonic", clock.monotonic), \
             patch.object(observer.time, "sleep", clock.sleep), \
             patch.object(observer.importlib, "import_module", return_value=fake_model), \
             patch.dict(sys.modules, {"profile_model_runtime": fake_profile}):
            try:
                observer.observe(args, object(), object(),
                                 lambda kind, **data: events.append((kind, data)), report)
            except RuntimeError:
                if not worker_error:
                    raise
        return report, events, executors

    def test_requests_keep_original_reference_and_shutdown_waits_for_worker(self):
        report, events, executors = self.run_observer()
        self.assertGreater(report["counts"]["actions"], 0)
        actions = [data for kind, data in events if kind == "action_completed"]
        self.assertTrue(any(data["semantic_request_in_flight"] for data in actions))
        self.assertTrue(all(data["before"]["shadow_only"] for data in actions))
        self.assertTrue(all(data["before"]["reference"]["received_at"]
                            <= data["current"]["received_at"] for data in actions))
        self.assertEqual(executors[0].workers, 1)
        self.assertEqual(executors[0].closed, {"wait": True, "cancel_futures": True})
        self.assertTrue(any(kind == "observation_stopped" for kind, _ in events))

    def test_slow_action_is_discarded_after_freshness_or_duration_expires(self):
        report, events, _ = self.run_observer(action_duration=.7)
        self.assertEqual(report["counts"]["actions"], 0)
        discarded = [data for kind, data in events if kind == "action_discarded"]
        self.assertTrue(discarded)
        self.assertEqual(discarded[0]["reason"], "duration_ended_during_action")

    def test_semantic_failure_still_resets_and_joins(self):
        report, events, executors = self.run_observer(worker_error=True)
        self.assertEqual(report["counts"]["actions"], 0)
        self.assertTrue(executors[0].closed["wait"])
        self.assertTrue(any(kind == "observation_stopped" for kind, _ in events))


if __name__ == "__main__":
    unittest.main()
