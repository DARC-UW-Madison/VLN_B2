"""Vendor API contract tests with mocks; these do not validate real devices."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from b2_tic_vla import hardware


def sample(**changes):
    fields = dict(
        position=[1.0, 2.0, 3.0],
        velocity=[0.2, 0.3, 99.0],
        imu_state=SimpleNamespace(rpy=[0.0, 0.0, 0.5]),
        yaw_speed=0.4,
        stamp=SimpleNamespace(sec=7, nanosec=500_000_000),
    )
    fields.update(changes)
    return SimpleNamespace(**fields)


class ZedCameraTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "frame.jpg"
        self.camera = Mock()
        self.camera.open.return_value = 0
        self.camera.grab.return_value = 0
        self.camera.retrieve_image.return_value = 0
        self.camera.get_timestamp.return_value.get_nanoseconds.return_value = 12_500_000_000
        self.image = Mock()

        def write_image(path):
            Path(path).write_bytes(b"mock JPEG")
            return 0

        self.image.write.side_effect = write_image
        self.sl = SimpleNamespace(
            Camera=Mock(return_value=self.camera),
            InitParameters=SimpleNamespace,
            RuntimeParameters=SimpleNamespace,
            Mat=Mock(return_value=self.image),
            ERROR_CODE=SimpleNamespace(SUCCESS=0),
            RESOLUTION=SimpleNamespace(HD720=720),
            DEPTH_MODE=SimpleNamespace(NONE="none"),
            VIEW=SimpleNamespace(LEFT="left"),
            TIME_REFERENCE=SimpleNamespace(IMAGE="image", CURRENT="current"),
        )
        self.module_patch = patch.object(hardware.importlib, "import_module", return_value=self.sl)
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)

    def test_capture_preserves_source_clock_and_does_not_invent_capture_time(self):
        adapter = hardware.ZedCamera()
        with patch.object(hardware.time, "monotonic", side_effect=[100.0, 100.1]):
            adapter.open()
            frame = adapter.capture(str(self.path))
        self.assertEqual(frame.received_at, 100.1)
        self.assertIsNone(frame.captured_at)
        self.assertFalse(frame.timestamp_verified)
        self.assertEqual(frame.source_timestamp, 12.5)
        self.assertEqual(frame.source_clock, "zed_image_unverified")
        self.camera.get_timestamp.assert_called_once_with("image")
        self.camera.retrieve_image.assert_called_once_with(self.image, "left")
        parameters = self.camera.open.call_args.args[0]
        self.assertEqual(parameters.depth_mode, "none")
        self.assertTrue(parameters.async_grab_camera_recovery)
        adapter.close()
        adapter.close()
        self.camera.close.assert_called_once()

    def test_private_settings_directory_is_used_without_changing_sdk_default(self):
        default = hardware.ZedCamera()
        default.open()
        self.assertFalse(hasattr(self.camera.open.call_args.args[0], "optional_settings_path"))
        default.close()
        adapter = hardware.ZedCamera(settings_directory=self.folder.name)
        adapter.open()
        self.assertEqual(self.camera.open.call_args.args[0].optional_settings_path,
                         str(Path(self.folder.name).resolve()))
        adapter.close()

    def test_camera_settings_reject_non_directory_before_vendor_import(self):
        self.path.write_text("not a directory")
        with self.assertRaisesRegex(ValueError, "existing directory"):
            hardware.ZedCamera(settings_directory=str(self.path))
        self.sl.Camera.assert_not_called()

    def test_capture_without_source_timestamp_retains_receipt_only(self):
        self.camera.get_timestamp.return_value.get_nanoseconds.return_value = 0
        adapter = hardware.ZedCamera()
        adapter.open()
        frame = adapter.capture(str(self.path))
        self.assertIsNone(frame.source_timestamp)
        self.assertIsNone(frame.source_clock)
        self.assertIsNone(frame.captured_at)
        adapter.close()

    def test_failed_open_closes_camera(self):
        self.camera.open.return_value = 3
        adapter = hardware.ZedCamera()
        with self.assertRaisesRegex(RuntimeError, "open failed"):
            adapter.open()
        self.camera.close.assert_called_once()
        with self.assertRaisesRegex(RuntimeError, "Open the ZED"):
            adapter.capture(str(self.path))

    def test_grab_failure_has_bounded_attempts(self):
        self.camera.grab.return_value = 3
        adapter = hardware.ZedCamera(max_grab_attempts=2)
        adapter.open()
        with patch.object(hardware.time, "sleep"):
            with self.assertRaisesRegex(TimeoutError, "2 attempts"):
                adapter.capture(str(self.path))
        self.assertEqual(self.camera.grab.call_count, 2)
        self.camera.retrieve_image.assert_not_called()
        self.assertFalse(self.path.exists())
        adapter.close()

    def test_grab_failure_honors_deadline(self):
        self.camera.grab.return_value = 3
        adapter = hardware.ZedCamera(timeout_s=1.0)
        adapter.open()
        with patch.object(hardware.time, "monotonic", side_effect=[10.0, 12.0]):
            with self.assertRaisesRegex(TimeoutError, "deadline"):
                adapter.capture(str(self.path))
        self.assertEqual(self.camera.grab.call_count, 1)
        adapter.close()

    def test_retrieval_and_write_errors_are_reported(self):
        adapter = hardware.ZedCamera()
        adapter.open()
        self.camera.retrieve_image.return_value = 3
        with self.assertRaisesRegex(RuntimeError, "retrieval failed"):
            adapter.capture(str(self.path))
        self.image.write.assert_not_called()
        self.camera.retrieve_image.return_value = 0
        self.image.write.side_effect = None
        self.image.write.return_value = 3
        with self.assertRaisesRegex(RuntimeError, "write failed"):
            adapter.capture(str(self.path))
        self.image.write.return_value = 0
        with self.assertRaisesRegex(RuntimeError, "no image file"):
            adapter.capture(str(self.path))
        adapter.close()

    def test_existing_file_is_never_overwritten(self):
        self.path.write_bytes(b"original")
        adapter = hardware.ZedCamera()
        adapter.open()
        with self.assertRaises(FileExistsError):
            adapter.capture(str(self.path))
        self.camera.grab.assert_not_called()
        self.assertEqual(self.path.read_bytes(), b"original")
        adapter.close()


class UnitreeStateReaderTests(unittest.TestCase):
    def setUp(self):
        self.subscribers = {}

        def subscribe(topic, message_type):
            subscriber = Mock()
            self.subscribers[topic] = subscriber
            return subscriber

        self.channel = SimpleNamespace(
            ChannelSubscriber=Mock(side_effect=subscribe),
            ChannelFactoryInitialize=Mock(),
        )
        self.messages = SimpleNamespace(SportModeState_=object())
        self.imports = []

        def import_module(name):
            self.imports.append(name)
            return {
                "unitree_sdk2py.core.channel": self.channel,
                "unitree_sdk2py.idl.unitree_go.msg.dds_": self.messages,
            }[name]

        self.module_patch = patch.object(hardware.importlib, "import_module", side_effect=import_module)
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)
        self.config_patch = patch.object(hardware, "_dds_configuration", None)
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)

    def emit(self, topic, message):
        self.subscribers[topic].Init.call_args.args[0](message)

    def test_lazy_imports_and_no_control_client_or_publisher(self):
        reader = hardware.UnitreeStateReader("eth0")
        self.assertEqual(self.imports, [])
        self.assertIsNone(reader.latest())
        reader.open()
        self.assertEqual(len(self.imports), 2)
        self.assertTrue(all("sport_client" not in name for name in self.imports))
        self.assertEqual(set(self.subscribers), set(hardware._STATE_TOPICS))
        self.channel.ChannelFactoryInitialize.assert_called_once_with(0, "eth0")
        reader.close()
        self.assertTrue(all(sub.Close.call_count == 1 for sub in self.subscribers.values()))

    def test_invalid_high_frequency_stream_falls_back_to_valid_low_frequency(self):
        reader = hardware.UnitreeStateReader("eth0")
        reader.open()
        self.emit("rt/sportmodestate", sample(position=[float("nan"), 0, 0]))
        self.assertIsNone(reader.latest())
        with patch.object(hardware.time, "monotonic", return_value=123.0):
            self.emit("rt/lf/sportmodestate", sample())
        state = reader.latest()
        self.assertEqual(state.received_at, 123.0)
        self.assertEqual((state.x, state.y, state.yaw), (1.0, 2.0, 0.5))
        self.assertEqual((state.vx, state.vy, state.yaw_rate), (0.2, 0.3, 0.4))
        self.assertNotEqual(state.yaw_rate, 99.0)
        self.assertEqual(state.source_timestamp, 7.5)
        self.assertEqual(state.source_clock, "unitree_stamp_unverified")
        self.assertEqual(state.frame_id, "unknown")
        self.assertEqual(state.velocity_frame, "unknown")
        stats = reader.stats()
        self.assertEqual(stats["received"], 2)
        self.assertEqual(stats["valid"], 1)
        self.assertEqual(stats["active_topic"], "rt/lf/sportmodestate")
        stats["topics"]["rt/sportmodestate"]["valid"] = 999
        self.assertEqual(reader.stats()["topics"]["rt/sportmodestate"]["valid"], 0)
        reader.close()

    def test_malformed_fields_and_timestamps_do_not_escape_callback(self):
        reader = hardware.UnitreeStateReader("eth0", topic="rt/sportmodestate")
        reader.open()
        for invalid in [SimpleNamespace(), sample(velocity=[]), sample(yaw_speed=float("inf"))]:
            self.emit("rt/sportmodestate", invalid)
        for stamp in [None, SimpleNamespace(sec=0, nanosec=0),
                      SimpleNamespace(sec=1, nanosec=1_000_000_000)]:
            self.emit("rt/sportmodestate", sample(stamp=stamp))
            self.assertIsNone(reader.latest().source_timestamp)
        self.assertEqual(reader.stats()["received"], 6)
        self.assertEqual(reader.stats()["valid"], 3)
        reader.close()
        self.emit("rt/sportmodestate", sample())
        self.assertEqual(reader.stats()["received"], 6)

    def test_partial_open_failure_closes_all_created_subscribers(self):
        original = self.channel.ChannelSubscriber.side_effect

        def subscribe(topic, message_type):
            subscriber = original(topic, message_type)
            if topic == "rt/lf/sportmodestate":
                subscriber.Init.side_effect = RuntimeError("DDS setup failure")
            return subscriber

        self.channel.ChannelSubscriber.side_effect = subscribe
        reader = hardware.UnitreeStateReader("eth0")
        with self.assertRaisesRegex(RuntimeError, "DDS setup failure"):
            reader.open()
        self.assertTrue(all(sub.Close.call_count == 1 for sub in self.subscribers.values()))
        reader.close()

    def test_cleanup_continues_when_one_subscriber_fails(self):
        reader = hardware.UnitreeStateReader("eth0")
        reader.open()
        self.subscribers["rt/lf/sportmodestate"].Close.side_effect = RuntimeError("cleanup error")
        with self.assertRaisesRegex(RuntimeError, "cleanup failed"):
            reader.close()
        self.assertTrue(all(sub.Close.call_count == 1 for sub in self.subscribers.values()))
        reader.close()

    def test_dds_interface_changes_require_new_process(self):
        reader = hardware.UnitreeStateReader("eth0")
        reader.open()
        reader.close()
        with self.assertRaisesRegex(RuntimeError, "new process"):
            hardware.UnitreeStateReader("eth1").open()


class VendorDependencyTests(unittest.TestCase):
    def test_missing_vendor_dependency_reports_manual_installation(self):
        with patch.object(hardware.importlib, "import_module", side_effect=ImportError("not installed")):
            with self.assertRaisesRegex(RuntimeError, "does not install or download"):
                hardware.ZedCamera().open()
            with self.assertRaisesRegex(RuntimeError, "DDS runtime"):
                hardware.UnitreeStateReader("eth0").open()

    def test_invalid_configuration_is_rejected_without_imports(self):
        for kwargs in [{"max_grab_attempts": 0}, {"timeout_s": float("nan")}]:
            with self.assertRaises(ValueError):
                hardware.ZedCamera(**kwargs)
        for kwargs in [{"interface": "eth0<xml>"}, {"interface": "eth0", "domain_id": -1},
                       {"interface": "eth0", "topic": "rt/lowcmd"}]:
            with self.assertRaises(ValueError):
                hardware.UnitreeStateReader(**kwargs)


if __name__ == "__main__":
    unittest.main()
