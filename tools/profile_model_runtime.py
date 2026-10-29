"""Profile recorded-image inference with explicitly assumed stationary state; no robot I/O."""

import argparse
from contextlib import contextmanager
import hashlib
import importlib
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


def owned_cache(raw, torch, layers, feature_width):
    """Normalize only reviewed cache APIs, then take independent tensor ownership."""
    kind = type(raw).__name__
    if not isinstance(raw, (tuple, list)):
        if callable(getattr(raw, "to_legacy_cache", None)):
            raw = raw.to_legacy_cache()
        elif hasattr(raw, "layers"):
            raw = tuple((layer.keys, layer.values) for layer in raw.layers)
        else:
            raise TypeError("Unsupported semantic cache type")
    if len(raw) != layers:
        raise ValueError("Semantic cache layer count differs from the base model")
    total, result = 0, []
    for pair in raw:
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise ValueError("Expected key/value pairs in every cache layer")
        for tensor in pair:
            if not isinstance(tensor, torch.Tensor) or tensor.ndim != 4:
                raise ValueError("Expected rank-four key/value tensors")
            if tensor.shape[0] != 1 or min(tensor.shape) <= 0:
                raise ValueError("Expected a nonempty single-observation cache")
            if not torch.isfinite(tensor).all().item():
                raise ValueError("Semantic cache contains nonfinite values")
            total += tensor.numel() * tensor.element_size()
        if pair[0].shape != pair[1].shape or pair[1].shape[1] * pair[1].shape[-1] != feature_width:
            raise ValueError("Cache shape differs from the action decoder interface")
    if total > 512 * 1024 * 1024:
        raise ValueError("Cache exceeds the 512 MiB diagnostic clone budget")
    for pair in raw:
        result.append(tuple(t.detach().clone().contiguous() for t in pair))
    return tuple(result), {"source_type": kind, "layers": len(result), "bytes": total,
                           "layer_shapes": [list(pair[1].shape) for pair in result]}


def cache_digest(cache, torch):
    value = hashlib.sha256()
    for pair in cache:
        for tensor in pair:
            value.update(str((str(tensor.dtype), tuple(tensor.shape))).encode())
            value.update(tensor.detach().contiguous().view(torch.uint8).cpu().numpy().tobytes())
    return value.hexdigest()


def check_cached_actions(predictor, image, plan, raw_cache, reference_at, count, torch):
    model = predictor._model
    cache, report = owned_cache(raw_cache, torch, model.vlm.language_model.config.num_hidden_layers,
                                model.action_expert.kv_cache_proj.in_features)
    before = cache_digest(cache, torch)
    load_image = importlib.import_module("ticvla.models.ticvla").load_image

    def action(delay):
        started = time.monotonic()
        with torch.inference_mode():
            pixels = load_image(str(image), input_size=448, max_num=1).to(
                device="cuda:0", dtype=torch.bfloat16)
            visual = model.vlm.extract_feature(pixels)
            visual = visual.reshape(-1, visual.shape[-1]).unsqueeze(0)
            state = torch.tensor([0., 0., 0., 0., 0., delay], device="cuda:0",
                                 dtype=torch.bfloat16).reshape(1, 6, 1)
            output = model.action_expert(visual, state, kv_cache=cache)
            if tuple(output.shape) != (1, len(plan.points), 2) or not torch.isfinite(output).all().item():
                raise ValueError("Cached action output has invalid shape or values")
            torch.cuda.synchronize()
        return output.float(), time.monotonic() - started

    reference = torch.tensor([[[p.x, p.y] for p in plan.points]], device="cuda:0", dtype=torch.float32)
    parity, parity_seconds = action(0.)
    torch.testing.assert_close(parity, reference, rtol=0., atol=0.001)
    report.update(zero_delay_parity_passed=True, parity_atol_m=0.001,
                  parity_max_abs_difference=float((parity - reference).abs().max().item()),
                  parity_seconds=parity_seconds, runs=[],
                  reference_time_basis="offline replay host time before semantic inference; not camera capture")
    for index in range(count):
        age = time.monotonic() - reference_at
        output, seconds = action(age)
        report["runs"].append({"index": index, "model_delay_s": age, "seconds": seconds,
                               "waypoint_count": output.shape[1]})
    after = cache_digest(cache, torch)
    if before != after:
        raise ValueError("Action reuse mutated the owned semantic cache")
    report.update(cache_unchanged=True, cache_sha256=before,
                  concurrent_execution_tested=False, physical_delay_limit_validated=False)
    return report


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
    parser.add_argument("--cached-actions", type=int, choices=range(6), default=0,
                        help="Explicit numerical reuse/parity checks; no live worker or control")
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
                captured = []
                handle = None
                if args.cached_actions:
                    def capture(module, inputs, kwargs, output):
                        if kwargs.get("use_cache") is True:
                            captured.append(getattr(output, "past_key_values", None))
                    handle = predictor._model.vlm.register_forward_hook(capture, with_kwargs=True)
                started = time.monotonic()
                try:
                    with stage_measurements(predictor._model, torch.cuda.synchronize, events):
                        plan = predictor.predict([str(args.image)], args.instruction, state, observed)
                finally:
                    if handle is not None:
                        handle.remove()
                torch.cuda.synchronize()
                report["runs"].append({
                    "index": index, "seconds": time.monotonic() - started,
                    "stages": events, "waypoint_count": len(plan.points),
                    "waypoints": [{"x": p.x, "y": p.y, "time_from_now": p.time_from_now}
                                  for p in plan.points],
                    "torch_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                })
            if args.cached_actions:
                if len(captured) != 1 or captured[0] is None:
                    raise ValueError("Expected exactly one complete semantic-cache forward output")
                report["cached_actions"] = check_cached_actions(
                    predictor, args.image, plan, captured[0], observed, args.cached_actions, torch)
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
