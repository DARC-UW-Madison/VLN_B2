#!/usr/bin/env python3
"""Read-only target inventory; Python 3.8+, standard library only.

Schema 1: each probe has a status (available, not_installed, unknown, error,
timeout, or not_checked), optional data, and a next_step. Inventory never proves
sensor operation, model inference, or robot control. No network requests, sudo,
installations, sensor streaming, or robot commands are performed. Network interface
addresses are included only with --include-network. Review even default reports
before sharing; hardware/software inventory can still be laboratory information.
"""

import argparse
import datetime
import importlib.metadata
import ipaddress
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path


SCHEMA_VERSION = 1
COMMAND_TIMEOUT_SECONDS = 3
PACKAGES = (
    "torch", "torchvision", "transformers", "numpy", "opencv-python",
    "pyzed", "unitree-sdk2py", "cyclonedds", "rclpy",
)


def _probe(status, data=None, next_step=None):
    result = {"status": status}
    if data is not None:
        result["data"] = data
    if next_step:
        result["next_step"] = next_step
    return result


def _read_text(path):
    """Read a bounded known file; never inspect serial-number files."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read(16384).replace("\x00", "").strip()
    except (OSError, ValueError):
        return None


def _run_command(arguments):
    """Suppress command diagnostics, which may contain local paths or users."""
    if shutil.which(arguments[0]) is None:
        return _probe("not_installed", next_step="Install only if this tool is needed.")
    command_environment = {**os.environ, "LC_ALL": "C", "GIT_OPTIONAL_LOCKS": "0"}
    if arguments[0] == "docker":
        # Never follow a user's remote Docker context or SSH/TCP endpoint.
        for name in ("DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH"):
            command_environment.pop(name, None)
    try:
        process = subprocess.run(
            arguments, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, universal_newlines=True,
            timeout=COMMAND_TIMEOUT_SECONDS, check=False,
            env=command_environment,
        )
    except subprocess.TimeoutExpired:
        return _probe("timeout", next_step="Check the tool locally; no response within 3 seconds.")
    except OSError:
        return _probe("error", next_step="Check local execution permissions and tool installation.")
    if process.returncode:
        return _probe("error", {"exit_code": process.returncode},
                      "Run the documented read-only command locally to inspect its error.")
    if len(process.stdout) > 65536:
        return _probe("error", next_step="Command output exceeded the inventory limit.")
    return _probe("available", process.stdout.strip())


def _os_info():
    values = {}
    content = _read_text("/etc/os-release")
    if content:
        for line in content.splitlines():
            key, separator, value = line.partition("=")
            if separator and key in ("ID", "VERSION_ID", "PRETTY_NAME"):
                values[key.lower()] = value.strip("\"'")[:160]
    return _probe("available", {
        "system": platform.system(), "architecture": platform.machine(),
        "kernel": platform.release(), "distribution": values,
    })


def _memory():
    content = _read_text("/proc/meminfo")
    if content is None:
        return _probe("unknown", next_step="Read installed RAM in the system information UI.")
    values = {}
    for field in ("MemTotal", "MemAvailable"):
        match = re.search(r"^" + field + r":\s+(\d+) kB$", content, re.MULTILINE)
        if match:
            values[field] = int(match.group(1)) * 1024
    return _probe("available", values) if values else _probe("unknown")


def _disk():
    try:
        usage = shutil.disk_usage("/")
        return _probe("available", {"total_bytes": usage.total, "free_bytes": usage.free},
                      "These figures cover the root filesystem only; check the intended model storage separately.")
    except OSError:
        return _probe("error", next_step="Check root filesystem capacity locally.")


def _packages():
    values = {}
    for name in PACKAGES:
        try:
            version = importlib.metadata.version(name)
            values[name] = _probe("available", {"version": version[:120]})
        except importlib.metadata.PackageNotFoundError:
            values[name] = _probe("unknown", next_step="No distribution metadata in this Python environment; other environments or source installs may exist.")
        except Exception:
            values[name] = _probe("error", next_step="Inspect this package's metadata locally.")
    return values


def _system_packages():
    """Query selected Debian package metadata, never drivers or model runtimes."""
    patterns = {
        "l4t_core": "nvidia-l4t-core",
        "jetpack_meta": "nvidia-jetpack",
        "cuda_runtime": "cuda-cudart-*",
        "tensorrt": "libnvinfer*",
        "nvidia_container_toolkit": "nvidia-container-toolkit",
        "docker_debian": "docker.io",
    }
    packages = {}
    for label, pattern in patterns.items():
        result = _run_command([
            "dpkg-query", "-W", "-f=${binary:Package}\t${Version}\t${db:Status-Abbrev}\n",
            pattern,
        ])
        if result["status"] == "available":
            selected = []
            for line in result["data"].splitlines():
                fields = line.split("\t")
                if len(fields) != 3 or fields[2].strip() != "ii":
                    continue
                name, version = fields[:2]
                if (re.fullmatch(r"[a-z0-9.+:-]{1,120}", name)
                        and re.fullmatch(r"[A-Za-z0-9.+:~_-]{1,120}", version)):
                    selected.append({"package": name, "version": version})
            result = _probe("available", selected) if selected else _probe(
                "unknown", next_step="No installed package records recognized; inspect locally.")
        elif result["status"] == "error":
            result = _probe("unknown", next_step=(
                "No matching package metadata obtained. A missing meta-package does not "
                "prove the underlying runtime is absent; check the existing installation."))
        packages[label] = result
    return packages


def _environment():
    values = {}
    safe_values = {
        "ROS_DISTRO": r"[a-z][a-z0-9_]{0,31}",
        "RMW_IMPLEMENTATION": r"rmw_[a-z0-9_]{1,64}",
        "ROS_DOMAIN_ID": r"\d{1,3}",
        "ROS_LOCALHOST_ONLY": r"[01]",
    }
    for name in tuple(safe_values) + ("CYCLONEDDS_URI", "FASTRTPS_DEFAULT_PROFILES_FILE", "ROS_DISCOVERY_SERVER"):
        value = os.environ.get(name)
        values[name] = {"present": value is not None}
        if value is not None and name in safe_values and re.fullmatch(safe_values[name], value):
            values[name]["value"] = value
    return values


def _docker():
    # Explicit fields avoid endpoints, usernames, labels, and daemon configuration.
    version = _run_command(["docker", "--version"])
    if version["status"] == "available":
        match = re.fullmatch(r"Docker version ([A-Za-z0-9.+:~_-]+), build [A-Za-z0-9.+:~_-]+", version["data"])
        version = _probe("available", {"version": match.group(1)}) if match else _probe("unknown", next_step="Check Docker version locally; output format was not recognized.")
    runtime = _run_command([
        "docker", "--host", "unix:///var/run/docker.sock", "info", "--format",
        '{"server_version":{{json .ServerVersion}},"default_runtime":{{json .DefaultRuntime}},"runtimes":{{json .Runtimes}}}',
    ])
    if runtime["status"] == "available":
        try:
            data = json.loads(runtime["data"])
            server, default, runtimes = data["server_version"], data["default_runtime"], data["runtimes"]
            if not isinstance(server, str) or not server or not isinstance(default, str) or not default or not isinstance(runtimes, dict):
                raise ValueError("Unexpected Docker data")
            names = sorted(name for name in runtimes if re.fullmatch(r"[a-zA-Z0-9_.-]{1,64}", name))
            runtime = _probe("available", {"server_version": server[:80], "default_runtime": default[:80], "runtime_names": names},
                             "A listed NVIDIA runtime does not verify GPU access inside a container.")
        except (ValueError, TypeError, KeyError):
            runtime = _probe("unknown", next_step="Check Docker daemon and runtime information locally.")
    elif runtime["status"] == "error":
        runtime["next_step"] = "The local /var/run/docker.sock daemon may be stopped or inaccessible; rootless or custom local sockets are not inspected. Check locally without changing permissions automatically."
    socket = Path("/var/run/docker.sock")
    if socket.is_socket():
        writable = os.access(str(socket), os.W_OK)
        if not writable and runtime["status"] != "available":
            runtime = _probe("error", {"reason": "local_socket_not_writable"},
                             "The current user cannot access the standard Docker socket. Review approved administrator access; this tool changes no groups or permissions.")
    return {"client": version, "daemon": runtime}


def _usb():
    result = _run_command(["lsusb"])
    if result["status"] != "available":
        return result
    ids = [value.lower() for value in re.findall(r"\bID ([0-9a-fA-F]{4}:[0-9a-fA-F]{4})\b", result["data"])]
    counts = {device_id: ids.count(device_id) for device_id in sorted(set(ids))}
    return _probe("available", {"vendor_product_counts": counts},
                  "USB enumeration does not verify a camera driver or RGB stream; Ethernet LiDAR will not appear here.")


def _sdk(path):
    if path is None:
        return _probe("not_checked", next_step="Pass --sdk-path to an existing SDK checkout if available.")
    if not Path(path).is_dir():
        return _probe("unknown", next_step="The supplied SDK directory does not exist; locate the working checkout.")
    revision = _run_command(["git", "-C", str(path), "rev-parse", "HEAD"])
    if revision["status"] != "available":
        return revision
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision["data"]):
        return _probe("unknown", next_step="The supplied directory did not yield a recognized Git revision.")
    state = _run_command(["git", "-C", str(path), "status", "--porcelain", "--untracked-files=normal"])
    data = {"revision": revision["data"], "dirty_status": state["status"]}
    if state["status"] == "available":
        data["dirty"] = bool(state["data"])
    return _probe("available", data, "Revision and dirty state do not identify applied patches or verify robot communication.")


def _network():
    result = _run_command(["ip", "-j", "address", "show"])
    if result["status"] != "available":
        return result
    try:
        interfaces = []
        for entry in json.loads(result["data"]):
            name = entry.get("ifname", "")
            if not re.fullmatch(r"[a-zA-Z0-9_.:@-]{1,64}", name):
                continue
            item = {"interface": name, "addresses": [], "cidrs": []}
            mac = entry.get("address", "")
            if re.fullmatch(r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", mac):
                item["mac"] = mac
            for address in entry.get("addr_info", []):
                try:
                    parsed = ipaddress.ip_address(address.get("local", ""))
                    item["addresses"].append(str(parsed))
                    prefix = address.get("prefixlen")
                    if type(prefix) is int:
                        item["cidrs"].append(str(ipaddress.ip_interface("{}/{}".format(parsed, prefix))))
                except (ValueError, TypeError):
                    continue
            interfaces.append(item)
        return _probe("available", interfaces, "This optional section contains local addresses; keep it private and review before sharing.")
    except (ValueError, TypeError, AttributeError):
        return _probe("unknown", next_step="Inspect network interfaces locally; command output was not recognized.")


def _network_records(arguments, fields):
    """Keep selected local topology fields, not aliases or complete configuration."""
    result = _run_command(arguments)
    if result["status"] != "available":
        return result
    try:
        records = json.loads(result["data"])
        if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
            raise ValueError("Expected records")
        selected = []
        for record in records:
            item = {}
            for key in fields:
                value = record.get(key)
                if isinstance(value, str) and len(value) <= 160 and value.isprintable():
                    item[key] = value
                elif type(value) is int:
                    item[key] = value
                elif isinstance(value, list) and all(
                    isinstance(part, str) and len(part) <= 64 and part.isprintable()
                    for part in value
                ):
                    item[key] = value
            if item:
                selected.append(item)
        return _probe("available", selected)
    except (ValueError, TypeError, AttributeError):
        return _probe("unknown", next_step="Inspect topology locally; JSON output was not recognized.")


def _network_details():
    """Read local links, IPv4 routes and caches; never scan or contact peers."""
    flags = {}
    for name, path in (
        ("ipv4_forwarding", "/proc/sys/net/ipv4/ip_forward"),
        ("bridge_ipv4_filtering", "/proc/sys/net/bridge/bridge-nf-call-iptables"),
    ):
        value = _read_text(path)
        flags[name] = _probe("available", int(value)) if value in ("0", "1") else _probe(
            "unknown", next_step="This kernel flag is unavailable; no setting was changed.")
    return {
        "links": _network_records(["ip", "-j", "link", "show"], (
            "ifindex", "ifname", "mtu", "flags", "operstate", "master", "link_index", "link_netnsid",
        )),
        "ipv4_routes": _network_records(["ip", "-j", "-4", "route", "show", "table", "all"], (
            "dst", "gateway", "prefsrc", "dev", "metric", "table", "type", "scope", "protocol",
        )),
        "bridge_ports": _network_records(["bridge", "-j", "link", "show"], (
            "ifindex", "ifname", "master", "state", "flags", "cost", "priority",
        )),
        "cached_neighbors": _network_records(["ip", "-j", "neigh", "show"], (
            "dst", "dev", "lladdr", "state",
        )),
        "kernel_flags": flags,
        "limitations": (
            "Local network namespace only. No probes, packet capture, firewall-rule dump, "
            "or peer identification. Cached neighbors can be stale; addresses do not identify computers. "
            "An empty bridge list is not proof of direct controller access."
        ),
    }


def collect_report(sdk_path=None, include_network=False):
    """Collect schema-versioned inventory without importing optional packages."""
    model = _read_text("/proc/device-tree/model") or _read_text("/sys/firmware/devicetree/base/model")
    l4t = _read_text("/etc/nv_tegra_release")
    report = {
        "schema_version": SCHEMA_VERSION,
        "collected_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Read-only inventory; no sensor stream, inference, or robot-control test.",
        "privacy": {"network_included": bool(include_network), "serial_numbers_collected": False},
        "os": _os_info(),
        "jetson_model": _probe("available", model[:200]) if model else _probe("unknown", next_step="No Jetson model file found; confirm the compute module physically."),
        "l4t_release": _probe("available", l4t.splitlines()[0][:300]) if l4t else _probe("unknown", next_step="Confirm installed Jetson Linux/JetPack locally before selecting a container."),
        "memory": _memory(), "root_disk": _disk(),
        "python_interpreter": {"version": platform.python_version(), "implementation": platform.python_implementation()},
        "python_packages": _packages(), "system_packages": _system_packages(),
        "selected_environment": _environment(), "docker": _docker(),
        "usb": _usb(), "sdk_checkout": _sdk(sdk_path),
        "operational_checks": {name: _probe("not_checked") for name in (
            "zed_rgb_stream", "camera_timestamps", "mid360_data", "b2_state", "b2_stop_procedure", "gpu_container", "ticvla_inference",
        )},
    }
    if include_network:
        report["network"] = _network()
        report["network_details"] = _network_details()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write JSON to this file; otherwise print to stdout.")
    parser.add_argument("--sdk-path", type=Path, help="Inspect revision and dirty state of an existing SDK checkout.")
    parser.add_argument("--include-network", action="store_true", help="Include private addresses, prefixes, routes and local topology; disabled by default.")
    args = parser.parse_args(argv)
    payload = json.dumps(collect_report(args.sdk_path, args.include_network), indent=2, sort_keys=True) + "\n"
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(payload)
        except OSError:
            parser.error("Cannot create output file. Choose a new filename in a writable location.")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
