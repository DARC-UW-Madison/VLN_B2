"""Exercise real tensor-only I/O with generated fixtures; no model assets or GPU."""

import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import torch
from safetensors.torch import save_file

from b2_tic_vla.inference import _architecture, _checkpoint_state, _load_local_checkpoint


def main():
    shared = torch.tensor([1.0, -2.0], dtype=torch.bfloat16)
    state = {
        "model.vlm.weight": shared,
        "model.vlm_model.vlm.weight": shared,
        "model.action_expert.action_chunk_embed.weight": torch.arange(1024).reshape(2, 512).float(),
        "model.action_expert.attention_layers.0.weight": torch.ones((2, 2)),
    }
    # Materialize both alias names: the application requires every full-state key.
    independent = {key: value.contiguous().clone() for key, value in state.items()}
    with tempfile.TemporaryDirectory(prefix="tensor-loading-") as directory:
        path = Path(directory) / "generated.safetensors"
        save_file(independent, str(path))
        with patch.object(torch, "load", side_effect=AssertionError("Unexpected pickle path")) as load:
            checkpoint = _load_local_checkpoint(path, torch)
            restored = checkpoint["state_dict"]
            assert restored.keys() == state.keys()
            for key, value in state.items():
                assert value.shape == restored[key].shape
                assert value.dtype == restored[key].dtype
                assert torch.equal(value, restored[key])
            assert _architecture(_checkpoint_state(checkpoint), checkpoint) == (2, 1)
            malformed = Path(directory) / "malformed.safetensors"
            malformed.write_bytes(b"Not a safetensors payload")
            try:
                _load_local_checkpoint(malformed, torch)
            except Exception as error:
                assert type(error).__module__.startswith("safetensors"), type(error).__name__
            else:
                raise AssertionError("Malformed safetensors was accepted")
            with patch.object(torch, "__version__", "2.2.2"):
                try:
                    _load_local_checkpoint(Path(directory) / "external.ckpt", torch)
                except RuntimeError as error:
                    assert "stable Torch >=2.10.0" in str(error)
                else:
                    raise AssertionError("Older Torch checkpoint decode was not blocked")
            load.assert_not_called()
        report = {
            "passed": True,
            "torch_version": str(torch.__version__),
            "generated_tensor_keys": len(state),
            "file_bytes": path.stat().st_size,
            "fp32_bf16_values_shapes_dtypes_verified": True,
            "both_alias_names_retained": True,
            "malformed_input_rejected_without_pickle_fallback": True,
            "older_torch_checkpoint_decode_blocked": True,
            "architecture_inferred_from_generated_weights": True,
            "external_assets_read": False,
            "model_constructed": False,
            "gpu_used": False,
        }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
