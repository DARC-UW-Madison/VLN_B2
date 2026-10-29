"""Ensure the explicit GPU verifier fails before model imports on invalid inputs."""

import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location(
    "verify_model_load", Path(__file__).resolve().parents[1] / "tools/verify_model_load.py"
)
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class ModelLoadVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.checkpoint = self.root / "model.safetensors"
        self.checkpoint.write_bytes(b"Fixture; not a model")
        self.report = self.root / "report.json"

    def arguments(self):
        return ["--base-model", str(self.root), "--checkpoint", str(self.checkpoint),
                "--expected-sha256", "0" * 64, "--upstream-root", str(self.root),
                "--report", str(self.report)]

    def test_original_checkpoint_format_rejected_before_hash_or_import(self):
        self.checkpoint = self.root / "model.ckpt"
        with patch.object(verifier, "digest") as digest, patch("sys.stderr", io.StringIO()):
            with self.assertRaises(SystemExit):
                verifier.main(self.arguments())
        digest.assert_not_called()
        self.assertFalse(self.report.exists())

    def test_existing_report_is_never_overwritten(self):
        self.report.write_text("retained")
        with patch.object(verifier, "digest") as digest:
            with self.assertRaises(FileExistsError):
                verifier.main(self.arguments())
        digest.assert_not_called()
        self.assertEqual(self.report.read_text(), "retained")

    def test_checksum_failure_records_no_model_or_inference(self):
        with patch.dict(verifier.os.environ, {"HF_HUB_OFFLINE": "1"}), \
             patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
            self.assertEqual(verifier.main(self.arguments()), 1)
        report = json.loads(self.report.read_text())
        self.assertFalse(report["passed"])
        self.assertFalse(report["model_constructed"])
        self.assertFalse(report["inference_run"])
        self.assertFalse(report["motion_sent"])
        self.assertIn("SHA256 mismatch", report["error"])

    def test_nonoffline_configuration_rejected_before_hash_or_import(self):
        with patch.dict(verifier.os.environ, {"HF_HUB_OFFLINE": "0"}), \
             patch.object(verifier, "digest") as digest, \
             patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
            self.assertEqual(verifier.main(self.arguments()), 1)
        digest.assert_not_called()
        self.assertFalse(json.loads(self.report.read_text())["model_constructed"])

    def test_successful_default_load_does_not_run_inference_or_create_image(self):
        predictor = SimpleNamespace(
            _model=SimpleNamespace(parameters=lambda: [SimpleNamespace(numel=lambda: 1)]),
            describe=lambda: {"loaded": True},
            predict=Mock(side_effect=AssertionError("Inference must be explicitly requested")),
        )
        predictor.load = lambda: predictor
        torch = ModuleType("torch")
        torch.__version__ = "test"
        torch.cuda = SimpleNamespace(init=lambda: None, set_device=lambda device: None,
            reset_peak_memory_stats=lambda device: None, synchronize=lambda device: None,
            memory_allocated=lambda device: 1, max_memory_allocated=lambda device: 1)
        module = ModuleType("b2_tic_vla.inference")
        module.TicVlaPredictor = lambda *args: predictor
        with patch.dict(verifier.os.environ, {"HF_HUB_OFFLINE": "1"}), \
             patch.dict("sys.modules", {"torch": torch, "b2_tic_vla.inference": module}), \
             patch.object(verifier, "digest", return_value="0" * 64), \
             patch("sys.stdout", io.StringIO()):
            self.assertEqual(verifier.main(self.arguments()), 0)
        report = json.loads(self.report.read_text())
        self.assertTrue(report["passed"])
        self.assertFalse(report["inference_run"])
        self.assertFalse((self.root / "generated-frame.png").exists())
        predictor.predict.assert_not_called()


if __name__ == "__main__":
    unittest.main()
