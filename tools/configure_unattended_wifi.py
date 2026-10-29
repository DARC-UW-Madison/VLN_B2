"""Inspect or configure an existing enterprise Wi-Fi profile without disconnecting.

Run with the host's system Python and python3-dbus. Password entry is local to
an interactive terminal; never pass passwords as arguments or environment values.
"""

import argparse
import configparser
import getpass
import json
import os
import pwd
import re
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

SERVICE = "org.freedesktop.NetworkManager"
GDM_CONFIG = Path("/etc/gdm3/custom.conf")
BACKUPS = Path("/etc/NetworkManager/vln-b2-backups")


class SetupError(ValueError):
    """An operator-facing error with a fixed, credential-free message."""


def active_connection(interface):
    import dbus

    bus = dbus.SystemBus()
    manager = dbus.Interface(bus.get_object(SERVICE, "/org/freedesktop/NetworkManager"), SERVICE)
    device = bus.get_object(SERVICE, manager.GetDeviceByIpIface(interface))
    active = dbus.Interface(device, "org.freedesktop.DBus.Properties").Get(
        SERVICE + ".Device", "ActiveConnection"
    )
    connection = dbus.Interface(bus.get_object(SERVICE, active), "org.freedesktop.DBus.Properties").Get(
        SERVICE + ".Connection.Active", "Connection"
    )
    proxy = dbus.Interface(bus.get_object(SERVICE, connection), SERVICE + ".Settings.Connection")
    return dbus, proxy, proxy.GetSettings()


def select_saved_connection(candidates, connection_id):
    matches = [(proxy, settings) for proxy, settings in candidates
               if str(settings.get("connection", {}).get("id", "")) == connection_id]
    if len(matches) != 1:
        raise SetupError("Expected exactly one saved connection with that name; nothing was changed.")
    return matches[0]


def saved_connection(connection_id):
    import dbus

    bus = dbus.SystemBus()
    manager = dbus.Interface(bus.get_object(SERVICE, "/org/freedesktop/NetworkManager/Settings"),
                             SERVICE + ".Settings")
    candidates = []
    for path in manager.ListConnections():
        proxy = dbus.Interface(bus.get_object(SERVICE, path), SERVICE + ".Settings.Connection")
        candidates.append((proxy, proxy.GetSettings()))
    proxy, settings = select_saved_connection(candidates, connection_id)
    return dbus, proxy, settings


def validate_enterprise(settings):
    if settings.get("802-11-wireless-security", {}).get("key-mgmt") != "wpa-eap":
        raise SetupError("Expected an existing WPA-Enterprise profile.")
    enterprise = settings.get("802-1x", {})
    if "peap" not in enterprise.get("eap", []) or not enterprise.get("identity"):
        raise SetupError("This helper supports the existing PEAP password profile only.")


def summary(settings):
    connection = settings["connection"]
    enterprise = settings.get("802-1x", {})
    return {
        "autoconnect": bool(connection.get("autoconnect", True)),
        "autoconnect_retries": int(connection.get("autoconnect-retries", -1)),
        "system_wide": not bool(connection.get("permissions", [])),
        "password_flags": int(enterprise.get("password-flags", 0)),
        "enterprise_method": [str(value) for value in enterprise.get("eap", [])],
    }


def configure_settings(settings, password, dbus):
    if not password:
        raise SetupError("An empty password is not saved.")
    validate_enterprise(settings)
    enterprise = settings.get("802-1x", {})
    # Retain the identity, CA, server checks, phase-2 method and all other settings.
    connection = settings["connection"]
    connection["permissions"] = dbus.Array([], signature="s")
    connection["autoconnect"] = dbus.Boolean(True)
    connection["autoconnect-retries"] = dbus.Int32(0)
    enterprise["password"] = dbus.String(password)
    enterprise["password-flags"] = dbus.UInt32(0)


def backup_wifi(settings):
    profile_uuid = str(uuid.UUID(str(settings["connection"]["uuid"])))
    BACKUPS.mkdir(mode=0o700, exist_ok=True)
    for path in Path("/etc/NetworkManager/system-connections").iterdir():
        if not path.is_file():
            continue
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(str(path))
        if parser.get("connection", "uuid", fallback="") == str(settings["connection"]["uuid"]):
            backup = BACKUPS / ("wifi-" + profile_uuid + ".before-vln-b2.nmconnection")
            if not backup.exists():
                shutil.copy2(str(path), str(backup))
                backup.chmod(0o600)
            return
    raise RuntimeError("No persistent profile found; inspect the host before changing it.")


def autologin_text(text, username):
    if not re.fullmatch(r"[a-z_][a-z0-9_-]*", username):
        raise SetupError("Invalid Linux login name.")
    section = re.search(r"(?ms)^\[daemon\][^\n]*\n(.*?)(?=^\[|\Z)", text)
    if section is None:
        raise SetupError("The existing GDM configuration needs a [daemon] section.")
    block = section.group(1)
    for key, value in (("AutomaticLoginEnable", "True"), ("AutomaticLogin", username)):
        pattern = r"(?m)^\s*" + key + r"\s*=.*$"
        if re.search(pattern, block):
            block = re.sub(pattern, key + "=" + value, block)
        else:
            block = block.rstrip() + "\n" + key + "=" + value + "\n"
    return text[:section.start(1)] + block + text[section.end(1):]


def set_autologin(username):
    account = pwd.getpwnam(username)
    if account.pw_uid < 1000:
        raise SetupError("Select a regular research login, not a system account.")
    old = GDM_CONFIG.read_text()
    updated = autologin_text(old, username)
    backup = GDM_CONFIG.with_name(GDM_CONFIG.name + ".before-vln-b2")
    if not backup.exists():
        shutil.copy2(str(GDM_CONFIG), str(backup))
    mode = GDM_CONFIG.stat().st_mode & 0o777
    descriptor, name = tempfile.mkstemp(prefix=".vln-b2-", dir=str(GDM_CONFIG.parent))
    with os.fdopen(descriptor, "w") as handle:
        handle.write(updated)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(name, mode)
    os.replace(name, str(GDM_CONFIG))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interface", default="wlan0")
    parser.add_argument("--connection-id", help="Edit exactly one saved profile by name, even if inactive")
    parser.add_argument("--apply", action="store_true", help="Prompt locally and save boot-time credentials")
    parser.add_argument("--autologin", help="Set this regular GDM login after saving Wi-Fi")
    args = parser.parse_args(argv)
    try:
        if args.autologin and not args.apply:
            raise SetupError("--autologin requires --apply.")
        if args.apply and os.geteuid() != 0:
            raise SetupError("Run the apply operation with sudo and the host system Python.")
        if args.autologin:
            if pwd.getpwnam(args.autologin).pw_uid < 1000:
                raise SetupError("Select a regular research login, not a system account.")
            autologin_text(GDM_CONFIG.read_text(), args.autologin)
        dbus, proxy, settings = (saved_connection(args.connection_id) if args.connection_id
                                 else active_connection(args.interface))
        if not args.apply:
            print(json.dumps(summary(settings), indent=2))
            return 0
        if not sys.stdin.isatty():
            raise SetupError("Use an interactive terminal; piped password input is not accepted.")
        validate_enterprise(settings)
        # Identity is shown only in the operator's terminal, never in a saved report.
        identity = str(settings.get("802-1x", {}).get("identity", ""))
        print("Configured enterprise account: " + identity)
        print("The password will be saved in NetworkManager's root-protected system profile.")
        print("This does not restart Wi-Fi, GDM, Tailscale, or the computer.")
        password = getpass.getpass("Wi-Fi account password: ")
        if getpass.getpass("Confirm Wi-Fi account password: ") != password:
            raise SetupError("The passwords do not match; nothing was saved.")
        configure_settings(settings, password, dbus)
        backup_wifi(settings)
        proxy.Update(settings)
        saved = proxy.GetSecrets("802-1x").get("802-1x", {})
        if saved.get("password") != password:
            raise RuntimeError("NetworkManager did not retain the supplied credential.")
        if args.autologin:
            set_autologin(args.autologin)
        print("Saved boot-time Wi-Fi settings. A controlled reconnect/boot test is still required.")
        return 0
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130
    except SetupError as error:
        print("Setup error: " + str(error), file=sys.stderr)
        return 2
    except Exception as error:
        # Third-party exception text may contain identifiers or credentials.
        print("Setup failed (" + type(error).__name__ + "). Inspect the settings locally; no reconnect was requested.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
