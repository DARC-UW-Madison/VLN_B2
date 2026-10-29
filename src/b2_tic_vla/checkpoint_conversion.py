"""Local CPU conversion to tensor data; acquisition and permission are separate.

The caller must use the reviewed offline, unprivileged container and immutable
input mount. This module neither downloads files nor grants redistribution.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import hashlib
import importlib
import json
from pathlib import Path
import platform
import re
import stat

from .inference import _load_local_checkpoint


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_metadata(repository, repository_type, revision):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Use a repository identifier, not a URL or local path.")
    if repository_type not in ("dataset", "model"):
        raise ValueError("Repository type must be dataset or model.")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Use a pinned 40-character repository revision.")
    return {"repository": repository, "repository_type": repository_type, "revision": revision}


def tensor_state(payload, torch, max_tensor_bytes):
    if not isinstance(payload, Mapping) or not payload:
        raise ValueError("Expected a nonempty checkpoint mapping.")
    state = payload.get("state_dict", payload)
    if not isinstance(state, Mapping) or not state or len(state) > 100000:
        raise ValueError("Expected a bounded, nonempty tensor state mapping.")
    allowed = {torch.bool, torch.uint8, torch.int8, torch.int16, torch.int32,
               torch.int64, torch.float16, torch.bfloat16, torch.float32, torch.float64}
    total = 0
    for name, value in state.items():
        if not isinstance(name, str) or not name or len(name) > 1024 or "\0" in name:
            raise ValueError("Tensor names must be bounded nonempty strings without NUL.")
        if (not isinstance(value, torch.Tensor) or value.layout != torch.strided
                or value.device.type != "cpu" or value.is_quantized
                or getattr(value, "is_nested", False) or value.dtype not in allowed):
            raise ValueError("Only supported dense CPU tensors can be converted.")
        total += value.numel() * value.element_size()
        if total > max_tensor_bytes:
            raise ValueError("Tensor data exceeds the configured output budget.")
    return dict(state), total


def architecture_metadata(payload):
    metadata = payload.get("hyper_parameters", {})
    if not isinstance(metadata, Mapping):
        raise ValueError("Checkpoint hyper_parameters must be a mapping.")
    selected = {}
    for key in ("action_horizon_steps", "action_num_layers"):
        if key in metadata:
            if type(metadata[key]) is not int or metadata[key] < 1:
                raise ValueError("Architecture metadata must contain positive integers.")
            selected[key] = metadata[key]
    return selected


def tensor_record(value):
    # Byte views preserve NaN payloads and signed zeros, unlike numeric equality.
    data = value.detach().contiguous().reshape(-1).view(importlib.import_module("torch").uint8)
    digest = hashlib.sha256(memoryview(data.numpy())).hexdigest()
    return {"dtype": str(value.dtype), "shape": list(value.shape), "sha256": digest}


def convert_checkpoint(source, output, expected_sha256, repository, repository_type,
                       revision, max_input_bytes=3 * 1024**3, max_tensor_bytes=4 * 1024**3):
    provenance = source_metadata(repository, repository_type, revision)
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("An expected lowercase SHA256 is required.")
    if any(type(limit) is not int or limit < 1 for limit in (max_input_bytes, max_tensor_bytes)):
        raise ValueError("Input and tensor budgets must be positive integers.")
    source, output = Path(source), Path(output)
    if source.suffix.lower() == ".safetensors":
        raise ValueError("This converter expects the original serialized checkpoint.")
    if output.exists() or output.is_symlink():
        raise FileExistsError("The conversion output directory must not already exist.")
    source_stat = source.stat()
    if not stat.S_ISREG(source_stat.st_mode):
        raise ValueError("The checkpoint input must be a regular file.")
    size = source_stat.st_size
    if size > max_input_bytes:
        raise ValueError("Source checkpoint exceeds the configured input budget.")
    if file_sha256(source) != expected_sha256:
        raise ValueError("Source SHA256 mismatch; checkpoint was not decoded.")
    torch = importlib.import_module("torch")
    if torch.version.cuda is not None:
        raise RuntimeError("Use the reviewed CPU-only PyTorch environment for conversion.")
    payload = _load_local_checkpoint(source, torch)
    if file_sha256(source) != expected_sha256:
        raise ValueError("Source changed during decoding; conversion was stopped.")
    state, raw_bytes = tensor_state(payload, torch, max_tensor_bytes)
    metadata = architecture_metadata(payload)
    # Do not filter names, normalize prefixes or remove tied aliases here.
    independent = {name: value.detach().contiguous().clone() for name, value in state.items()}
    expected = {name: tensor_record(value) for name, value in state.items()}
    output.mkdir(mode=0o700)
    tensor_path = output / "model.safetensors"
    safetensors = importlib.import_module("safetensors")
    io = importlib.import_module("safetensors.torch")
    io.save_file(independent, str(tensor_path))
    if tensor_path.stat().st_size > max_tensor_bytes + 128 * 1024**2:
        raise ValueError("Serialized output exceeds the tensor and header budget.")
    restored = io.load_file(str(tensor_path), device="cpu")
    if restored.keys() != state.keys() or any(tensor_record(restored[name]) != expected[name]
                                              for name in state):
        raise ValueError("Tensor readback verification failed; no success manifest was written.")
    manifest = {
        "schema_version": 1,
        "source": dict(provenance, filename=source.name, sha256=expected_sha256, bytes=size),
        "output": {"filename": tensor_path.name, "sha256": file_sha256(tensor_path),
                   "bytes": tensor_path.stat().st_size},
        "conversion": {"python": platform.python_version(), "torch": str(torch.__version__),
                       "safetensors": str(safetensors.__version__),
                       "tool_sha256": file_sha256(Path(__file__)),
                       "alias_strategy": "independent_contiguous_copy_for_every_original_name",
                       "max_input_bytes": max_input_bytes, "max_tensor_bytes": max_tensor_bytes,
                       "tensor_data_bytes": raw_bytes},
        "architecture_metadata": metadata,
        "tensors": expected,
        "verified": True,
    }
    # The manifest is the last completion marker. Retain incomplete output for review.
    with (output / "manifest.json").open("x") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("output", help="A new directory under the approved output mount")
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--repository-type", required=True, choices=("dataset", "model"))
    parser.add_argument("--revision", required=True)
    parser.add_argument("--max-input-bytes", type=int, default=3 * 1024**3)
    parser.add_argument("--max-tensor-bytes", type=int, default=4 * 1024**3)
    args = parser.parse_args(argv)
    result = convert_checkpoint(args.source, args.output, args.expected_sha256,
                                args.repository, args.repository_type, args.revision,
                                args.max_input_bytes, args.max_tensor_bytes)
    print(json.dumps({"verified": result["verified"], "tensor_keys": len(result["tensors"]),
                      "output_sha256": result["output"]["sha256"]}))


if __name__ == "__main__":
    main()
