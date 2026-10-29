"""Explicit offline model construction check; no images, inference or robot I/O."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args(argv)
    if args.checkpoint.suffix.lower() != ".safetensors":
        parser.error("The GPU verifier accepts only the reviewed converted safetensors input.")
    # Reserve a new report before any runtime import or model construction.
    with args.report.open("x") as stream:
        report = {"passed": False, "model_constructed": False, "inference_run": False,
                  "robot_connected": False, "motion_sent": False}
        started = time.monotonic()
        try:
            if os.environ.get("HF_HUB_OFFLINE") != "1":
                raise ValueError("Run this verifier with offline Hub resolution and network isolation.")
            actual = digest(args.checkpoint)
            if actual != args.expected_sha256:
                raise ValueError("Converted checkpoint SHA256 mismatch; model was not constructed.")
            from b2_tic_vla.inference import TicVlaPredictor
            import torch

            torch.cuda.reset_peak_memory_stats(args.device)
            load_started = time.monotonic()
            predictor = TicVlaPredictor(args.base_model, args.checkpoint, args.device,
                                        args.upstream_root).load()
            torch.cuda.synchronize(args.device)
            report.update(
                passed=True, model_constructed=True, load_seconds=time.monotonic() - load_started,
                checkpoint_sha256=actual, torch_version=str(torch.__version__),
                parameter_count=sum(value.numel() for value in predictor._model.parameters()),
                torch_allocated_bytes=torch.cuda.memory_allocated(args.device),
                torch_peak_allocated_bytes=torch.cuda.max_memory_allocated(args.device),
                description=predictor.describe(),
                base_config_sha256=digest(args.base_model / "config.json"),
                custom_python_sha256={p.name: digest(p) for p in args.base_model.glob("*.py")},
            )
        except Exception as error:
            report.update(error_type=type(error).__name__, error=str(error))
            traceback.print_exc()
        report["wall_seconds_including_checksum"] = time.monotonic() - started
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: report[key] for key in
                      ("passed", "model_constructed", "inference_run", "robot_connected", "motion_sent")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
