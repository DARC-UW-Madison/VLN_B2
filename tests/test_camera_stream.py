"""Camera-only producer contracts with mock devices and a deterministic clock."""

from dataclasses import asdict
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch

from b2_tic_vla.types import Frame


SPEC = importlib.util.spec_from_file_location(
    "record_camera_stream", Path(__file__).resolve().parents[1] / "tools/record_camera_stream.py"
)
producer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(producer)


class Clock:
    def __init__(self):
        self.now = 100.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        if seconds <= 0:
            raise AssertionError("Only positive sleeps are expected")
        self.sleeps.append(seconds)
        self.now += seconds


class CameraStreamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.settings = self.root / "settings"
        self.settings.mkdir()
        self.output = self.root / "stream"
        self.clock = Clock()
        self.camera = Mock()
        self.images = {}
        self.frames = []
        self.capture_times = []
        self.capture_delay = 0.0

        def capture(path):
            self.capture_times.append(self.clock.now)
            for existing, original in self.images.items():
                self.assertEqual(existing.read_bytes(), original)
            image = Path(path)
            content = f"Mock JPEG {len(self.images) + 1}".encode()
            with image.open("xb") as stream:
                stream.write(content)
            self.images[image] = content
            self.clock.now += self.capture_delay
            frame = Frame(str(image), self.clock.now, source_timestamp=12.5,
                          source_clock="zed_image_unverified")
            self.frames.append(frame)
            return frame

        self.camera.capture.side_effect = capture
        for target, value in (("_make_camera", Mock(return_value=self.camera)),
                              ("time.monotonic", self.clock.monotonic),
                              ("time.sleep", self.clock.sleep)):
            owner, name = (producer.time, target.split(".")[1]) if "." in target else (producer, target)
            patcher = patch.object(owner, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def arguments(self, duration="0.65", fps="5"):
        return ["--output-dir", str(self.output), "--settings-dir", str(self.settings),
                "--duration", duration, "--fps", fps]

    def run_producer(self, arguments=None):
        with patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
            return producer.main(arguments or self.arguments())

    def test_immutable_frames_and_complete_atomic_latest_preserve_all_clock_fields(self):
        original_replace = producer.os.replace
        publications = []

        def publish(source, destination):
            source, destination = Path(source), Path(destination)
            self.assertEqual(source.parent, self.output)
            self.assertEqual(destination, self.output / "latest.json")
            if publications:
                self.assertEqual(json.loads(destination.read_text()), publications[-1])
            else:
                self.assertFalse(destination.exists())
            manifest = json.loads(source.read_text())
            image = self.output / manifest["frame"]["path"]
            self.assertEqual(manifest["image_sha256"], hashlib.sha256(image.read_bytes()).hexdigest())
            self.assertEqual(json.loads(image.with_suffix(".json").read_text()), manifest)
            original_replace(source, destination)
            self.assertEqual(json.loads(destination.read_text()), manifest)
            publications.append(manifest)

        with patch.object(producer.os, "replace", side_effect=publish):
            self.assertEqual(self.run_producer(), 0)
        self.assertEqual(len(publications), 4)
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o700)
        for index, (image, content) in enumerate(self.images.items()):
            self.assertEqual(image.name, f"frame-{index + 1:06d}.jpg")
            self.assertEqual(image.read_bytes(), content)
            self.assertEqual(stat.S_IMODE(image.stat().st_mode), 0o400)
            manifest = publications[index]
            expected_frame = asdict(self.frames[index])
            expected_frame["path"] = image.name
            self.assertEqual(manifest["frame"], expected_frame)
            self.assertIsNone(manifest["frame"]["captured_at"])
            self.assertFalse(manifest["frame"]["timestamp_verified"])
            self.assertEqual(manifest["schema_version"], 1)
            self.assertEqual(manifest["mode"], "camera_stream_observation_only")
            self.assertEqual(manifest["producer_clock"], "host_monotonic")
            self.assertFalse(manifest["motion_sent"])
        summary = json.loads((self.output / "summary.json").read_text())
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["frames"], summary["published_frames"])
        self.assertEqual(summary["frames"], 4)
        self.assertFalse(summary["robot_connected"])
        self.assertFalse(summary["motion_sent"])
        self.assertTrue(summary["clock_unverified"])
        self.camera.open.assert_called_once()
        self.camera.close.assert_called_once()
        self.assertEqual(list(self.output.glob(".latest-*")), [])

    def test_missed_slots_are_skipped_without_catchup_bursts(self):
        self.capture_delay = 0.35
        self.assertEqual(self.run_producer(self.arguments(duration="0.9")), 0)
        self.assertEqual(len(self.capture_times), 3)
        self.assertAlmostEqual(self.capture_times[1] - self.capture_times[0], 0.4)
        self.assertAlmostEqual(self.capture_times[2] - self.capture_times[1], 0.4)
        self.assertLess(self.capture_times[-1], 100.9)

    def test_existing_output_is_refused_before_camera_construction(self):
        self.output.mkdir()
        sentinel = self.output / "existing.jpg"
        sentinel.write_bytes(b"Keep this existing recording")
        self.assertEqual(self.run_producer(), 1)
        producer._make_camera.assert_not_called()
        self.assertEqual(sentinel.read_bytes(), b"Keep this existing recording")
        self.assertFalse((self.output / "summary.json").exists())

    def test_missing_parent_is_not_created(self):
        self.output = self.root / "missing" / "stream"
        self.assertEqual(self.run_producer(), 1)
        self.assertFalse(self.output.parent.exists())
        producer._make_camera.assert_not_called()

    def test_failed_open_still_closes_and_records_failure(self):
        self.camera.open.side_effect = RuntimeError("Mock open failure")
        self.assertEqual(self.run_producer(), 1)
        summary = json.loads((self.output / "summary.json").read_text())
        self.assertFalse(summary["passed"])
        self.assertEqual(summary["frames"], 0)
        self.assertEqual(summary["error"], "Mock open failure")
        self.assertFalse((self.output / "latest.json").exists())
        self.camera.close.assert_called_once()

    def test_failed_publication_keeps_previous_latest_and_cleans_temporary_file(self):
        original_replace = producer.os.replace
        count = 0

        def fail_second(source, destination):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("Mock publication failure")
            original_replace(source, destination)

        with patch.object(producer.os, "replace", side_effect=fail_second):
            self.assertEqual(self.run_producer(), 1)
        latest = json.loads((self.output / "latest.json").read_text())
        summary = json.loads((self.output / "summary.json").read_text())
        self.assertEqual(latest["frame"]["path"], "frame-000001.jpg")
        self.assertEqual(summary["frames"], 2)
        self.assertEqual(summary["published_frames"], 1)
        self.assertFalse(summary["passed"])
        self.assertEqual(list(self.output.glob(".latest-*")), [])
        for image, original in self.images.items():
            self.assertEqual(image.read_bytes(), original)
        self.camera.close.assert_called_once()

    def test_capture_and_close_failures_are_both_reported(self):
        self.camera.capture.side_effect = RuntimeError("Mock capture failure")
        self.camera.close.side_effect = RuntimeError("Mock close failure")
        self.assertEqual(self.run_producer(), 1)
        summary = json.loads((self.output / "summary.json").read_text())
        self.assertFalse(summary["passed"])
        self.assertEqual(summary["error"], "Mock capture failure")
        self.assertEqual(summary["close_error"], "Mock close failure")
        self.camera.close.assert_called_once()

    def test_invalid_limits_reject_before_directory_or_sdk_use(self):
        for duration, fps in (("nan", "5"), ("inf", "5"), ("0", "5"), ("61", "5"),
                              ("1", "nan"), ("1", "inf"), ("1", "0"), ("1", "11")):
            with self.subTest(duration=duration, fps=fps), \
                 patch("sys.stderr", io.StringIO()), self.assertRaises(SystemExit):
                producer.main(self.arguments(duration=duration, fps=fps))
        self.assertFalse(self.output.exists())
        producer._make_camera.assert_not_called()

    def test_help_does_not_construct_camera(self):
        with patch("sys.stdout", io.StringIO()), self.assertRaises(SystemExit) as result:
            producer.main(["--help"])
        self.assertEqual(result.exception.code, 0)
        producer._make_camera.assert_not_called()


if __name__ == "__main__":
    unittest.main()
