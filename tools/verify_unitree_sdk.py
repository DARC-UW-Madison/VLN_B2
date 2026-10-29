"""Offline SDK imports and synthetic state serialization; never robot I/O.

Run in the dedicated SDK image with Docker --network none. Network isolation is
an external precondition: this verifier cannot prove the container's network
mode. It never constructs a DDS domain, participant, factory or robot client.
No library-loading bypass variable is allowed. No Hugging Face assets are used.
"""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import sys
import time
import traceback


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(report):
    report["stage"] = "environment"
    if "CYCLONEDDS_PYTHON_NO_IMPORT_LIBS" in os.environ:
        raise ValueError("Unset CYCLONEDDS_PYTHON_NO_IMPORT_LIBS; native loading is required")
    if sys.version_info[:2] != (3, 11) or platform.system() != "Linux":
        raise RuntimeError("Use the dedicated Linux Python 3.11 SDK image")
    if platform.machine() != "aarch64" or Path(sys.prefix) != Path("/opt/unitree"):
        raise RuntimeError("Use the dedicated /opt/unitree aarch64 virtual environment")
    prefix = Path("/opt/cyclonedds").resolve(strict=True)
    if os.environ.get("CYCLONEDDS_HOME") != str(prefix):
        raise ValueError("CYCLONEDDS_HOME must select /opt/cyclonedds")
    if any(name.split(".")[0] in {"cyclonedds", "unitree_sdk2py"} for name in sys.modules):
        raise RuntimeError("Start a fresh verifier process without preloaded DDS/SDK modules")
    report["versions"] = {name: version(name) for name in
                          ("cyclonedds", "unitree_sdk2py", "numpy", "opencv-python")}
    expected = {"cyclonedds": "0.10.2", "unitree_sdk2py": "1.0.1",
                "numpy": "1.26.4", "opencv-python": "4.10.0.84"}
    if report["versions"] != expected:
        raise RuntimeError("Installed SDK runtime versions differ from the reviewed pins")

    report["stage"] = "native_import"
    from cyclonedds.internal import DDS

    expected_library = (prefix / "lib/libddsc.so").resolve(strict=True)
    actual_library = Path(os.fsdecode(DDS._dll_handle._name)).resolve(strict=True)
    if actual_library != expected_library:
        raise RuntimeError("CycloneDDS loaded a native library outside the dedicated prefix")
    mapped_libraries = set()
    for line in Path("/proc/self/maps").read_text().splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) == 6 and Path(fields[5]).name.startswith("libddsc.so"):
            mapped_libraries.add(Path(fields[5]).resolve(strict=True))
    if mapped_libraries != {expected_library}:
        raise RuntimeError("Unexpected or missing CycloneDDS native library mappings")
    report["native_library"] = {"path": str(actual_library),
                                "sha256": sha256(actual_library),
                                "dedicated_prefix_verified": True,
                                "process_mappings_verified": True}

    report["stage"] = "sdk_import"
    # Importing these definitions does not initialize ChannelFactory or DDS entities.
    from unitree_sdk2py.core.channel import ChannelSubscriber
    from unitree_sdk2py.idl.default import unitree_go_msg_dds__SportModeState_
    from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_

    if not callable(ChannelSubscriber):
        raise RuntimeError("SDK ChannelSubscriber definition is unavailable")
    report["stage"] = "state_serialization"
    sample = unitree_go_msg_dds__SportModeState_()
    sample.position = [1.25, -2.5, 0.5]
    sample.velocity = [0.25, -0.5, 0.0]
    sample.yaw_speed = 0.125
    sample.imu_state.rpy = [0.0, 0.0, 0.75]
    sample.stamp.sec, sample.stamp.nanosec = 12, 500_000_000
    if not isinstance(sample, SportModeState_):
        raise RuntimeError("SDK state factory returned an unexpected type")
    encoded = sample.serialize()
    restored = SportModeState_.deserialize(encoded)
    if asdict(sample) != asdict(restored):
        raise RuntimeError("Synthetic SportModeState_ serialization roundtrip differs")
    if len(restored.position) != 3 or len(restored.velocity) != 3:
        raise RuntimeError("Unexpected SportModeState_ vector layout")
    if len(restored.imu_state.rpy) != 3:
        raise RuntimeError("Unexpected IMUState_ orientation layout")
    report.update(serialization_verified=True, serialized_bytes=len(encoded),
                  state_type="unitree_go.msg.dds_.SportModeState_",
                  synthetic_state_only=True, passed=True, stage="complete")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True,
                        help="New private JSON report on an existing writable mount; never overwritten")
    args = parser.parse_args(argv)
    # O_EXCL rejects existing files and symlinks; creation permissions are private
    # from the outset, regardless of the caller's umask. No directory is created.
    descriptor = os.open(args.report, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        report = {"passed": False, "stage": "starting",
                  "started_at_utc": datetime.now(timezone.utc).isoformat(),
                  "python_version": platform.python_version(),
                  "network_isolation_required": True,
                  "network_isolation_verified_by_tool": False,
                  "network_isolation_precondition": "Run this process with Docker --network none",
                  "dds_entities_created_by_verifier": False,
                  "robot_client_created": False, "robot_connected": False,
                  "motion_sent": False, "external_model_assets_used": False,
                  "serialization_verified": False}
        started = time.monotonic()
        try:
            verify(report)
        except Exception as error:
            report.update(error_type=type(error).__name__, error=str(error))
            traceback.print_exc()
        report["wall_seconds"] = time.monotonic() - started
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({name: report[name] for name in
                      ("passed", "stage", "serialization_verified", "robot_connected",
                       "motion_sent", "network_isolation_verified_by_tool")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
