"""Check conversion boundaries without installing Torch or reading external assets."""

import hashlib
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from b2_tic_vla.checkpoint_conversion import (
    architecture_metadata, convert_checkpoint, source_metadata, tensor_state,
)


class Tensor:
    layout = "strided"
    device = SimpleNamespace(type="cpu")
    is_quantized = False
    dtype = "float32"

    def numel(self):
        return 2

    def element_size(self):
        return 4


TORCH = SimpleNamespace(Tensor=Tensor, strided="strided", **{
    name: name for name in ("bool", "uint8", "int8", "int16", "int32", "int64",
                            "float16", "bfloat16", "float32", "float64")
})


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "generated.ckpt"
        self.source.write_bytes(b"Fixture bytes; never deserialized in these tests")
        self.digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.output = self.root / "output"

    def convert(self, **kwargs):
        options = dict(source=self.source, output=self.output, expected_sha256=self.digest,
                       repository="example/generated", repository_type="dataset", revision="0" * 40)
        options.update(kwargs)
        return convert_checkpoint(**options)

    def test_bad_digest_aborts_before_import_and_output(self):
        with patch("b2_tic_vla.checkpoint_conversion.importlib.import_module") as imports:
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                self.convert(expected_sha256="f" * 64)
        imports.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_existing_output_is_never_overwritten(self):
        self.output.mkdir()
        marker = self.output / "keep.txt"
        marker.write_text("original")
        with self.assertRaises(FileExistsError):
            self.convert()
        self.assertEqual(marker.read_text(), "original")

    def test_input_budget_and_invalid_limits_abort_before_decode(self):
        with patch("b2_tic_vla.checkpoint_conversion.importlib.import_module") as imports:
            for kwargs in ({"max_input_bytes": 1}, {"max_tensor_bytes": 0},
                           {"max_input_bytes": True}, {"expected_sha256": "invalid"}):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    self.convert(**kwargs)
        imports.assert_not_called()

    def test_nonregular_input_is_rejected_without_opening(self):
        fifo = self.root / "pipe.ckpt"
        os.mkfifo(fifo)
        with self.assertRaisesRegex(ValueError, "regular file"):
            self.convert(source=fifo)

    def test_source_identity_requires_pinned_revision_and_no_local_path(self):
        for args in (("/private/path", "dataset", "0" * 40),
                     ("example/model", "dataset", "main"),
                     ("example/model", "other", "0" * 40)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                source_metadata(*args)

    def test_all_original_names_and_aliases_count_toward_budget(self):
        shared = Tensor()
        source = {"model.first": shared, "model.alias": shared}
        result, size = tensor_state({"state_dict": source}, TORCH, 16)
        self.assertEqual(result, source)
        self.assertIs(result["model.first"], result["model.alias"])
        self.assertEqual(size, 16)
        with self.assertRaisesRegex(ValueError, "budget"):
            tensor_state(source, TORCH, 8)

    def test_empty_mixed_or_unsupported_states_fail_before_copying(self):
        sparse = Tensor()
        sparse.layout = "sparse"
        remote = Tensor()
        remote.device = SimpleNamespace(type="cuda")
        unsupported = Tensor()
        unsupported.dtype = "complex128"
        for state in ({}, {"x": "metadata"}, {1: Tensor()}, {"": Tensor()},
                      {"x": sparse}, {"x": remote}, {"x": unsupported}):
            with self.subTest(state=state), self.assertRaises(ValueError):
                tensor_state(state, TORCH, 100)

    def test_manifest_metadata_omits_unrelated_training_details(self):
        payload = {"hyper_parameters": {"action_horizon_steps": 2, "action_num_layers": 1,
                                         "private_training_path": "/private/example"}}
        self.assertEqual(architecture_metadata(payload),
                         {"action_horizon_steps": 2, "action_num_layers": 1})
        for value in (False, 0, "2"):
            with self.assertRaises(ValueError):
                architecture_metadata({"hyper_parameters": {"action_horizon_steps": value}})


if __name__ == "__main__":
    unittest.main()
