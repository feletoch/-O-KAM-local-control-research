#!/usr/bin/env python3
"""One-time O-KAM account helper: retrieve the camera-level password and save it.

This contacts the official O-KAM account service once, enumerates the camera,
and writes its device password into okam_config.json for okam_local.py.

If the account record has an empty ``password`` field but contains ``security``
and ``doubleCheck``, the helper decrypts the camera password from those values
(the same AppCrypto format used by the O-KAM app).

The camera password is NOT the O-KAM account password. Do not post it anywhere.

Usage:
    python okam_get_password.py

On Android/Termux:
    pkg install python
    python okam_get_password.py
"""

from __future__ import annotations

import getpass
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    from okam_native.account import Eye4AccountClient, derive_device_password
    from okam_native.p2p import get_service_parameter, resolve_client_id
except ImportError as exc:
    print("Missing okam_native package next to this script.")
    raise SystemExit(1) from exc

CONFIG_PATH = HERE / "okam_config.json"


def main() -> int:
    username = input("O-KAM account email: ").strip()
    password = getpass.getpass("O-KAM account password (not shown): ")
    if not username or not password:
        print("Account email/password required.")
        return 2

    print("Contacting the official O-KAM account service...")
    try:
        devices = Eye4AccountClient().enumerate(username, password)
    except Exception as exc:
        print("Account lookup failed:", exc)
        return 1

    if not devices:
        print("No cameras visible to this account.")
        return 1

    print("\nCameras visible to this account:")
    derived_passwords = []
    for index, device in enumerate(devices):
        derived = device.device_password or derive_device_password(device)
        derived_passwords.append(derived)
        if device.device_password:
            state = "password available"
        elif derived:
            state = "password derivable from security record"
        else:
            state = "no password in account"
        print("  [%d] %s  uid=%s  (%s)" % (index, device.name, device.uid, state))

    if len(devices) == 1:
        choice = 0
    else:
        raw = input("\nChoose camera index: ").strip()
        try:
            choice = int(raw)
        except ValueError:
            print("Invalid index.")
            return 2
    device = devices[choice]
    camera_password = device.device_password or derived_passwords[choice]

    if not camera_password:
        print("\nThe account did not return a camera-level password.")
        print("This is normal for sharing or for firmware that keeps the password")
        print("on the camera. You can set one in O-KAM Pro if the camera supports")
        print("'Plaintext password settings'; this BMW1 reports that it does not.")
        print("Otherwise, reset the camera and re-add it, or enter a known")
        print("camera password below.")
        manual = getpass.getpass("Camera password (or blank to skip): ").strip()
        config = {}
        if CONFIG_PATH.exists():
            try:
                config = json.loads(CONFIG_PATH.read_text())
            except Exception:
                config = {}
        config["vuid"] = device.uid
        try:
            config["uid"] = resolve_client_id(device.uid)
        except Exception:
            config["uid"] = device.uid
        if manual:
            config["password"] = manual
            try:
                config["service"] = get_service_parameter(config["uid"])
            except Exception:
                pass
            CONFIG_PATH.write_text(json.dumps(config, indent=2))
            try:
                import os
                os.chmod(CONFIG_PATH, 0o600)
            except OSError:
                pass
            print("Saved camera password and UID to", CONFIG_PATH)
            return 0
        CONFIG_PATH.write_text(json.dumps(config, indent=2))
        print("Saved UID/VUID without a password to", CONFIG_PATH)
        print("Set the plaintext password in O-KAM Pro, then rerun this script")
        print("or enter it in the Android app.")
        return 1

    config = {}
    if CONFIG_PATH.exists():
        try:
            config = json.loads(CONFIG_PATH.read_text())
        except Exception:
            config = {}
    config["vuid"] = device.uid
    try:
        config["uid"] = resolve_client_id(device.uid)
    except Exception:
        config["uid"] = device.uid
    config["password"] = camera_password
    try:
        config["service"] = get_service_parameter(config["uid"])
    except Exception as exc:
        print("Init-string fetch failed (will retry later):", exc)

    CONFIG_PATH.write_text(json.dumps(config, indent=2))
    try:
        import os
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass

    source = "account password field" if device.device_password else "derived security record"
    print("\nSaved camera credentials to", CONFIG_PATH)
    print("VUID:", device.uid)
    print("Transport UID:", config.get("uid"))
    print("Password source:", source)
    print("Password: <saved, not printed>")
    print("\nNow run:")
    print("  python okam_local.py --status")
    print("  python okam_local.py --snapshot snap.jpg")
    print("  python okam_local.py --http --bind 0.0.0.0 --port 8098")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
