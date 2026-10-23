"""Read-only inventory checks; no hardware, optional packages, or network needed."""

import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SPEC = importlib.util.spec_from_file_location(
    "inspect_target", Path(__file__).resolve().parents[1] / "tools" / "inspect_target.py"
)
target = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(target)


class TargetInspectionTests(unittest.TestCase):
    def test_missing_tool_is_not_a_hardware_failure(self):
        with mock.patch.object(target.shutil, "which", return_value=None), mock.patch.object(target.subprocess, "run") as run:
            result = target._run_command(["docker", "--version"])
        self.assertEqual(result["status"], "not_installed")
        run.assert_not_called()

    def test_timeout_is_bounded_and_diagnostics_are_not_returned(self):
        with mock.patch.object(target.shutil, "which", return_value="/usr/bin/docker"), mock.patch.object(
            target.subprocess, "run", side_effect=subprocess.TimeoutExpired("private-user@private-host", 3, output="secret")
        ) as run:
            result = target._run_command(["docker", "info"])
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(run.call_args.kwargs["timeout"], 3)
        self.assertEqual(run.call_args.kwargs["stderr"], subprocess.DEVNULL)
        self.assertNotIn("secret", json.dumps(result))

    def test_command_failure_exposes_only_exit_code(self):
        process = subprocess.CompletedProcess(["docker"], 1, stdout="token=secret", stderr="private-user@private-host")
        with mock.patch.object(target.shutil, "which", return_value="/usr/bin/docker"), mock.patch.object(target.subprocess, "run", return_value=process):
            result = target._run_command(["docker", "info"])
        self.assertEqual(result["data"], {"exit_code": 1})
        self.assertNotIn("private", json.dumps(result))
        self.assertNotIn("secret", json.dumps(result))

    def test_docker_does_not_follow_remote_context_environment(self):
        process = subprocess.CompletedProcess(["docker"], 0, stdout="Docker version 27.5.1, build 1234567")
        with mock.patch.dict(os.environ, {"DOCKER_HOST": "tcp://192.0.2.9:2375", "DOCKER_CONTEXT": "remote-lab"}), mock.patch.object(
            target.shutil, "which", return_value="/usr/bin/docker"
        ), mock.patch.object(target.subprocess, "run", return_value=process) as run:
            target._run_command(["docker", "--version"])
        self.assertNotIn("DOCKER_HOST", run.call_args.kwargs["env"])
        self.assertNotIn("DOCKER_CONTEXT", run.call_args.kwargs["env"])

    def test_environment_values_are_allowlisted(self):
        environment = {
            "ROS_DISTRO": "humble", "ROS_DOMAIN_ID": "42",
            "RMW_IMPLEMENTATION": "rmw_cyclonedds_cpp",
            "CYCLONEDDS_URI": "<NetworkInterfaceAddress>192.0.2.9</NetworkInterfaceAddress>",
            "ROS_DISCOVERY_SERVER": "private-host:11811",
            "FASTRTPS_DEFAULT_PROFILES_FILE": "/home/private-user/secret.xml",
            "PASSWORD": "secret", "HOSTNAME": "private-host", "USER": "private-user",
        }
        with mock.patch.dict(os.environ, environment, clear=True):
            result = target._environment()
        self.assertEqual(result["ROS_DISTRO"]["value"], "humble")
        self.assertEqual(result["CYCLONEDDS_URI"], {"present": True})
        serialized = json.dumps(result)
        for private in ("192.0.2.9", "private-host", "private-user", "secret", "PASSWORD"):
            self.assertNotIn(private, serialized)

    def test_malformed_environment_value_is_presence_only(self):
        with mock.patch.dict(os.environ, {"ROS_DISTRO": "/home/private-user"}, clear=True):
            self.assertEqual(target._environment()["ROS_DISTRO"], {"present": True})

    def test_usb_retains_only_ids_and_counts(self):
        stdout = "Bus 001 Device 002: ID 2b03:f880 Camera private-serial\nBus 001 Device 003: ID 2b03:f880 Camera private-serial\n"
        with mock.patch.object(target, "_run_command", return_value=target._probe("available", stdout)):
            result = target._usb()
        self.assertEqual(result["data"]["vendor_product_counts"], {"2b03:f880": 2})
        self.assertNotIn("private-serial", json.dumps(result))

    def test_sdk_does_not_expose_path_or_dirty_names(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(target, "_run_command", side_effect=[
            target._probe("available", "a" * 40),
            target._probe("available", "?? secret-recording.mp4\n M private-config.txt"),
        ]):
            result = target._sdk(directory)
        self.assertTrue(result["data"]["dirty"])
        self.assertEqual(result["data"]["revision"], "a" * 40)
        self.assertNotIn(directory, json.dumps(result))
        self.assertNotIn("private-config", json.dumps(result))

    def test_inventory_shape_and_default_network_privacy(self):
        files = {
            "/proc/device-tree/model": "NVIDIA Jetson AGX Orin Developer Kit",
            "/etc/nv_tegra_release": "# R36 (release), REVISION: 4.3",
            "/etc/os-release": 'ID=ubuntu\nVERSION_ID="22.04"\nPRETTY_NAME="Ubuntu 22.04"\nSECRET=private-data',
            "/proc/meminfo": "MemTotal:       1024 kB\nMemAvailable:     512 kB\n",
        }
        with mock.patch.object(target, "_read_text", side_effect=lambda name: files.get(name)), mock.patch.object(
            target, "_run_command", return_value=target._probe("not_installed")
        ), mock.patch.object(target.importlib.metadata, "version", side_effect=target.importlib.metadata.PackageNotFoundError), mock.patch.dict(
            os.environ, {"USER": "private-user", "HOSTNAME": "private-host"}, clear=True
        ), mock.patch.object(target, "_network") as network, mock.patch.object(target.platform, "system", return_value="Linux"), mock.patch.object(
            target.platform, "machine", return_value="aarch64"
        ), mock.patch.object(target.platform, "release", return_value="5.15.148-tegra"):
            report = target.collect_report()
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["os"]["data"]["architecture"], "aarch64")
        self.assertEqual(report["memory"]["data"]["MemTotal"], 1024 * 1024)
        self.assertEqual(report["operational_checks"]["b2_state"]["status"], "not_checked")
        self.assertEqual(report["python_packages"]["torch"]["status"], "unknown")
        self.assertNotIn("network", report)
        network.assert_not_called()
        for private in ("private-user", "private-host", "private-data"):
            self.assertNotIn(private, json.dumps(report))
        self.assertRegex(report["collected_at_utc"], r"^\d{4}-\d{2}-\d{2}T.*\+00:00$")

    def test_network_is_explicit_and_removes_unselected_fields(self):
        stdout = json.dumps([{
            "ifname": "eth0", "address": "02:00:00:00:00:01", "hostname": "private-host",
            "addr_info": [{"local": "192.0.2.1"}, {"local": "not an address"}],
        }])
        with mock.patch.object(target, "_run_command", return_value=target._probe("available", stdout)):
            result = target._network()
        self.assertEqual(result["data"][0]["addresses"], ["192.0.2.1"])
        self.assertEqual(result["data"][0]["mac"], "02:00:00:00:00:01")
        self.assertNotIn("private-host", json.dumps(result))

    def test_docker_runtime_configuration_is_not_emitted(self):
        stdout = '"27.5.1"\n"runc"\n{"nvidia":{"path":"/home/private-user/runtime"},"runc":{}}'
        with mock.patch.object(target, "_run_command", side_effect=[
            target._probe("available", "Docker version 27.5.1, build 1234567"),
            target._probe("available", stdout),
        ]) as run:
            result = target._docker()
        self.assertEqual(result["daemon"]["data"]["runtime_names"], ["nvidia", "runc"])
        self.assertNotIn("private-user", json.dumps(result))
        self.assertIn("unix:///var/run/docker.sock", run.call_args_list[1].args[0])

    def test_system_packages_keep_installed_metadata_only(self):
        output = (
            "nvidia-l4t-core\t36.4.3-20250107174145\tii \n"
            "private/path\t1.0\tii \n"
            "removed-package\t1.0\trc \n"
        )
        with mock.patch.object(target, "_run_command", return_value=target._probe("available", output)) as run:
            result = target._system_packages()
        self.assertEqual(result["l4t_core"]["data"], [
            {"package": "nvidia-l4t-core", "version": "36.4.3-20250107174145"},
        ])
        self.assertEqual(run.call_args_list[0].args[0][0], "dpkg-query")
        self.assertNotIn("private", json.dumps(result))

    def test_missing_meta_packages_do_not_prove_missing_runtime(self):
        with mock.patch.object(target, "_run_command", return_value=target._probe("error", {"exit_code": 1})):
            result = target._system_packages()
        self.assertEqual(result["jetpack_meta"]["status"], "unknown")
        self.assertIn("does not prove", result["jetpack_meta"]["next_step"])

    def test_cli_creates_missing_output_parents(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new" / "local" / "inventory.json"
            with mock.patch.object(target, "collect_report", return_value={"schema_version": 1}):
                self.assertEqual(target.main(["--output", str(output)]), 0)
            self.assertEqual(json.loads(output.read_text()), {"schema_version": 1})

    def test_cli_output_refuses_to_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "inventory.json"
            output.write_text("existing data", encoding="utf-8")
            with mock.patch.object(target, "collect_report", return_value={"schema_version": 1}), mock.patch("sys.stderr", new_callable=io.StringIO), self.assertRaises(SystemExit):
                target.main(["--output", str(output)])
            self.assertEqual(output.read_text(encoding="utf-8"), "existing data")


if __name__ == "__main__":
    unittest.main()
