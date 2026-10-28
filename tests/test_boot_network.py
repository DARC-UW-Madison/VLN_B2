"""Credential handling and configuration boundaries; no real network changes."""

import copy
import importlib.util
import io
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    "configure_unattended_wifi", Path(__file__).resolve().parents[1] / "tools/configure_unattended_wifi.py"
)
boot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(boot)

DBUS = SimpleNamespace(
    Array=lambda value, signature: list(value), Boolean=bool, Int32=int, UInt32=int, String=str
)


def profile():
    return {
        "connection": {"permissions": ["user:example-user:"], "autoconnect": False},
        "802-11-wireless-security": {"key-mgmt": "wpa-eap"},
        "802-1x": {
            "identity": "example-user", "eap": ["peap"], "password-flags": 1,
            "ca-cert": "/example/ca.pem", "domain-suffix-match": "example.invalid",
            "phase2-auth": "mschapv2",
        },
        "ipv4": {"method": "auto"},
    }


class BootNetworkTests(unittest.TestCase):
    def test_password_mismatch_never_saves_or_echoes_credentials(self):
        proxy = mock.Mock()
        output = io.StringIO()
        with mock.patch.object(boot, "active_connection", return_value=(DBUS, proxy, profile())), \
             mock.patch.object(boot.os, "geteuid", return_value=0), \
             mock.patch.object(boot.sys.stdin, "isatty", return_value=True), \
             mock.patch.object(boot.getpass, "getpass", side_effect=["one-value", "other-value"]), \
             mock.patch.object(boot, "backup_wifi") as backup, \
             mock.patch("sys.stdout", output), mock.patch("sys.stderr", output):
            self.assertEqual(boot.main(["--apply"]), 2)
        proxy.Update.assert_not_called()
        backup.assert_not_called()
        self.assertNotIn("one-value", output.getvalue())
        self.assertNotIn("other-value", output.getvalue())

    def test_omitted_autoconnect_uses_networkmanager_default(self):
        settings = profile()
        settings["connection"].pop("autoconnect")
        self.assertTrue(boot.summary(settings)["autoconnect"])

    def test_boot_settings_preserve_identity_trust_and_ip(self):
        settings = profile()
        original = copy.deepcopy(settings)
        boot.configure_settings(settings, "example", DBUS)
        self.assertTrue(settings["connection"]["autoconnect"])
        self.assertEqual(settings["connection"]["permissions"], [])
        self.assertEqual(settings["connection"]["autoconnect-retries"], 0)
        self.assertEqual(settings["802-1x"]["password-flags"], 0)
        for key in ("identity", "ca-cert", "domain-suffix-match", "eap", "phase2-auth"):
            self.assertEqual(settings["802-1x"][key], original["802-1x"][key])
        self.assertEqual(settings["ipv4"], original["ipv4"])

    def test_empty_password_leaves_settings_unchanged(self):
        settings = profile()
        original = copy.deepcopy(settings)
        with self.assertRaises(ValueError):
            boot.configure_settings(settings, "", DBUS)
        self.assertEqual(settings, original)

    def test_certificate_only_profile_is_not_converted(self):
        settings = profile()
        settings["802-1x"]["eap"] = ["tls"]
        original = copy.deepcopy(settings)
        with self.assertRaises(ValueError):
            boot.configure_settings(settings, "example", DBUS)
        self.assertEqual(settings, original)

    def test_inspection_excludes_identity_password_and_certificate_path(self):
        settings = profile()
        settings["802-1x"]["password"] = "fixture-value"
        report = json.dumps(boot.summary(settings))
        for private in ("example-user", "fixture-value", "/example/ca.pem"):
            self.assertNotIn(private, report)

    def test_autologin_preserves_comments_and_other_sections(self):
        old = "# Keep this comment\n[daemon]\nAutomaticLogin=previous\nOtherFlag=True\n[security]\nDisallowTCP=True\n"
        result = boot.autologin_text(old, "research")
        self.assertIn("# Keep this comment", result)
        self.assertIn("OtherFlag=True", result)
        self.assertIn("[security]\nDisallowTCP=True", result)
        self.assertIn("AutomaticLoginEnable=True", result)
        self.assertIn("AutomaticLogin=research", result)
        self.assertNotIn("AutomaticLogin=previous", result)

    def test_autologin_rejects_config_injection(self):
        with self.assertRaises(ValueError):
            boot.autologin_text("[daemon]\n", "research\n[security]")


if __name__ == "__main__":
    unittest.main()
