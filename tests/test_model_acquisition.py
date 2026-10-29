"""Verify acquisition guards without contacting the Hub or reading model files."""

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location(
    "acquire_model_assets", Path(__file__).resolve().parents[1] / "tools/acquire_model_assets.py"
)
assets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assets)


class AcquisitionTests(unittest.TestCase):
    def test_default_plan_does_not_import_hub_or_contact_network(self):
        output = io.StringIO()
        with patch("sys.stdout", output):
            with patch.object(assets.importlib, "import_module") as imports:
                assets.main([])
        imports.assert_not_called()
        plan = json.loads(output.getvalue())
        self.assertEqual((plan["total_files"], plan["total_bytes"]), (17, 3827163803))

    def test_file_size_sha256_and_git_blob_are_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture"
            path.write_bytes(b"abc")
            sha = hashlib.sha256(b"abc").hexdigest()
            blob = hashlib.sha1(b"blob 3\0abc").hexdigest()
            self.assertEqual(assets.verify_file(path, 3, sha, blob), sha)
            for args in ((4, sha, blob), (3, "0" * 64, None), (3, None, "0" * 40), (3, None, None)):
                with self.subTest(args=args), self.assertRaises(ValueError):
                    assets.verify_file(path, *args)

    def test_existing_report_is_not_overwritten_or_network_contacted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "report.json"
            report.write_text("retained")
            with patch.object(assets.importlib, "import_module") as imports:
                with self.assertRaises(FileExistsError):
                    assets.acquire(root, report)
            imports.assert_not_called()
            self.assertEqual(report.read_text(), "retained")

    def test_wrong_revision_rejected_before_file_acquisition(self):
        api = SimpleNamespace(repo_info=Mock(return_value=SimpleNamespace(sha="wrong")))
        hub = SimpleNamespace(HfApi=lambda **kwargs: api, hf_hub_download=Mock())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(assets.importlib, "import_module", return_value=hub):
                with self.assertRaisesRegex(ValueError, "approved revision"):
                    assets.acquire(root, root / "new-report.json")
            hub.hf_hub_download.assert_not_called()
            self.assertFalse((root / "new-report.json").exists())


if __name__ == "__main__":
    unittest.main()
