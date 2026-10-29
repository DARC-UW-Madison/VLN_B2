"""Offline SDK imports and synthetic state serialization; never robot I/O.

Run in the dedicated SDK image with Docker --network none. Network isolation is
an external precondition: this verifier cannot prove the container's network
mode. It never constructs a DDS domain, participant, factory or robot client.
No library-loading bypass variable is allowed. No Hugging Face assets are used.
The SDK is imported from pinned source for its state path only. Its full pip
distribution is not installed and its declared dependencies are not satisfied.
"""

import argparse
import ast
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, distribution, version
from importlib.util import find_spec
import json
import os
from pathlib import Path
import platform
import sys
import time
import traceback


SDK_REVISION = "814556d15970dd2ecf1c9984e845ca02ab07e206"
SDK_REPOSITORY = "https://github.com/unitreerobotics/unitree_sdk2_python"
SDK_SOURCE = Path("/opt/vendor/unitree_sdk2_python")
SDK_METADATA = Path("/opt/runtime-metadata/unitree")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sdk_source(report):
    """Check build-recorded source provenance without executing setup.py."""
    try:
        distribution("unitree_sdk2py")
    except PackageNotFoundError:
        report["sdk_distribution_installed"] = False
    else:
        report["sdk_distribution_installed"] = True
        raise RuntimeError("Remove the installed SDK distribution; source/distribution mixing is refused")
    source = SDK_SOURCE.resolve(strict=True)
    if os.environ.get("PYTHONPATH") != str(source):
        raise ValueError("PYTHONPATH must select only the pinned SDK source directory")
    manifest_path = SDK_METADATA / "unitree-sdk2-source.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("repository") != SDK_REPOSITORY or manifest.get("revision") != SDK_REVISION:
        raise RuntimeError("SDK source manifest does not identify the reviewed repository/revision")
    if (source / ".git/HEAD").read_text().strip() != SDK_REVISION:
        raise RuntimeError("SDK source is not detached at the reviewed revision")
    if (SDK_METADATA / "unitree-sdk2-revision.txt").read_text().strip() != SDK_REVISION:
        raise RuntimeError("SDK source revision record differs from the reviewed revision")
    if manifest.get("sdk_import_mode") != "pinned source; state path only":
        raise RuntimeError("SDK source manifest has an unexpected import mode")
    if manifest.get("declared_full_sdk_dependencies_satisfied") is not False:
        raise RuntimeError("SDK source manifest must not claim full distribution dependency coverage")
    setup_path = source / "setup.py"
    if sha256(setup_path) != manifest.get("setup_py_sha256"):
        raise RuntimeError("SDK original setup.py differs from the pinned build manifest")
    if sha256(SDK_METADATA / "unitree-sdk2-setup.py") != manifest["setup_py_sha256"]:
        raise RuntimeError("SDK archived original setup.py differs from its source")
    if sha256(source / "LICENSE") != manifest.get("license_sha256"):
        raise RuntimeError("SDK original license differs from the pinned build manifest")
    if sha256(SDK_METADATA / "licenses/unitree-sdk2-LICENSE") != manifest["license_sha256"]:
        raise RuntimeError("SDK archived original license differs from its source")
    syntax = ast.parse(setup_path.read_text(), filename="upstream/setup.py")
    calls = [node for node in ast.walk(syntax) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == "setup"]
    if len(calls) != 1:
        raise RuntimeError("Expected exactly one upstream setup() declaration")
    fields = {item.arg: ast.literal_eval(item.value) for item in calls[0].keywords
              if item.arg in {"name", "version", "install_requires"}}
    if fields.get("name") != "unitree_sdk2py" or fields.get("version") != "1.0.1":
        raise RuntimeError("SDK original setup.py has an unexpected package name/version")
    if manifest.get("version") != fields["version"]:
        raise RuntimeError("SDK source manifest version differs from its original declaration")
    if fields.get("install_requires") != ["cyclonedds==0.10.2", "numpy", "opencv-python"]:
        raise RuntimeError("SDK original full dependency declarations were changed")
    files = sorted([setup_path, *(source / "unitree_sdk2py").rglob("*.py")])
    actual_hashes = {str(path.relative_to(source)): sha256(path) for path in files}
    if actual_hashes != manifest.get("python_source_sha256"):
        raise RuntimeError("SDK Python source file set/hashes differ from the pinned build manifest")
    spec = find_spec("unitree_sdk2py")
    if spec is None or spec.origin is None:
        raise RuntimeError("Pinned SDK source package cannot be resolved")
    if Path(spec.origin).resolve(strict=True) != source / "unitree_sdk2py/__init__.py":
        raise RuntimeError("SDK import would resolve outside the pinned source package")
    report["sdk_source"] = {"repository": SDK_REPOSITORY, "revision": SDK_REVISION,
                            "version": fields["version"], "path": str(source),
                            "setup_py_sha256": manifest["setup_py_sha256"],
                            "manifest_sha256": sha256(manifest_path),
                            "python_source_files_verified": len(actual_hashes),
                            "declared_full_sdk_dependencies": fields["install_requires"],
                            "origin_verified": True, "setup_executed": False}
    return source


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
    report["versions"] = {"cyclonedds": version("cyclonedds")}
    if report["versions"] != {"cyclonedds": "0.10.2"}:
        raise RuntimeError("Installed CycloneDDS version differs from the reviewed pin")
    report["stage"] = "sdk_source_provenance"
    source = verify_sdk_source(report)
    report["versions"]["unitree_sdk2py_source"] = report["sdk_source"]["version"]

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

    for name, module in list(sys.modules.items()):
        if name == "unitree_sdk2py" or name.startswith("unitree_sdk2py."):
            origin = getattr(module, "__file__", None)
            if origin is not None and not Path(origin).resolve(strict=True).is_relative_to(source):
                raise RuntimeError("Imported SDK module origin is outside the pinned source directory")
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
                  "sdk_import_mode": "pinned source; state path only",
                  "declared_full_sdk_dependencies_satisfied": False,
                  "sdk_distribution_installed": None,
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
