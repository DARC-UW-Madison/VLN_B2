"""Check adapter contracts with fake libraries; no model/GPU execution is claimed."""

import os
import sys
import tempfile
import time
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from b2_tic_vla.inference import TicVlaPredictor, _offline_loaders
from b2_tic_vla.types import RobotState


class Tensor:
    def __init__(self, data=None, shape=None):
        self.data = data
        self.shape = shape

    def detach(self):
        return self

    def float(self):
        return self

    def cpu(self):
        return self

    def tolist(self):
        return self.data


def standard_state():
    return {
        "vlm.weight": Tensor(shape=(1,)),
        "vlm_model.vlm.weight": Tensor(shape=(1,)),
        "action_expert.action_chunk_embed.weight": Tensor(shape=(2, 512)),
        "action_expert.attention_layers.0.weight": Tensor(shape=(512, 512)),
    }


class InferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / "base"
        self.base.mkdir()
        (self.base / "config.json").write_text("{}")
        self.checkpoint_path = self.root / "model.ckpt"
        self.checkpoint_path.write_bytes(b"fake")
        self.image = self.root / "frame.png"
        self.image.write_bytes(b"fake image; no actual image decode in these tests")
        self.checkpoint = {"state_dict": {"model." + key: value for key, value in standard_state().items()}}
        self.output = Tensor([[[0.2, 0.0], [0.4, 0.1]]], (1, 2, 2))
        self.load_arguments = None
        self.model_kwargs = None
        self.predict_kwargs = None
        self.predict_offline = None
        self.lazy_predict_load = False
        self.stale_device = None
        self.strict = None
        self.loader_calls = []
        self.expected = standard_state()
        test = self

        class Model:
            def __init__(self, **kwargs):
                self.device = "cpu"
                test.model_kwargs = kwargs
                self.constructor_offline = os.environ.get("HF_HUB_OFFLINE")
                for name in ("AutoModel", "AutoTokenizer", "AutoProcessor"):
                    getattr(test.transformers, name).from_pretrained(kwargs["model_path"])

            def state_dict(self):
                return test.expected

            def load_state_dict(self, state, strict):
                test.strict = strict
                for key, value in state.items():
                    if strict and value.shape != test.expected[key].shape:
                        raise RuntimeError("state_dict shape mismatch")

            def to(self, **kwargs):
                self.device = test.stale_device or kwargs["device"]
                return self

            def eval(self):
                return self

            def predict(self, **kwargs):
                test.predict_kwargs = kwargs
                test.predict_offline = os.environ.get("HF_HUB_OFFLINE")
                if test.lazy_predict_load:
                    test.transformers.AutoProcessor.from_pretrained("already-cached-processor")
                return "reasoning", test.output, "prompt"

        self.torch = ModuleType("torch")
        self.torch.__version__ = "2.10.0+cpu"
        self.torch.bfloat16 = "bfloat16"
        self.torch.device = str
        self.torch.inference_mode = nullcontext
        self.torch.tensor = lambda data, **kwargs: data

        def load(*args, **kwargs):
            self.load_arguments = kwargs
            return self.checkpoint

        self.torch.load = load
        self.upstream = ModuleType("ticvla.models.ticvla")
        self.upstream.TICVLA = Model
        self.transformers = ModuleType("transformers")
        for name in ("AutoModel", "AutoTokenizer", "AutoProcessor"):
            class Loader:
                @staticmethod
                def from_pretrained(*args, **kwargs):
                    test.loader_calls.append(kwargs)
            setattr(self.transformers, name, Loader)
        self.modules = patch.dict(sys.modules, {
            "torch": self.torch,
            "transformers": self.transformers,
            "ticvla.models.ticvla": self.upstream,
        })
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.state = RobotState(received_at=0.0, x=0.0, y=0.0, yaw=0.0, vx=0.2, vy=0.1, yaw_rate=0.3, velocity_frame="base_link")

    def predictor(self):
        return TicVlaPredictor(self.base, self.checkpoint_path)

    def predict(self, predictor, instruction="Go to the door"):
        return predictor.predict([str(self.image)], instruction, self.state, time.monotonic())

    def test_restricted_local_loading_and_architecture(self):
        predictor = self.predictor().load()
        self.assertEqual(self.load_arguments, {"map_location": "cpu", "weights_only": True})
        self.assertEqual(self.model_kwargs["action_horizon_steps"], 2)
        self.assertEqual(self.model_kwargs["action_num_layers"], 1)
        self.assertFalse(self.model_kwargs["train_vlm"])
        self.assertTrue(self.strict)
        self.assertEqual(predictor._model.constructor_offline, "1")
        self.assertEqual(self.loader_calls, [
            {"local_files_only": True, "use_safetensors": True},
            {"local_files_only": True}, {"local_files_only": True},
        ])
        self.assertTrue(predictor.describe()["loaded"])

    def test_vulnerable_unknown_and_prerelease_torch_never_deserialize(self):
        for version in ("2.2.2", "2.9.1", "2.10.0rc1", "2.10.0a0+git", "unknown", ""):
            with self.subTest(version=version):
                self.torch.__version__ = version
                with self.assertRaisesRegex(RuntimeError, "stable Torch >=2.10.0"):
                    self.predictor().load()
                self.assertIsNone(self.load_arguments)
                self.assertIsNone(self.model_kwargs)

    def test_safetensors_on_older_torch_preserves_all_keys_and_strict_loading(self):
        self.torch.__version__ = "2.2.2"
        path = self.root / "model.safetensors"
        path.write_bytes(b"mock safetensors; real reader exercised separately")
        reader = ModuleType("safetensors.torch")
        calls = []
        def load_file(filename, device):
            calls.append((filename, device))
            return self.checkpoint["state_dict"]
        reader.load_file = load_file
        with patch.dict(sys.modules, {"safetensors.torch": reader}):
            TicVlaPredictor(self.base, path).load()
            self.assertTrue(self.strict)
            self.assertEqual(calls, [(str(path.resolve()), "cpu")])
            self.assertIsNone(self.load_arguments)
            self.checkpoint["state_dict"].pop("model.vlm.weight")
            with self.assertRaisesRegex(ValueError, "missing keys"):
                TicVlaPredictor(self.base, path).load()

    def test_mislabeled_safetensors_never_falls_back_to_pickle(self):
        path = self.root / "model.safetensors"
        path.write_bytes(b"invalid")
        reader = ModuleType("safetensors.torch")
        def rejected(*args, **kwargs):
            raise ValueError("invalid safetensors header")
        reader.load_file = rejected
        with patch.dict(sys.modules, {"safetensors.torch": reader}):
            with self.assertRaisesRegex(ValueError, "invalid safetensors header"):
                TicVlaPredictor(self.base, path).load()
        self.assertIsNone(self.load_arguments)
        self.assertIsNone(self.model_kwargs)

    def test_base_model_cannot_override_safetensors_or_local_only_policy(self):
        with _offline_loaders():
            self.transformers.AutoModel.from_pretrained(
                str(self.base), local_files_only=False, use_safetensors=False)
        self.assertEqual(self.loader_calls, [{"local_files_only": True, "use_safetensors": True}])

    def test_remote_identifier_and_missing_config_are_rejected_before_import(self):
        with self.assertRaisesRegex(ValueError, "local model directory"):
            TicVlaPredictor("OpenGVLab/InternVL3-1B", self.checkpoint_path).load()
        (self.base / "config.json").unlink()
        with self.assertRaisesRegex(ValueError, "config.json"):
            self.predictor().load()
        self.assertIsNone(self.load_arguments)

    def test_missing_checkpoint_and_invalid_upstream_path(self):
        with self.assertRaises(FileNotFoundError):
            TicVlaPredictor(self.base, self.root / "absent.ckpt").load()
        with self.assertRaisesRegex(ValueError, "upstream_root"):
            TicVlaPredictor(self.base, self.checkpoint_path, upstream_root=self.root).load()

    def test_restricted_loading_never_falls_back_to_pickle(self):
        calls = []

        def old_load(*args, **kwargs):
            calls.append(kwargs)
            raise TypeError("unexpected keyword weights_only")

        self.torch.load = old_load
        with self.assertRaisesRegex(RuntimeError, "Unsafe pickle loading is disabled"):
            self.predictor().load()
        self.assertEqual(len(calls), 1)

    def test_rejected_checkpoint_never_retries_unsafe_deserialization(self):
        import pickle

        calls = []

        def rejected(*args, **kwargs):
            calls.append(kwargs)
            raise pickle.UnpicklingError("unsupported checkpoint global")

        self.torch.load = rejected
        with self.assertRaisesRegex(RuntimeError, "unsafe pickle fallback is disabled"):
            self.predictor().load()
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0]["weights_only"])

    def test_missing_and_unexpected_keys_fail_closed(self):
        self.checkpoint["state_dict"]["model.surprise"] = Tensor(shape=(1,))
        with self.assertRaisesRegex(ValueError, "unexpected keys"):
            self.predictor().load()
        del self.checkpoint["state_dict"]["model.surprise"]
        del self.checkpoint["state_dict"]["model.vlm.weight"]
        with self.assertRaisesRegex(ValueError, "missing keys"):
            self.predictor().load()

    def test_mixed_prefix_is_not_silently_filtered(self):
        self.checkpoint["state_dict"]["vlm.weight"] = self.checkpoint["state_dict"].pop("model.vlm.weight")
        with self.assertRaises(ValueError):
            self.predictor().load()

    def test_plain_state_dictionary_and_tensor_shape_validation(self):
        self.checkpoint = standard_state()
        self.predictor().load()
        self.checkpoint["vlm.weight"] = Tensor(shape=(2,))
        with self.assertRaisesRegex(RuntimeError, "shape mismatch"):
            self.predictor().load()

    def test_noncontiguous_layers_and_disagreeing_metadata(self):
        state = self.checkpoint["state_dict"]
        state["model.action_expert.attention_layers.2.weight"] = Tensor(shape=(512, 512))
        with self.assertRaisesRegex(ValueError, "contiguous"):
            self.predictor().load()
        del state["model.action_expert.attention_layers.2.weight"]
        self.checkpoint["hyper_parameters"] = {"action_horizon_steps": 30}
        with self.assertRaisesRegex(ValueError, "metadata disagrees"):
            self.predictor().load()

    def test_prediction_preserves_relative_positions_without_cumsum(self):
        predictor = self.predictor().load()
        before = time.monotonic()
        plan = predictor.predict([str(self.image)], "Go to the door", self.state, before)
        self.assertEqual([(point.x, point.y) for point in plan.points], [(0.2, 0.0), (0.4, 0.1)])
        self.assertEqual([point.time_from_now for point in plan.points], [0.1, 0.2])
        self.assertEqual(plan.source, "ticvla-sync")
        self.assertEqual(plan.observation_at, before)
        self.assertGreaterEqual(plan.created_at, before)
        self.assertLessEqual(plan.created_at, time.monotonic())
        self.assertEqual(self.predict_kwargs["robot_state"], [0.2, 0.1, 0.3, 0.0, 0.0])
        self.assertEqual(self.predict_kwargs["time_delay"], 0.0)
        self.assertEqual(self.predict_kwargs["current_image_path"], str(self.image.resolve()))

    def test_wrong_shape_and_nonfinite_outputs_rejected(self):
        predictor = self.predictor().load()
        self.output.shape = (2, 2)
        with self.assertRaisesRegex(ValueError, "waypoint shape"):
            self.predict(predictor)
        self.output.shape = (1, 2, 2)
        self.output.data[0][1][0] = float("nan")
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            self.predict(predictor)

    def test_empty_instruction_images_and_unloaded_model(self):
        predictor = self.predictor()
        with self.assertRaisesRegex(ValueError, "instruction"):
            self.predict(predictor, "  ")
        with self.assertRaisesRegex(ValueError, "image path"):
            predictor.predict([], "Go", self.state, time.monotonic())
        with self.assertRaises(FileNotFoundError):
            predictor.predict([str(self.root / "absent.png")], "Go", self.state, time.monotonic())
        with self.assertRaisesRegex(RuntimeError, "load"):
            self.predict(predictor)

    def test_velocity_frame_and_timestamp_checks(self):
        predictor = self.predictor().load()
        with self.assertRaisesRegex(ValueError, "future"):
            predictor.predict([str(self.image)], "Go", self.state, time.monotonic() + 100)
        unknown = RobotState(received_at=0.0, x=0.0, y=0.0, yaw=0.0, vx=0.0, vy=0.0, yaw_rate=0.0)
        with self.assertRaisesRegex(ValueError, "frame"):
            predictor.predict([str(self.image)], "Go", unknown, time.monotonic())

    def test_secondary_cuda_device_and_stale_upstream_device(self):
        predictor = TicVlaPredictor(self.base, self.checkpoint_path, device="cuda:1").load()
        self.assertEqual(predictor._model.device, "cuda:1")
        self.stale_device = "cuda:0"
        with self.assertRaisesRegex(RuntimeError, "reports device cuda:0"):
            TicVlaPredictor(self.base, self.checkpoint_path, device="cuda:1").load()

    def test_inference_lazy_loading_is_offline_and_environment_is_restored(self):
        predictor = self.predictor().load()
        self.lazy_predict_load = True
        with patch.dict(os.environ, {"HF_HUB_OFFLINE": "0"}):
            self.predict(predictor)
            self.assertEqual(os.environ["HF_HUB_OFFLINE"], "0")
        self.assertEqual(self.predict_offline, "1")
        self.assertEqual(self.loader_calls[-1], {"local_files_only": True})


if __name__ == "__main__":
    unittest.main()
