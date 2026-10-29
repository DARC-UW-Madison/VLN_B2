"""Read-only vendor adapters; no control clients or motion messages are created.

Receipt times use host monotonic seconds. Vendor timestamps are retained as
unverified source-clock seconds and must not be subtracted from receipt times.
"""

from __future__ import annotations

import importlib
import math
import re
import threading
import time
from pathlib import Path
from typing import Any

from .types import Frame, RobotState


def _vendor_module(name: str, installation: str) -> Any:
    try:
        return importlib.import_module(name)
    except (ImportError, OSError) as exc:
        raise RuntimeError(
            f"Cannot load {name}: {exc}. {installation} "
            "This command does not install or download dependencies."
        ) from exc


class ZedCamera:
    """Capture left rectified color images using an already installed ZED SDK.

    Attempts and recovery are bounded at the application level. An SDK/native
    driver hang still requires an external process timeout. This adapter does
    not enable tracking, depth inference, recording, or sensor fusion.
    """

    def __init__(self, *, max_grab_attempts: int = 30, timeout_s: float = 5.0,
                 settings_directory: str | None = None):
        if not isinstance(max_grab_attempts, int) or max_grab_attempts < 1:
            raise ValueError("max_grab_attempts must be a positive integer")
        if not math.isfinite(timeout_s) or timeout_s <= 0:
            raise ValueError("timeout_s must be positive and finite")
        self.max_grab_attempts = max_grab_attempts
        self.timeout_s = timeout_s
        self.settings_directory = None
        if settings_directory is not None:
            settings = Path(settings_directory).expanduser().resolve(strict=True)
            if not settings.is_dir():
                raise ValueError("Camera settings must be an existing directory")
            self.settings_directory = str(settings)
        self._sl: Any = None
        self._camera: Any = None
        self._image: Any = None
        self._runtime: Any = None

    def open(self) -> None:
        if self._camera is not None:
            return
        sl = _vendor_module(
            "pyzed.sl",
            "Install the official ZED SDK and its Python binding matching the Jetson environment.",
        )
        camera = sl.Camera()
        try:
            parameters = sl.InitParameters()
            parameters.camera_resolution = sl.RESOLUTION.HD720
            parameters.camera_fps = 30
            parameters.depth_mode = sl.DEPTH_MODE.NONE
            parameters.open_timeout_sec = self.timeout_s
            parameters.async_grab_camera_recovery = True
            if self.settings_directory is not None:
                parameters.optional_settings_path = self.settings_directory
            result = camera.open(parameters)
            if result != sl.ERROR_CODE.SUCCESS:
                raise RuntimeError(f"ZED camera open failed: {result}")
            image = sl.Mat()
            runtime = sl.RuntimeParameters()
        except Exception:
            camera.close()
            raise
        self._sl, self._camera = sl, camera
        self._image, self._runtime = image, runtime

    def capture(self, output_path: str) -> Frame:
        if self._camera is None:
            raise RuntimeError("Open the ZED camera before capture")
        path = Path(output_path)
        if path.suffix.lower() not in {".jpg", ".jpeg"}:
            raise ValueError("ZED capture output must use a .jpg or .jpeg extension")
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite an existing image: {path}")
        if not path.parent.is_dir():
            raise FileNotFoundError(f"Image output directory does not exist: {path.parent}")
        started = time.monotonic()
        result: Any = "no frames"
        for _ in range(self.max_grab_attempts):
            result = self._camera.grab(self._runtime)
            received_at = time.monotonic()
            if result == self._sl.ERROR_CODE.SUCCESS:
                break
            if received_at - started >= self.timeout_s:
                raise TimeoutError(f"No ZED image before the capture deadline: {result}")
            time.sleep(min(0.01, self.timeout_s - (received_at - started)))
        else:
            raise TimeoutError(f"No ZED image after {self.max_grab_attempts} attempts: {result}")

        source_timestamp = None
        try:
            nanoseconds = int(
                self._camera.get_timestamp(self._sl.TIME_REFERENCE.IMAGE).get_nanoseconds()
            )
            if nanoseconds > 0:
                source_timestamp = nanoseconds / 1_000_000_000
        except (AttributeError, TypeError, ValueError, OverflowError):
            pass
        result = self._camera.retrieve_image(self._image, self._sl.VIEW.LEFT)
        if result != self._sl.ERROR_CODE.SUCCESS:
            raise RuntimeError(f"ZED left image retrieval failed: {result}")
        result = self._image.write(str(path))
        if result != self._sl.ERROR_CODE.SUCCESS:
            raise RuntimeError(f"ZED image write failed: {result}")
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError("ZED SDK reported success but produced no image file")
        return Frame(
            path=str(path),
            received_at=received_at,
            captured_at=None,
            source_timestamp=source_timestamp,
            source_clock="zed_image_unverified" if source_timestamp is not None else None,
            timestamp_verified=False,
        )

    def close(self) -> None:
        camera, self._camera = self._camera, None
        self._image, self._runtime = None, None
        if camera is not None:
            camera.close()


_dds_lock = threading.Lock()
_dds_configuration: tuple[int, str] | None = None
_STATE_TOPICS = ("rt/sportmodestate", "rt/lf/sportmodestate")


class UnitreeStateReader:
    """Subscribe to sport state only; validity means finite fields, not readiness.

    The vendor DDS factory is process-global. Use a new process to change the
    network interface or domain. Frame conventions remain unknown until measured.
    """

    def __init__(self, interface: str, domain_id: int = 0, topic: str = "auto"):
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", interface):
            raise ValueError("Specify an explicit valid network interface name")
        if not isinstance(domain_id, int) or isinstance(domain_id, bool) or domain_id < 0:
            raise ValueError("domain_id must be a non-negative integer")
        if topic != "auto" and topic not in _STATE_TOPICS:
            raise ValueError(f"topic must be auto or one of {_STATE_TOPICS}")
        self.interface, self.domain_id, self.topic = interface, domain_id, topic
        self._topics = _STATE_TOPICS if topic == "auto" else (topic,)
        self._lock = threading.Lock()
        self._subscribers: list[Any] = []
        self._accepting = False
        self._latest: RobotState | None = None
        self._active_topic: str | None = None
        self._counts = {name: {"received": 0, "valid": 0} for name in self._topics}

    def open(self) -> None:
        global _dds_configuration
        if self._subscribers:
            return
        channel = _vendor_module(
            "unitree_sdk2py.core.channel",
            "Install the official Unitree SDK2 Python package and its DDS runtime.",
        )
        message = _vendor_module(
            "unitree_sdk2py.idl.unitree_go.msg.dds_",
            "The SDK installation must provide SportModeState_.",
        )
        configuration = (self.domain_id, self.interface)
        with _dds_lock:
            if _dds_configuration is not None and _dds_configuration != configuration:
                raise RuntimeError("Unitree DDS is already configured differently; start a new process")
            if _dds_configuration is None:
                channel.ChannelFactoryInitialize(self.domain_id, self.interface)
                _dds_configuration = configuration
        self._accepting = True
        try:
            for topic in self._topics:
                subscriber = channel.ChannelSubscriber(topic, message.SportModeState_)
                self._subscribers.append(subscriber)
                subscriber.Init(lambda msg, name=topic: self._receive(name, msg), 10)
        except Exception:
            self.close()
            raise

    def _receive(self, topic: str, message: Any) -> None:
        received_at = time.monotonic()
        with self._lock:
            if not self._accepting:
                return
            self._counts[topic]["received"] += 1
            try:
                values = [
                    float(message.position[0]), float(message.position[1]),
                    float(message.imu_state.rpy[2]), float(message.velocity[0]),
                    float(message.velocity[1]), float(message.yaw_speed),
                ]
                if not all(math.isfinite(value) for value in values):
                    return
            except (AttributeError, IndexError, TypeError, ValueError, OverflowError):
                return
            source_timestamp = None
            try:
                sec, nanosec = message.stamp.sec, message.stamp.nanosec
                if isinstance(sec, int) and isinstance(nanosec, int):
                    if sec >= 0 and 0 <= nanosec < 1_000_000_000 and (sec or nanosec):
                        source_timestamp = sec + nanosec / 1_000_000_000
            except AttributeError:
                pass
            self._latest = RobotState(
                received_at=received_at,
                x=values[0], y=values[1], yaw=values[2],
                vx=values[3], vy=values[4], yaw_rate=values[5],
                source_timestamp=source_timestamp,
                source_clock="unitree_stamp_unverified" if source_timestamp is not None else None,
                frame_id="unknown", velocity_frame="unknown",
            )
            self._counts[topic]["valid"] += 1
            self._active_topic = topic

    def latest(self) -> RobotState | None:
        """Return the latest finite sample; callers must check its receipt age."""
        with self._lock:
            return self._latest

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "received": sum(count["received"] for count in self._counts.values()),
                "valid": sum(count["valid"] for count in self._counts.values()),
                "active_topic": self._active_topic,
                "topics": {topic: dict(count) for topic, count in self._counts.items()},
            }

    def close(self) -> None:
        with self._lock:
            self._accepting = False
        subscribers, self._subscribers = self._subscribers, []
        failures = []
        for subscriber in reversed(subscribers):
            try:
                subscriber.Close()
            except Exception as exc:
                failures.append(str(exc))
        if failures:
            raise RuntimeError(f"Unitree subscriber cleanup failed: {'; '.join(failures)}")
