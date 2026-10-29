"""Generated checkpoint conversion and optional cross-runtime tensor readback."""

import argparse
from collections import OrderedDict
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import torch

from b2_tic_vla.checkpoint_conversion import convert_checkpoint, file_sha256, tensor_record
from b2_tic_vla.inference import _load_local_checkpoint


class UnsupportedMetadata:
    pass


def verify_generated_artifact(directory):
    manifest = json.loads((directory / "manifest.json").read_text())
    path = directory / "model.safetensors"
    assert manifest["verified"] and file_sha256(path) == manifest["output"]["sha256"]
    with patch.object(torch, "load", side_effect=AssertionError("Unexpected pickle path")) as load:
        state = _load_local_checkpoint(path, torch)["state_dict"]
        assert state.keys() == manifest["tensors"].keys()
        assert all(tensor_record(value) == manifest["tensors"][name] for name, value in state.items())
        load.assert_not_called()
    return {"passed": True, "torch_version": str(torch.__version__), "tensor_keys": len(state),
            "bitwise_readback_verified": True, "pickle_called": False,
            "external_model_assets_used": False, "model_constructed": False}


def run(directory):
    assert torch.version.cuda is None, "Conversion must use the CPU-only image"
    shared = torch.tensor([1.0, -2.0], dtype=torch.bfloat16)
    state = OrderedDict([
        ("model.first", shared), ("model.alias", shared),
        ("model.transposed", torch.arange(6).reshape(2, 3).t()),
        ("model.scalar", torch.tensor(7, dtype=torch.int64)),
        ("model.empty", torch.empty((0, 3))),
        ("model.special", torch.tensor([float("nan"), 0.0, -0.0, float("inf")], dtype=torch.float64)),
    ])
    payload = {"state_dict": state, "hyper_parameters": {"action_horizon_steps": 2,
                "action_num_layers": 1, "private_training_path": "/example/omitted"}}
    source = directory / "generated.ckpt"
    torch.save(payload, str(source))
    kwargs = dict(expected_sha256=file_sha256(source), repository="example/generated",
                  repository_type="dataset", revision="0" * 40)
    original = torch.load
    with patch.object(torch, "load", wraps=original) as load:
        manifest = convert_checkpoint(source, directory / "converted", **kwargs)
        assert len(manifest["tensors"]) == len(state)
        assert manifest["architecture_metadata"] == {"action_horizon_steps": 2, "action_num_layers": 1}
        assert "private_training_path" not in json.dumps(manifest)
        bad = directory / "unsupported.ckpt"
        torch.save(dict(payload, unsupported=UnsupportedMetadata()), str(bad))
        try:
            convert_checkpoint(bad, directory / "must-not-complete", **dict(kwargs, expected_sha256=file_sha256(bad)))
        except RuntimeError as error:
            assert "unsafe pickle fallback is disabled" in str(error)
        else:
            raise AssertionError("Unsupported serialized metadata was accepted")
        assert not (directory / "must-not-complete" / "manifest.json").exists()
        assert all(call.kwargs == {"map_location": "cpu", "weights_only": True}
                   for call in load.call_args_list)
    result = verify_generated_artifact(directory / "converted")
    result.update(alias_names_retained=True, scalar_empty_transposed_tensors_verified=True,
                  nan_signed_zero_bits_retained=True, unsupported_global_rejected=True,
                  source_checksum_verified=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, help="New fixture directory on a dedicated writable mount")
    parser.add_argument("--verify-only", type=Path, help="Read a trusted generated fixture from the CPU probe")
    args = parser.parse_args()
    if args.workspace and args.verify_only:
        parser.error("Select workspace or verify-only.")
    if args.verify_only:
        result = verify_generated_artifact(args.verify_only)
    elif args.workspace:
        args.workspace.mkdir(mode=0o700)
        result = run(args.workspace)
    else:
        with tempfile.TemporaryDirectory(prefix="checkpoint-conversion-") as directory:
            result = run(Path(directory))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
