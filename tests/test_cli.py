"""Exercise command boundaries without importing vendor runtimes."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from b2_tic_vla.cli import main
from b2_tic_vla.recording import read_observation
from b2_tic_vla.types import Frame, Plan, RobotState, Waypoint


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / "recorded.jpg"
        self.image.write_bytes(b"fake image")

    def run_cli(self, args):
        out, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(error):
            status = main(args)
        return status, out.getvalue(), error.getvalue()

    def test_replay_end_to_end_has_no_vendor_imports_and_stops_stale_input(self):
        import importlib
        original = importlib.import_module

        def no_vendor(name, *args, **kwargs):
            if name.startswith(("unitree", "pyzed", "torch", "ticvla")):
                self.fail("Replay attempted a vendor import")
            return original(name, *args, **kwargs)

        target = self.root / "replay.json"
        with patch("importlib.import_module", side_effect=no_vendor):
            status, output, error = self.run_cli(["replay", "--output", str(target)])
        self.assertEqual((status, error), (0, ""))
        result = json.loads(output)
        self.assertEqual(result, json.loads(target.read_text()))
        self.assertFalse(result["motion_sent"])
        self.assertEqual(result["decisions"][-1]["reason"], "stale_image")
        self.assertEqual(result["decisions"][-1]["command"], {"vx": 0, "vy": 0, "yaw_rate": 0})

    def test_existing_output_aborts_before_model_or_hardware(self):
        target = self.root / "existing.json"
        target.write_text("original")
        with patch("b2_tic_vla.cli._infer") as infer:
            status, _, _ = self.run_cli([
                "infer", "--observation", "missing", "--instruction", "go",
                "--base-model", "missing", "--checkpoint", "missing", "--output", str(target),
            ])
        self.assertEqual(status, 2)
        self.assertEqual(target.read_text(), "original")
        infer.assert_not_called()

    def test_state_failure_closes_reader(self):
        class Reader:
            closed = False

            def open(self):
                raise RuntimeError("DDS unavailable")

            def close(self):
                self.closed = True

        reader = Reader()
        with patch("b2_tic_vla.cli._reader", return_value=reader):
            status, _, error = self.run_cli(["state", "--interface", "eth0"])
        self.assertEqual(status, 2)
        self.assertIn("DDS unavailable", error)
        self.assertTrue(reader.closed)

    def test_state_empty_result_is_saved_and_returns_failure(self):
        class Reader:
            closed = False

            def open(self):
                pass

            def latest(self):
                return None

            def stats(self):
                return {"received": 0, "valid": 0}

            def close(self):
                self.closed = True

        reader = Reader()
        target = self.root / "state.json"
        with patch("b2_tic_vla.cli._reader", return_value=reader):
            status, _, _ = self.run_cli([
                "state", "--interface", "eth0", "--seconds", "0.001", "--output", str(target),
            ])
        self.assertEqual(status, 2)
        self.assertIsNone(json.loads(target.read_text())["state"])
        self.assertTrue(reader.closed)

    def test_camera_failure_closes_camera(self):
        class Camera:
            closed = False

            def open(self):
                raise RuntimeError("camera unavailable")

            def close(self):
                self.closed = True

        camera = Camera()
        with patch("b2_tic_vla.hardware.ZedCamera", return_value=camera):
            status, _, _ = self.run_cli(["camera", "--output", str(self.root / "frame.jpg")])
        self.assertEqual(status, 2)
        self.assertTrue(camera.closed)

    def test_camera_bad_extension_rejected_before_open(self):
        with patch("b2_tic_vla.hardware.ZedCamera") as camera:
            status, _, error = self.run_cli(["camera", "--output", str(self.root / "frame.png")])
        self.assertEqual(status, 2)
        self.assertIn(".jpg", error)
        camera.assert_not_called()

    def record_hardware(self, *, state_at=10.0, image_at=10.05, no_state=False):
        """Supply finite read-only samples without vendor imports or real devices."""
        sample = RobotState(state_at, 1, 2, 0.1, 0.2, 0, 0.3)

        class Reader:
            closed = False

            def open(self):
                pass

            def latest(self):
                return None if no_state else sample

            def stats(self):
                return {"received": 1, "valid": 1}

            def close(self):
                self.closed = True

        class Camera:
            closed = False

            def open(self):
                pass

            def capture(self, output_path):
                Path(output_path).write_bytes(b"fake frame")
                return Frame(output_path, image_at, source_timestamp=100,
                             source_clock="camera_unverified")

            def close(self):
                self.closed = True

        return Reader(), Camera()

    def test_record_creates_portable_manifest_and_closes_both_devices(self):
        reader, camera = self.record_hardware()
        target = self.root / "observation"
        with patch("b2_tic_vla.cli._reader", return_value=reader), \
             patch("b2_tic_vla.hardware.ZedCamera", return_value=camera):
            status, output, error = self.run_cli([
                "record", "--interface", "eth0", "--output-dir", str(target),
                "--velocity-frame", "body", "--position-frame", "odom",
            ])
        self.assertEqual((status, error), (0, ""))
        result = json.loads(output)
        self.assertFalse(result["motion_sent"])
        self.assertFalse(result["capture_time_verified"])
        manifest = target / "observation.json"
        self.assertEqual(json.loads(manifest.read_text())["frame"]["path"], "frame.jpg")
        frame, state = read_observation(manifest)
        self.assertEqual(frame.received_at, 10.05)
        self.assertEqual(frame.source_timestamp, 100)
        self.assertEqual(state.velocity_frame, "body")
        self.assertEqual(state.frame_id, "odom")
        self.assertTrue(reader.closed)
        self.assertTrue(camera.closed)

    def test_record_skew_failure_leaves_no_success_manifest_and_closes_devices(self):
        reader, camera = self.record_hardware(state_at=9.0)
        target = self.root / "skewed"
        with patch("b2_tic_vla.cli._reader", return_value=reader), \
             patch("b2_tic_vla.hardware.ZedCamera", return_value=camera):
            status, _, error = self.run_cli([
                "record", "--interface", "eth0", "--output-dir", str(target),
            ])
        self.assertEqual(status, 2)
        self.assertIn("skew", error)
        self.assertFalse((target / "observation.json").exists())
        self.assertTrue(reader.closed)
        self.assertTrue(camera.closed)

    def test_record_timeout_and_capture_failure_close_both_devices(self):
        for failure in ("no_state", "capture"):
            with self.subTest(failure=failure):
                reader, camera = self.record_hardware(no_state=failure == "no_state")
                if failure == "capture":
                    camera.capture = lambda _: (_ for _ in ()).throw(RuntimeError("capture failed"))
                clock = [0, 6] if failure == "no_state" else [0]
                target = self.root / failure
                with patch("b2_tic_vla.cli._reader", return_value=reader), \
                     patch("b2_tic_vla.hardware.ZedCamera", return_value=camera), \
                     patch("b2_tic_vla.cli.time.monotonic", side_effect=clock):
                    status, _, error = self.run_cli([
                        "record", "--interface", "eth0", "--output-dir", str(target),
                    ])
                self.assertEqual(status, 2)
                self.assertIn("No finite" if failure == "no_state" else "capture failed", error)
                self.assertTrue(reader.closed)
                self.assertTrue(camera.closed)
                self.assertFalse((target / "observation.json").exists())

    def test_record_reader_closes_even_if_camera_cleanup_fails(self):
        reader, camera = self.record_hardware(state_at=0)
        camera.close = lambda: (_ for _ in ()).throw(RuntimeError("camera cleanup failed"))
        with patch("b2_tic_vla.cli._reader", return_value=reader), \
             patch("b2_tic_vla.hardware.ZedCamera", return_value=camera):
            status, _, error = self.run_cli([
                "record", "--interface", "eth0", "--output-dir", str(self.root / "cleanup"),
            ])
        self.assertEqual(status, 2)
        self.assertIn("camera cleanup failed", error)
        self.assertTrue(reader.closed)

    def test_offline_inference_rebases_time_and_never_sends_motion(self):
        frame = Frame(str(self.image), 100)
        state = RobotState(100, 0, 0, 0, 0, 0, 0, velocity_frame="body")
        observed = []

        class Predictor:
            def __init__(self, *args, **kwargs):
                pass

            def load(self):
                pass

            def predict(self, images, instruction, robot_state, observation_at):
                observed.append(observation_at)
                return Plan((Waypoint(0.4, 0, 0.1),), observation_at, observation_at, "ticvla-sync")

            def describe(self):
                return {"fake": True}

        with patch("b2_tic_vla.cli.read_observation", return_value=(frame, state)), \
             patch("b2_tic_vla.inference.TicVlaPredictor", Predictor), \
             patch("b2_tic_vla.cli.time.monotonic", return_value=200):
            status, output, error = self.run_cli([
                "infer", "--observation", "record", "--instruction", "go",
                "--base-model", "local-base", "--checkpoint", "local-checkpoint",
            ])
        self.assertEqual((status, error), (0, ""))
        result = json.loads(output)
        self.assertEqual(observed, [200])
        self.assertEqual(result["recorded_frame"]["received_at"], 100)
        self.assertFalse(result["motion_sent"])

    def test_inference_prevalidation_happens_before_costly_model_loading(self):
        for issue in ("instruction", "velocity_frame", "empty_image"):
            with self.subTest(issue=issue):
                instruction = "   " if issue == "instruction" else "go"
                frame = Frame(str(self.image), 100)
                state = RobotState(100, 0, 0, 0, 0, 0, 0,
                                   velocity_frame="unknown" if issue == "velocity_frame" else "body")
                if issue == "empty_image":
                    self.image.write_bytes(b"")
                with patch("b2_tic_vla.cli.read_observation", return_value=(frame, state)), \
                     patch("b2_tic_vla.inference.TicVlaPredictor") as predictor:
                    status, _, error = self.run_cli([
                        "infer", "--observation", "record", "--instruction", instruction,
                        "--base-model", "local-base", "--checkpoint", "local-checkpoint",
                    ])
                self.assertEqual(status, 2)
                self.assertIn({"instruction": "instruction", "velocity_frame": "velocity frame",
                               "empty_image": "empty"}[issue], error)
                predictor.assert_not_called()

    def test_missing_inference_dependency_returns_concise_error(self):
        frame = Frame(str(self.image), 100)
        state = RobotState(100, 0, 0, 0, 0, 0, 0, velocity_frame="body")
        with patch("b2_tic_vla.cli.read_observation", return_value=(frame, state)), \
             patch("b2_tic_vla.inference.TicVlaPredictor") as predictor:
            predictor.return_value.load.side_effect = ModuleNotFoundError("No module named transformers")
            status, output, error = self.run_cli([
                "infer", "--observation", "record", "--instruction", "go",
                "--base-model", "local-base", "--checkpoint", "local-checkpoint",
            ])
        self.assertEqual(status, 2)
        self.assertEqual(output, "")
        self.assertIn("No module named transformers", error)
        self.assertNotIn("Traceback", error)

    def test_invalid_replay_reports_error(self):
        target = self.root / "bad.json"
        target.write_text('{"schema_version":1,"samples":[]}')
        status, _, error = self.run_cli(["replay", "--input", str(target)])
        self.assertEqual(status, 2)
        self.assertIn("nonempty", error)


if __name__ == "__main__":
    unittest.main()
