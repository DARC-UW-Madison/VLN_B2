"""Check profiling boundaries and fail-closed input guards without GPU/model imports."""

import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location(
    "profile_model_runtime", Path(__file__).resolve().parents[1] / "tools/profile_model_runtime.py"
)
profiler = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(profiler)


class ProfilingTests(unittest.TestCase):
    def test_nested_vision_is_not_counted_twice_and_methods_restore_on_failure(self):
        vision = Mock(return_value="feature")
        vlm = SimpleNamespace(extract_feature=vision)
        chat = lambda: vlm.extract_feature()
        vlm.chat, vlm.forward = chat, Mock()
        decoder = SimpleNamespace(forward=Mock())
        model = SimpleNamespace(vlm=vlm, action_expert=decoder)
        events = []
        with self.assertRaisesRegex(RuntimeError, "fixture"):
            with profiler.stage_measurements(model, lambda: None, events):
                self.assertEqual(vlm.chat(), "feature")
                vlm.extract_feature()
                raise RuntimeError("fixture")
        self.assertEqual([v["stage"] for v in events],
                         ["semantic_generation", "current_image_features"])
        self.assertIs(vlm.chat, chat)
        self.assertIs(vlm.extract_feature, vision)

    def test_bad_checkpoint_hash_fails_before_model_loading_and_report_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image, checkpoint, report = root / "frame.jpg", root / "model.safetensors", root / "report.json"
            image.write_bytes(b"fixture")
            checkpoint.write_bytes(b"fixture")
            args = ["--base-model", folder, "--checkpoint", str(checkpoint),
                    "--expected-sha256", "0" * 64, "--upstream-root", folder,
                    "--image", str(image), "--report", str(report), "--assumed-stationary"]
            with patch.dict(profiler.os.environ, {"HF_HUB_OFFLINE": "1"}), \
                 patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
                self.assertEqual(profiler.main(args), 1)
            original = report.read_text()
            value = json.loads(original)
            self.assertFalse(value["model_constructed"])
            self.assertFalse(value["motion_sent"])
            self.assertIn("SHA256 mismatch", value["error"])
            with self.assertRaises(FileExistsError):
                profiler.main(args)
            self.assertEqual(report.read_text(), original)


if __name__ == "__main__":
    unittest.main()
