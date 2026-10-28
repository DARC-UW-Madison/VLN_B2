"""Disable Python RPC availability in the pinned build without TensorPipe.

The model-free image retains distributed/Gloo for library imports but has no
RPC backend. Torch 2.2.2 otherwise advertises RPC and imports missing TensorPipe
bindings. This is a local Python feature guard, not a checkpoint security fix.
The original wheel and its license notices remain in the image.
"""

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path


def main() -> None:
    distribution = importlib.metadata.distribution("torch")
    if distribution.version != "2.2.2" or os.environ.get("USE_TENSORPIPE") != "0":
        raise RuntimeError("This guard applies only to the pinned Torch build without TensorPipe.")
    target = Path(distribution.locate_file("torch/distributed/rpc/__init__.py"))
    original = target.read_bytes()
    expected = "7c0f5fc19a95400a78a0508aff291ccd2d2ce74aea7aa5ce967024a63d495913"
    if hashlib.sha256(original).hexdigest() != expected:
        raise RuntimeError("RPC source differs from the reviewed revision; do not patch it.")
    before = b'    return hasattr(torch._C, "_rpc_init")'
    after = b"    return False  # This image intentionally has no TensorPipe RPC backend."
    if original.count(before) != 1:
        raise RuntimeError("Expected exactly one RPC availability predicate.")
    modified = original.replace(before, after)
    target.write_bytes(modified)
    metadata = {
        "torch_revision": "39901f229520a5256505ec24782f716ee7ddc843",
        "path": "torch/distributed/rpc/__init__.py",
        "original_sha256": expected,
        "modified_sha256": hashlib.sha256(modified).hexdigest(),
        "change": "Report RPC unavailable because this image was built without TensorPipe.",
        "checkpoint_security_fix": False,
    }
    Path("/opt/runtime-metadata/torch-rpc-patch.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
