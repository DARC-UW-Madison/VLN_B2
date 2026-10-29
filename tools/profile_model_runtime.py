"""Profile recorded-image inference with explicitly assumed stationary state; no robot I/O."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import random
import time
import traceback


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


@contextmanager
def stage_measurements(model, synchronize, events):
    """Measure disjoint top-level calls; exclude nested vision work from extra totals."""
    restored = []
    active = []

    def wrap(obj, name, label):
        original = getattr(obj, name)
        had_attribute = name in obj.__dict__
        previous = obj.__dict__.get(name)

        def measured(*args, **kwargs):
            if active:
                return original(*args, **kwargs)
            synchronize()
            started = time.monotonic()
            active.append(label)
            try:
                return original(*args, **kwargs)
            finally:
                try:
                    synchronize()
                    events.append({"stage": label, "seconds": time.monotonic() - started})
                finally:
                    active.pop()

        setattr(obj, name, measured)
        restored.append((obj, name, had_attribute, previous))

    try:
        wrap(model.vlm, "chat", "semantic_generation")
        wrap(model.vlm, "forward", "semantic_cache_forward")
        wrap(model.vlm, "extract_feature", "current_image_features")
        wrap(model.action_expert, "forward", "action_decoder")
        yield
    finally:
        for obj, name, had_attribute, previous in reversed(restored):
            if had_attribute:
                setattr(obj, name, previous)
            else:
                delattr(obj, name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--upstream-root", required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--assumed-stationary", action="store_true", required=True)
    parser.add_argument("--repeats", type=int, choices=[1, 2, 3], default=2)
    parser.add_argument("--instruction", default="Move straight ahead.")
    args = parser.parse_args(argv)
    report = {"passed": False, "model_constructed": False,
              "motion_sent": False, "robot_connected": False,
              "state_source": "assumed stationary; not received from a robot",
              "real_camera_input": "recorded file; capture provenance must be checked separately",
              "navigation_quality_evaluated": False, "seed_each_call": 0,
              "deterministic_algorithms_enabled": False,
              "measurement": "GPU synchronization at stage boundaries adds diagnostic overhead; not a control rate",
              "runs": []}
    with args.report.open("x", encoding="utf-8") as stream:
        try:
            if os.environ.get("HF_HUB_OFFLINE") != "1":
                raise ValueError("HF_HUB_OFFLINE=1 is required")
            if args.checkpoint.suffix != ".safetensors":
                raise ValueError("Only the verified converted safetensors file is accepted")
            if not args.image.is_file() or not 0 < args.image.stat().st_size <= 32 * 1024 * 1024:
                raise ValueError("Provide a nonempty local image of at most 32 MiB")
            if digest(args.checkpoint) != args.expected_sha256:
                raise ValueError("Checkpoint SHA256 mismatch")
            report.update(image_sha256=digest(args.image), checkpoint_sha256=args.expected_sha256)
            import numpy as np
            import torch
            from PIL import Image
            from b2_tic_vla.inference import TicVlaPredictor
            from b2_tic_vla.types import RobotState

            with Image.open(args.image) as image:
                report["image_size"] = list(image.size)
                image.verify()
            torch.cuda.init()
            torch.cuda.set_device("cuda:0")
            started = time.monotonic()
            predictor = TicVlaPredictor(args.base_model, str(args.checkpoint),
                                        "cuda:0", args.upstream_root).load()
            torch.cuda.synchronize()
            report.update(model_constructed=True, load_seconds=time.monotonic() - started,
                          model=predictor.describe(), torch_version=torch.__version__)
            for index in range(args.repeats):
                random.seed(0)
                np.random.seed(0)
                torch.manual_seed(0)
                torch.cuda.manual_seed_all(0)
                torch.cuda.reset_peak_memory_stats()
                observed = time.monotonic()
                state = RobotState(observed, 0., 0., 0., 0., 0., 0., velocity_frame="base_link")
                events = []
                started = time.monotonic()
                with stage_measurements(predictor._model, torch.cuda.synchronize, events):
                    plan = predictor.predict([str(args.image)], args.instruction, state, observed)
                torch.cuda.synchronize()
                report["runs"].append({
                    "index": index, "seconds": time.monotonic() - started,
                    "stages": events, "waypoint_count": len(plan.points),
                    "waypoints": [{"x": p.x, "y": p.y, "time_from_now": p.time_from_now}
                                  for p in plan.points],
                    "torch_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                })
            report["passed"] = True
        except Exception as error:
            report.update(error_type=type(error).__name__, error=str(error))
            traceback.print_exc()
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({k: report[k] for k in ("passed", "motion_sent", "robot_connected")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
