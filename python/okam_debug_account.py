#!/usr/bin/env python3
"""Inspect the raw O-KAM account device records without printing secrets.

Run this if okam_get_password.py says "no password in account". It shows the
field names returned by /PC/device/show and redacts password/token values.

Usage:
    python okam_debug_account.py
"""

from __future__ import annotations

import getpass
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request

BASE = "https://api.eye4.cn"
SECRET_KEY = re.compile(r"(pass|pwd|token|secret|key|auth)", re.I)


def request(method: str, path: str, query: dict | None = None, form: dict | None = None):
    url = BASE + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data = urllib.parse.urlencode(form).encode("ascii") if form is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/json",
            "client_version": "10.0.1",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "okam-debug-account",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def redact(value):
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if SECRET_KEY.search(key) and isinstance(item, str) and item:
                out[key] = "<%d chars>" % len(item)
            else:
                out[key] = redact(item)
        return out
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def main() -> int:
    username = input("O-KAM account email: ").strip()
    password = getpass.getpass("O-KAM account password (not shown): ")
    if not username or not password:
        return 2

    summary = request("POST", "/user/summary", form={"name": username, "oemid": "VSTC"})
    user_id = summary.get("userid")
    if not user_id:
        print("No userid in summary:", redact(summary))
        return 1
    digest = hashlib.md5(password.encode("utf-8")).hexdigest()
    login = request("GET", "/login/token",
                    query={"userid": str(user_id), "password": digest, "type": "PC"})
    if not isinstance(login, dict) or not login.get("token"):
        print("Login failed:", redact(login))
        return 1
    devices = request("GET", "/PC/device/show",
                      query={"userid": str(user_id), "pwd": digest})
    print("\nRaw device records (secret values redacted):")
    print(json.dumps(redact(devices), indent=2, ensure_ascii=False))
    print("\nKeys per device:")
    if isinstance(devices, list):
        for index, device in enumerate(devices):
            if isinstance(device, dict):
                print("  [%d] %s" % (index, ", ".join(sorted(device.keys()))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
