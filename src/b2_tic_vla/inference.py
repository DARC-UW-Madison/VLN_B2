"""Optional synchronous TIC-VLA inference for recorded images, never robot control.

The external package and model files must already exist locally. This adapter
does not install software, fetch assets, or implement asynchronous deployment.
"""

from __future__ import annotations

import importlib
import math
import os
import pickle
import re
import sys
import time
from collections.abc import Mapping
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch

from .types import Plan, RobotState, Waypoint


@contextmanager
def _offline_loaders():
    """Require local files even if Transformers was imported before this module."""
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
        }))
        transformers = importlib.import_module("transformers")
        for name in ("AutoModel", "AutoTokenizer", "AutoProcessor"):
            loader = getattr(transformers, name)
            original = loader.from_pretrained

            def local_loader(*args, _original=original, **kwargs):
                kwargs["local_files_only"] = True
                return _original(*args, **kwargs)

            stack.enter_context(patch.object(loader, "from_pretrained", local_loader))
        yield


def _checkpoint_state(checkpoint):
    if not isinstance(checkpoint, Mapping) or not checkpoint:
        raise ValueError("Checkpoint must contain a nonempty state dictionary.")
    state = checkpoint.get("state_dict", checkpoint)
    if not isinstance(state, Mapping) or not state:
        raise ValueError("Checkpoint state_dict must be a nonempty mapping.")
    if any(not isinstance(key, str) for key in state):
        raise ValueError("Checkpoint state dictionary keys must be strings.")
    state = dict(state)
    # Lightning adds model.; distributed/compiled wrappers may add one prefix.
    # Only strip a prefix shared by every key, never filter individual keys.
    for prefix in ("module.", "_orig_mod.", "model."):
        if all(key.startswith(prefix) for key in state):
            state = {key[len(prefix):]: value for key, value in state.items()}
    return state


def _architecture(state, checkpoint):
    embedding = state.get("action_expert.action_chunk_embed.weight")
    shape = getattr(embedding, "shape", ())
    if len(shape) != 2 or shape[0] < 1 or shape[1] != 512:
        raise ValueError("Expected action_chunk_embed.weight with shape (horizon, 512).")
    indices = {
        int(match.group(1))
        for key in state
        if (match := re.match(r"action_expert\.attention_layers\.(\d+)\.", key))
    }
    if not indices or indices != set(range(max(indices) + 1)):
        raise ValueError("Checkpoint must contain contiguous action attention layers starting at 0.")
    horizon, layers = int(shape[0]), len(indices)
    metadata = checkpoint.get("hyper_parameters", {})
    if not isinstance(metadata, Mapping):
        raise ValueError("Checkpoint hyper_parameters must be a mapping when present.")
    for key, expected in (("action_horizon_steps", horizon), ("action_num_layers", layers)):
        if key in metadata and metadata[key] != expected:
            raise ValueError(f"Checkpoint {key} metadata disagrees with its weights.")
    return horizon, layers


class TicVlaPredictor:
    """Run the current upstream package's synchronous, zero-cache-delay API.

    Only standard full-model state dictionaries (optionally wrapped by
    Lightning's state_dict) are supported. Incompatible published checkpoints
    fail closed rather than silently leaving untrained layers in use.
    """

    def __init__(self, base_model_path, checkpoint_path, device="cuda:0", upstream_root=None):
        self.base_model_path = Path(base_model_path).expanduser().resolve()
        self.checkpoint_path = Path(checkpoint_path).expanduser().resolve()
        self.device = str(device)
        self.upstream_root = Path(upstream_root).expanduser().resolve() if upstream_root else None
        self._model = None
        self._torch = None
        self._horizon = None
        self._layers = None
        self._last_runtime_seconds = None

    def load(self):
        """Load trusted existing local files with safe checkpoint deserialization."""
        if self._model is not None:
            return self
        if not self.base_model_path.is_dir() or not (self.base_model_path / "config.json").is_file():
            raise ValueError("base_model_path must be an existing local model directory containing config.json.")
        if not self.checkpoint_path.is_file():
            raise FileNotFoundError(f"Local checkpoint does not exist: {self.checkpoint_path}")
        if self.upstream_root is not None:
            if not (self.upstream_root / "ticvla" / "models" / "ticvla.py").is_file():
                raise ValueError("upstream_root must contain ticvla/models/ticvla.py.")
        with _offline_loaders():
            torch = importlib.import_module("torch")
            try:
                checkpoint = torch.load(str(self.checkpoint_path), map_location="cpu", weights_only=True)
            except pickle.UnpicklingError as error:
                raise RuntimeError(
                    "Checkpoint cannot be decoded with weights_only=True. "
                    "Use a compatible weights-only artifact; unsafe pickle fallback is disabled."
                ) from error
            except TypeError as error:
                raise RuntimeError("This adapter requires torch.load(weights_only=True); upgrade PyTorch. Unsafe pickle loading is disabled.") from error
            state = _checkpoint_state(checkpoint)
            horizon, layers = _architecture(state, checkpoint)
            root = str(self.upstream_root) if self.upstream_root else None
            if root:
                sys.path.insert(0, root)
            try:
                module = importlib.import_module("ticvla.models.ticvla")
                if self.upstream_root is not None:
                    origin = Path(module.__file__).resolve()
                    if not origin.is_relative_to(self.upstream_root):
                        raise RuntimeError("A different ticvla package is already imported; restart with the requested upstream_root.")
                model = module.TICVLA(
                    model_path=str(self.base_model_path),
                    action_horizon_steps=horizon,
                    action_num_layers=layers,
                    train_vlm=False,
                )
                # Check keys before loading, then let strict=True check every shape.
                expected = set(model.state_dict())
                missing, unexpected = sorted(expected - state.keys()), sorted(state.keys() - expected)
                if missing or unexpected:
                    raise ValueError(f"Checkpoint is incompatible: missing keys={missing[:8]}, unexpected keys={unexpected[:8]}.")
                model.load_state_dict(state, strict=True)
                model.to(device=self.device, dtype=torch.bfloat16)
                requested_device = str(torch.device(self.device))
                if requested_device == "cuda":
                    requested_device = f"cuda:{torch.cuda.current_device()}"
                actual_device = str(getattr(model, "device", "unknown"))
                if actual_device != requested_device:
                    raise RuntimeError(
                        f"Upstream model reports device {actual_device} after moving to "
                        f"{requested_device}; use a compatible package with a parameter-based device property."
                    )
                model.eval()
            finally:
                if root:
                    sys.path.remove(root)
        self._model, self._torch = model, torch
        self._horizon, self._layers = horizon, layers
        return self

    def predict(self, image_paths: list[str], instruction: str, state: RobotState, observation_at: float) -> Plan:
        """Predict one plan from images ordered oldest to newest; send no commands."""
        if not isinstance(instruction, str) or not instruction.strip():
            raise ValueError("A nonempty navigation instruction is required.")
        if not image_paths or isinstance(image_paths, (str, bytes)):
            raise ValueError("Provide at least one local image path, ordered oldest to newest.")
        paths = []
        for item in image_paths:
            path = Path(item).expanduser().resolve()
            if not path.is_file():
                raise FileNotFoundError(f"Local image does not exist: {path}")
            if path.stat().st_size == 0:
                raise ValueError(f"Local image is empty: {path}")
            paths.append(str(path))
        if not math.isfinite(observation_at):
            raise ValueError("observation_at must be finite.")
        if observation_at > time.monotonic() + 0.001:
            raise ValueError("observation_at must use the host monotonic clock and cannot be in the future.")
        if state.velocity_frame not in {"base_link", "body"}:
            raise ValueError("Robot velocities must explicitly use the base_link/body frame.")
        velocities = [state.vx, state.vy, state.yaw_rate]
        if not all(math.isfinite(value) for value in velocities):
            raise ValueError("Robot velocities must be finite.")
        if self._model is None:
            raise RuntimeError("Call load() before predict().")
        started = time.monotonic()
        # The upstream method may lazily construct a processor or other model.
        # Keep ordinary Hugging Face resolution local during inference as well.
        with _offline_loaders(), self._torch.inference_mode():
            _, output, _ = self._model.predict(
                delayed_image_paths=paths,
                current_image_path=paths[-1],
                instruction=instruction.strip(),
                robot_state=self._torch.tensor(velocities + [0.0, 0.0], device=self.device, dtype=self._torch.bfloat16),
                time_delay=0.0,
            )
        shape = tuple(getattr(output, "shape", ()))
        if shape != (1, self._horizon, 2):
            raise ValueError(f"Expected waypoint shape (1, {self._horizon}, 2), got {shape}.")
        rows = output.detach().float().cpu().tolist()[0]
        if not all(math.isfinite(value) for row in rows for value in row):
            raise ValueError("Model returned nonfinite waypoint coordinates.")
        self._last_runtime_seconds = time.monotonic() - started
        points = tuple(Waypoint(float(x), float(y), (index + 1) * 0.1) for index, (x, y) in enumerate(rows))
        return Plan(
            points=points,
            created_at=time.monotonic(),
            observation_at=observation_at,
            source="ticvla-sync",
            frame_id="base_link",
            cache_reference_at=observation_at,
        )

    def describe(self) -> dict:
        return {
            "loaded": self._model is not None,
            "mode": "offline synchronous inference only; no robot connection",
            "device": self.device,
            "action_horizon_steps": self._horizon,
            "action_num_layers": self._layers,
            "waypoint_interval_seconds": 0.1,
            "output": "XY positions relative to the current robot frame; no cumulative sum",
            "cache_delay_seconds": 0.0,
            "last_runtime_seconds": self._last_runtime_seconds,
            "timing": "observation_at and created_at use the host monotonic clock; recorded capture times remain separate source metadata, not verified host timestamps",
            "limitations": "Trusted local model code executes through upstream trust_remote_code; Hugging Face offline settings are not a sandbox for arbitrary Python code. Synchronous package smoke only; no asynchronous cache, controller, clearance verification, or real-time performance claim.",
        }
