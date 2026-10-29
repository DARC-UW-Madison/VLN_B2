"""Explicit offline load and optional synthetic-image smoke; never robot I/O."""

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
    parser.add_argument("--synthetic-inference", action="store_true",
                        help="Explicitly run one generated-image smoke; never a navigation evaluation")
    args = parser.parse_args(argv)
    if args.checkpoint.suffix.lower() != ".safetensors":
        parser.error("The GPU verifier accepts only the reviewed converted safetensors input.")
    # Reserve a new report before any runtime import or model construction.
    with args.report.open("x") as stream:
        report = {"passed": False, "model_constructed": False, "inference_run": False,
                  "robot_connected": False, "motion_sent": False}
        started = time.monotonic()
        try:
            report["stage"] = "checkpoint_checksum"
            if os.environ.get("HF_HUB_OFFLINE") != "1":
                raise ValueError("Run this verifier with offline Hub resolution and network isolation.")
            actual = digest(args.checkpoint)
            if actual != args.expected_sha256:
                raise ValueError("Converted checkpoint SHA256 mismatch; model was not constructed.")
            from b2_tic_vla.inference import TicVlaPredictor
            import torch

            report["stage"] = "cuda_initialization"
            torch.cuda.init()
            torch.cuda.set_device(args.device)
            torch.cuda.reset_peak_memory_stats(args.device)
            report["stage"] = "strict_model_loading"
            load_started = time.monotonic()
            predictor = TicVlaPredictor(args.base_model, args.checkpoint, args.device,
                                        args.upstream_root).load()
            torch.cuda.synchronize(args.device)
            report.update(
                model_constructed=True,
                load_seconds=time.monotonic() - load_started,
                checkpoint_sha256=actual, torch_version=str(torch.__version__),
                parameter_count=sum(value.numel() for value in predictor._model.parameters()),
                torch_allocated_bytes=torch.cuda.memory_allocated(args.device),
                torch_peak_allocated_bytes=torch.cuda.max_memory_allocated(args.device),
                description=predictor.describe(),
                base_config_sha256=digest(args.base_model / "config.json"),
                custom_python_sha256={p.name: digest(p) for p in args.base_model.glob("*.py")},
            )
            if args.synthetic_inference:
                from PIL import Image, ImageDraw
                from b2_tic_vla.types import RobotState

                report["stage"] = "synthetic_input_creation"
                image_path = args.report.with_name("generated-frame.png")
                if image_path.exists():
                    raise FileExistsError("Use a new fixture/report directory.")
                image = Image.new("RGB", (448, 448), (160, 160, 160))
                ImageDraw.Draw(image).rectangle((150, 70, 300, 400), outline=(30, 30, 30), width=6)
                image.save(image_path)
                observed = time.monotonic()
                state = RobotState(observed, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                   velocity_frame="base_link")
                torch.cuda.reset_peak_memory_stats(args.device)
                report.update(stage="synthetic_inference", inference_run=True,
                              synthetic_input=True, real_camera_used=False)
                plan = predictor.predict([str(image_path)], "Move straight ahead.", state, observed)
                torch.cuda.synchronize(args.device)
                report.update(
                    inference_completed=True,
                    inference_seconds=predictor.describe()["last_runtime_seconds"],
                    waypoint_count=len(plan.points),
                    waypoints=[{"x": point.x, "y": point.y, "time_from_now": point.time_from_now}
                               for point in plan.points],
                    inference_torch_peak_allocated_bytes=torch.cuda.max_memory_allocated(args.device),
                    synthetic_image_sha256=digest(image_path),
                    navigation_quality_evaluated=False,
                )
            report.update(passed=True, stage="complete")
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
