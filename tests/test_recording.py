"""Validate portable manifests and preserve the distinction between clocks."""

import json
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from b2_tic_vla.recording import read_observation, write_json, write_observation
from b2_tic_vla.types import Frame, RobotState


class RecordingTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name).resolve()
        self.image = self.root / "image.jpg"
        self.image.write_bytes(b"mock JPEG")
        self.manifest = self.root / "observation.json"
        self.frame = Frame(str(self.image), 10.0, source_timestamp=1_700_000_000.0,
                           source_clock="zed_image_unverified")
        self.state = RobotState(10.1, 1, 2, 0.3, 0.2, 0, 0.4,
                                source_timestamp=1000.5, source_clock="unitree_stamp_unverified")

    def record(self):
        frame = asdict(self.frame)
        frame["path"] = "image.jpg"
        return {"schema_version": 1, "frame": frame, "state": asdict(self.state)}

    def read_record(self, value):
        self.manifest.write_text(json.dumps(value), encoding="utf-8")
        return read_observation(self.manifest)

    def test_roundtrip_retains_unknown_capture_and_source_clock_metadata(self):
        write_observation(self.manifest, self.frame, self.state)
        raw = json.loads(self.manifest.read_text())
        self.assertEqual(raw["frame"]["path"], "image.jpg")
        frame, state = read_observation(self.manifest)
        self.assertEqual(frame, self.frame)
        self.assertEqual(state, self.state)
        self.assertIsNone(frame.captured_at)
        self.assertFalse(frame.timestamp_verified)
        self.assertEqual(state.velocity_frame, "unknown")

    def test_verified_capture_roundtrip(self):
        original = replace(self.frame, captured_at=9.9, timestamp_verified=True)
        write_observation(self.manifest, original, self.state)
        frame, _ = read_observation(self.manifest)
        self.assertEqual(frame, original)

    def test_relative_path_is_resolved_from_manifest_location(self):
        target = self.root / "manifests" / "observation.json"
        write_observation(target, self.frame, self.state)
        raw = json.loads(target.read_text())
        self.assertEqual(raw["frame"]["path"], "../image.jpg")
        self.assertEqual(read_observation(target)[0].path, str(self.image))

    def test_missing_image_is_reported_for_read_and_write(self):
        with self.assertRaisesRegex(ValueError, "image does not exist"):
            write_observation(self.manifest, replace(self.frame, path=str(self.root / "missing.jpg")),
                              self.state)
        record = self.record()
        record["frame"]["path"] = "missing.jpg"
        with self.assertRaisesRegex(ValueError, "image does not exist"):
            self.read_record(record)

    def test_wrong_schema_shapes_and_fields_raise_value_errors(self):
        cases = [[], None, {}, {"schema_version": True}, {"schema_version": 2},
                 {"schema_version": 1, "frame": [], "state": {}},
                 {"schema_version": 1, "frame": {"path": 12}, "state": {}}]
        record = self.record()
        del record["state"]["yaw"]
        cases.append(record)
        record = self.record()
        record["frame"]["unexpected"] = "value"
        cases.append(record)
        for record in cases:
            with self.subTest(record=record), self.assertRaises(ValueError):
                self.read_record(record)

    def test_invalid_numeric_and_clock_fields_are_rejected(self):
        mutations = [
            ("frame", "received_at", True),
            ("state", "vx", "0.1"),
            ("state", "x", float("nan")),
            ("state", "yaw_rate", float("inf")),
            ("frame", "captured_at", float("nan")),
            ("frame", "source_timestamp", float("inf")),
            ("state", "source_timestamp", "123"),
            ("frame", "source_clock", ""),
            ("state", "source_clock", None),
            ("state", "frame_id", 123),
            ("state", "velocity_frame", ""),
            ("frame", "timestamp_verified", "false"),
            ("frame", "timestamp_verified", True),
            ("frame", "captured_at", 11),
        ]
        for section, name, value in mutations:
            with self.subTest(section=section, name=name, value=value):
                record = self.record()
                record[section][name] = value
                with self.assertRaises(ValueError):
                    self.read_record(record)

    def test_writer_rejects_invalid_numbers_without_creating_partial_file(self):
        with self.assertRaises(ValueError):
            write_json(self.manifest, {"invalid": float("nan")})
        self.assertFalse(self.manifest.exists())
        with self.assertRaises(ValueError):
            write_observation(self.manifest, self.frame, replace(self.state, x=float("inf")))
        self.assertFalse(self.manifest.exists())

    def test_writer_never_overwrites_existing_manifest(self):
        write_observation(self.manifest, self.frame, self.state)
        before = self.manifest.read_bytes()
        with self.assertRaises(FileExistsError):
            write_observation(self.manifest, self.frame, self.state)
        self.assertEqual(self.manifest.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
