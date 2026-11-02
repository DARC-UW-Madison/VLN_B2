"""Record a bounded RGB observation stream; no robot, model or network clients.

Duration bounds the capture window after camera open. A native SDK call or
device hang still requires an external process timeout. Consumers must check
frame receipt age using the shared host monotonic clock; SDK time is unverified.
"""

import argparse
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
import traceback


MODE = "camera_stream_observation_only"


def _make_camera(settings_directory, timeout_s):
    # The CLI help and argument validation do not require the project/vendor SDK.
    from b2_tic_vla.hardware import ZedCamera

    return ZedCamera(settings_directory=str(settings_directory), timeout_s=timeout_s)


def _digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_new_json(path, value):
    encoded = json.dumps(value, indent=2, allow_nan=False) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())


def _publish_latest(directory, value):
    """Publish a complete manifest while retaining the previous one on failure."""
    encoded = json.dumps(value, indent=2, allow_nan=False) + "\n"
    descriptor, name = tempfile.mkstemp(prefix=".latest-", suffix=".json", dir=directory)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, directory / "latest.json")
    finally:
        temporary.unlink(missing_ok=True)


def record_stream(output_directory, settings_directory, duration, fps):
    """Own a new output directory and close the adapter even if open fails."""
    if not math.isfinite(duration) or not 0 < duration <= 60:
        raise ValueError("duration must be finite and in (0, 60] seconds")
    if not math.isfinite(fps) or not 0 < fps <= 10:
        raise ValueError("fps must be finite and in (0, 10]")
    settings = Path(settings_directory).expanduser().resolve(strict=True)
    if not settings.is_dir():
        raise ValueError("settings directory must be an existing directory")
    requested = Path(output_directory).expanduser()
    directory = requested.parent.resolve(strict=True) / requested.name
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    camera = None
    started = time.monotonic()
    stream_started = None
    summary = {"schema_version": 1, "mode": MODE, "passed": False, "frames": 0,
               "published_frames": 0, "requested_duration_s": duration, "fps": fps,
               "producer_clock": "host_monotonic", "clock_unverified": True,
               "robot_connected": False, "robot_state_received": False,
               "motion_sent": False}
    try:
        camera = _make_camera(settings, min(5.0, duration))
        camera.open()
        stream_started = time.monotonic()
        deadline = stream_started + duration
        period = 1.0 / fps
        next_capture = stream_started
        while True:
            now = time.monotonic()
            if now >= deadline:
                break
            if now < next_capture:
                time.sleep(min(next_capture - now, deadline - now))
                continue
            # Bound adapter retries by the remaining window, where the SDK allows.
            camera.timeout_s = min(5.0, deadline - now)
            sequence = summary["frames"] + 1
            image = directory / f"frame-{sequence:06d}.jpg"
            if image.exists() or image.is_symlink():
                raise FileExistsError(f"Refusing to overwrite an existing image: {image.name}")
            frame = camera.capture(str(image))
            if image.is_symlink() or not image.is_file() or image.stat().st_size == 0:
                raise RuntimeError("Camera did not produce a nonempty regular image file")
            if Path(frame.path).resolve(strict=True) != image.resolve(strict=True):
                raise RuntimeError("Camera returned a different image path")
            # Image bytes are append-only; even the producer no longer opens them writable.
            image.chmod(0o400)
            frame_fields = asdict(frame)
            frame_fields["path"] = image.name
            manifest = {"schema_version": 1, "mode": MODE, "sequence": sequence,
                        "frame": frame_fields, "image_sha256": _digest(image),
                        "producer_clock": "host_monotonic", "motion_sent": False}
            _write_new_json(directory / f"frame-{sequence:06d}.json", manifest)
            summary["frames"] += 1
            _publish_latest(directory, manifest)
            summary["published_frames"] += 1
            completed = time.monotonic()
            next_capture += period
            # Advance to a future slot instead of replaying missed capture times.
            if next_capture <= completed:
                next_capture += (math.floor((completed - next_capture) / period) + 1) * period
        if not summary["frames"]:
            raise RuntimeError("No frames were recorded during the capture window")
        summary["passed"] = True
    except (Exception, KeyboardInterrupt) as error:
        summary.update(error_type=type(error).__name__, error=str(error))
        traceback.print_exc()
    finally:
        if camera is not None:
            try:
                camera.close()
            except Exception as error:
                summary.update(passed=False, close_error_type=type(error).__name__,
                               close_error=str(error))
                traceback.print_exc()
        finished = time.monotonic()
        summary["duration_s"] = finished - started
        summary["stream_duration_s"] = (finished - stream_started
                                        if stream_started is not None else 0.0)
        _write_new_json(directory / "summary.json", summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New private directory; its parent must already exist")
    parser.add_argument("--settings-dir", type=Path, required=True,
                        help="Existing dedicated writable ZED calibration/settings directory")
    parser.add_argument("--duration", type=float, required=True,
                        help="Finite capture window after camera open, in (0, 60] seconds")
    parser.add_argument("--fps", type=float, default=5.0,
                        help="Finite target capture rate in (0, 10] (default: 5)")
    args = parser.parse_args(argv)
    if not math.isfinite(args.duration) or not 0 < args.duration <= 60:
        parser.error("--duration must be finite and in (0, 60] seconds")
    if not math.isfinite(args.fps) or not 0 < args.fps <= 10:
        parser.error("--fps must be finite and in (0, 10]")
    previous_umask = os.umask(0o077)
    try:
        try:
            summary = record_stream(args.output_dir, args.settings_dir, args.duration, args.fps)
        except Exception as error:
            traceback.print_exc()
            summary = {"passed": False, "error_type": type(error).__name__, "error": str(error),
                       "robot_connected": False, "motion_sent": False}
        print(json.dumps(summary, indent=2, allow_nan=False))
        return 0 if summary["passed"] else 1
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    sys.exit(main())
