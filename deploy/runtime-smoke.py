"""Model-free container checks; no robot access, asset downloads or checkpoint loads.

Use an offline container with no camera, robot sockets or model/cache mounts.
The optional full check imports a reviewed upstream source checkout without
constructing a model. The candidate Torch version is restricted to these tests.
"""

from __future__ import annotations

import argparse
import ctypes
import importlib
import importlib.metadata
import inspect
import json
import os
import platform
import sys
import time
from pathlib import Path


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _python_check() -> dict:
    _require(platform.machine() == "aarch64", "Expected a native aarch64 container.")
    _require(sys.version_info[:2] == (3, 11), "Expected the isolated Python 3.11 interpreter.")
    for name in ("bz2", "lzma", "sqlite3", "ssl"):
        importlib.import_module(name)
    cuda = ctypes.CDLL("libcuda.so.1")
    cuda.cuInit.argtypes = [ctypes.c_uint]
    cuda.cuInit.restype = ctypes.c_int
    _require(cuda.cuInit(0) == 0, "CUDA driver initialization failed inside the container.")
    count = ctypes.c_int()
    cuda.cuDeviceGetCount.argtypes = [ctypes.POINTER(ctypes.c_int)]
    cuda.cuDeviceGetCount.restype = ctypes.c_int
    _require(cuda.cuDeviceGetCount(ctypes.byref(count)) == 0 and count.value > 0,
             "No CUDA device is visible inside the container.")
    return {"python": platform.python_version(), "architecture": platform.machine(),
            "cuda_driver_devices": count.value}


def _torch_check() -> dict:
    torch = importlib.import_module("torch")
    vision = importlib.import_module("torchvision")
    _require(torch.__version__.split("+")[0] == "2.2.2", "Expected source-built Torch 2.2.2.")
    _require(vision.__version__.split("+")[0] == "0.17.2", "Expected matching torchvision 0.17.2.")
    _require(torch.version.cuda == "11.4", "Expected a CUDA 11.4 Torch build.")
    _require(torch.cuda.is_available(), "Torch cannot initialize a CUDA device.")
    _require(torch.cuda.get_device_capability() == (8, 7), "Expected Orin compute capability 8.7.")
    _require(torch.distributed.is_available(), "Torch distributed API must be compiled for imports.")
    _require("weights_only" in inspect.signature(torch.load).parameters,
             "The required restricted-loading argument is missing.")
    _require(torch.cuda.is_bf16_supported(), "The candidate requires BF16 support.")
    torch.manual_seed(0)
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()
    started = time.perf_counter()
    operations = []
    with torch.inference_mode():
        for dtype in (torch.float32, torch.bfloat16):
            matrix = torch.randn(128, 128, device="cuda", dtype=dtype)
            outputs = {
                "matmul": matrix @ matrix.T,
                "conv2d": torch.nn.functional.conv2d(
                    torch.randn(1, 3, 16, 16, device="cuda", dtype=dtype),
                    torch.randn(4, 3, 3, 3, device="cuda", dtype=dtype)),
                "layer_norm": torch.nn.functional.layer_norm(matrix, (128,)),
            }
            attention = torch.nn.MultiheadAttention(32, 4, batch_first=True,
                                                   device="cuda", dtype=dtype).eval()
            tokens = torch.randn(2, 8, 32, device="cuda", dtype=dtype)
            outputs["multihead_attention"] = attention(tokens, tokens, tokens, need_weights=False)[0]
            for name, output in outputs.items():
                _require(output.is_cuda and bool(torch.isfinite(output).all().item()),
                         f"{name} did not produce finite CUDA output for {dtype}.")
                operations.append({"operation": name, "dtype": str(dtype),
                                   "shape": list(output.shape), "finite": True})
    torch.cuda.synchronize()
    return {"torch": torch.__version__, "torchvision": vision.__version__,
            "torch_git_revision": torch.version.git_version, "cuda": torch.version.cuda,
            "compute_capability": list(torch.cuda.get_device_capability()),
            "bf16_supported": True, "distributed_compiled": True,
            "operations": operations, "elapsed_seconds": time.perf_counter() - started,
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "checkpoint_loading_allowed": False}


def _full_import_check(upstream_root: str | None) -> dict:
    _require(upstream_root is not None, "The full check requires --upstream-root.")
    root = Path(upstream_root).resolve()
    _require((root / "ticvla/models/ticvla.py").is_file(), "Expected a reviewed upstream checkout.")
    expected = {"transformers": "4.44.2", "pytorch-lightning": "2.2.5",
                "torchmetrics": "1.2.1", "timm": "0.9.12", "einops": "0.7.0"}
    for name, version in expected.items():
        _require(importlib.metadata.version(name) == version, f"Unexpected installed version for {name}.")
    for name in ("transformers", "pytorch_lightning", "torchmetrics", "timm", "einops"):
        importlib.import_module(name)
    sys.path.insert(0, str(root))
    try:
        module = importlib.import_module("ticvla.models.ticvla")
        _require(Path(module.__file__).resolve().is_relative_to(root),
                 "A different ticvla package was imported.")
    finally:
        sys.path.remove(str(root))
    return {"versions": expected, "ticvla_imported": True, "model_constructed": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("python", "torch", "full"), default="torch")
    parser.add_argument("--upstream-root", help="Read-only mount of a reviewed pinned upstream checkout")
    args = parser.parse_args(argv)
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_DATASETS_OFFLINE="1")
    result = {"schema_version": 1, "stage": args.stage, "model_loaded": False,
              "motion_sent": False, "checkpoint_loading_allowed": False}
    try:
        result["python_check"] = _python_check()
        if args.stage in {"torch", "full"}:
            result["torch_check"] = _torch_check()
        if args.stage == "full":
            result["imports"] = _full_import_check(args.upstream_root)
        result["status"] = "passed"
    except Exception as error:
        result.update(status="failed", error_type=type(error).__name__, error=str(error))
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
