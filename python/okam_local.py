#!/usr/bin/env python3
"""O-KAM local client / HTTP bridge (mostly local, direct LAN P2P).

This uses the pure-Python CS2/PPPP implementation from okam-ha-native, but
connects DIRECTLY to the camera (prefer_relay=False). It only contacts the
vendor directory to learn the camera's current local UDP port, and uses the
cached init string for server parameters.

Runs on a PC or on Android in Termux.

Setup on Android/Termux:
    pkg update
    pkg install python
    termux-setup-storage
    cd ~
    mkdir -p okam && cd okam
    # copy this file and the okam_native package here
    python okam_local.py --configure

Usage:
    python okam_local.py --configure
    python okam_local.py --http --bind 127.0.0.1 --port 8098
    python okam_local.py --status
    python okam_local.py --snapshot snap.jpg
    python okam_local.py --light on
    python okam_local.py --siren off
    python okam_local.py --ptz right

The camera password is stored in okam_config.json (chmod 600 recommended).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "okam_config.json"

# okam_native lives next to this script (copy from okam-ha-native/src/okam_native)
sys.path.insert(0, str(HERE))

try:
    from okam_native.cs2 import (
        CS2Session,
        authenticate_camera,
        make_cgi_request,
        read_command,
        write_command,
    )
    from okam_native.p2p import get_service_parameter, resolve_client_id
except ImportError as exc:  # pragma: no cover
    print("Missing okam_native package next to this script.")
    print("Copy okam-ha-native/src/okam_native into", HERE)
    raise SystemExit(1) from exc


DEFAULT_CONFIG = {
    "vuid": "",
    "uid": "",
    "service": "",
    "password": "",
    "bind": "127.0.0.1",
    "port": 8098,
    "token": "",
}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text()))
        except Exception as exc:
            print("Config read failed:", exc)
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass
    print("Saved", CONFIG_PATH)


class Camera:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.session: CS2Session | None = None
        self.lock = threading.Lock()
        self.password = cfg.get("password") or ""
        self.user = "admin"

    def ensure(self) -> CS2Session:
        if self.session is not None and self.session.connected:
            return self.session
        uid = self.cfg.get("uid") or ""
        if not uid:
            vuid = self.cfg.get("vuid") or ""
            if not vuid:
                raise RuntimeError("No VUID/UID configured")
            print("Resolving VUID", vuid)
            uid = resolve_client_id(vuid)
            self.cfg["uid"] = uid
            save_config(self.cfg)
        service = self.cfg.get("service") or ""
        if not service:
            print("Fetching init string for", uid[:4])
            service = get_service_parameter(uid)
            self.cfg["service"] = service
            save_config(self.cfg)
        print("Connecting direct to", uid)
        session = CS2Session(uid, service, prefer_relay=False)
        session.connect(timeout=30)
        print("P2P path:", session.connect_path, "peer:", session._peer)
        login = authenticate_camera(session, self.password, timeout=30)
        print("Login OK (candidate %d)" % login.candidate)
        self.session = session
        self.password = login.password
        return session

    def cgi(self, path: str, timeout: float = 10.0) -> bytes:
        with self.lock:
            session = self.ensure()
            write_command(session, make_cgi_request(path, self.user, self.password))
            command, payload = read_command(session, timeout=timeout)
            return payload

    def close(self) -> None:
        with self.lock:
            if self.session is not None:
                try:
                    self.session.close()
                except Exception:
                    pass
                self.session = None


def find_jpeg(payload: bytes) -> bytes | None:
    start = payload.find(b"\xff\xd8")
    if start < 0:
        return None
    end = payload.find(b"\xff\xd9", start + 2)
    if end < 0:
        return payload[start:]
    return payload[start:end + 2]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configure", action="store_true", help="prompt and save config")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--snapshot", metavar="FILE")
    ap.add_argument("--light", choices=["on", "off"])
    ap.add_argument("--siren", choices=["on", "off"])
    ap.add_argument("--ptz", choices=["up", "down", "left", "right", "stop"])
    ap.add_argument("--http", action="store_true", help="run local HTTP bridge")
    ap.add_argument("--bind", default=None)
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--token", default=None)
    args = ap.parse_args()

    cfg = load_config()

    if args.configure:
        cfg["vuid"] = input("VUID [%s]: " % cfg["vuid"]).strip() or cfg["vuid"]
        cfg["password"] = input("Camera password: ").strip()
        bind = input("Bind address [%s]: " % cfg["bind"]).strip()
        if bind:
            cfg["bind"] = bind
        port = input("Port [%d]: " % cfg["port"]).strip()
        if port:
            cfg["port"] = int(port)
        token = input("API token (optional) [%s]: " % cfg["token"]).strip()
        if token:
            cfg["token"] = token
        try:
            cfg["uid"] = resolve_client_id(cfg["vuid"])
            print("Transport UID:", cfg["uid"])
            cfg["service"] = get_service_parameter(cfg["uid"])
        except Exception as exc:
            print("Resolution failed (will retry later):", exc)
        save_config(cfg)
        return 0

    if args.bind:
        cfg["bind"] = args.bind
    if args.port:
        cfg["port"] = args.port
    if args.token is not None:
        cfg["token"] = args.token

    camera = Camera(cfg)

    try:
        if args.status:
            print(camera.cgi("get_status.cgi?name=admin&").decode("utf-8", "replace"))
            return 0
        if args.snapshot:
            payload = camera.cgi("snapshot.cgi?res=2&", timeout=15)
            jpeg = find_jpeg(payload)
            if jpeg is None:
                print("No JPEG in response (%d bytes):" % len(payload), payload[:200])
                return 1
            Path(args.snapshot).write_bytes(jpeg)
            print("Saved", args.snapshot, len(jpeg), "bytes")
            return 0
        if args.light:
            value = "1" if args.light == "on" else "0"
            camera.cgi("trans_cmd_string.cgi?cmd=2109&command=0&light=%s&" % value)
            print("Light", args.light)
            return 0
        if args.siren:
            value = "1" if args.siren == "on" else "0"
            camera.cgi("trans_cmd_string.cgi?cmd=2109&command=0&siren=%s&" % value)
            print("Siren", args.siren)
            return 0
        if args.ptz:
            commands = {"up": 0, "down": 2, "left": 4, "right": 6, "stop": 1}
            camera.cgi("decoder_control.cgi?command=%d&onestep=1&" % commands[args.ptz])
            print("PTZ", args.ptz)
            return 0

        if args.http:
            token = cfg.get("token") or ""
            bind = cfg.get("bind") or "127.0.0.1"
            port = int(cfg.get("port") or 8098)

            class Handler(BaseHTTPRequestHandler):
                def log_message(self, fmt, *values):
                    print("%s - %s" % (self.address_string(), fmt % values))

                def _allow(self) -> bool:
                    if not token:
                        return True
                    supplied = self.headers.get("X-Token") or urllib.parse.parse_qs(
                        urllib.parse.urlparse(self.path).query
                    ).get("token", [""])[0]
                    return supplied == token

                def _send(self, code: int, body: bytes, content_type: str):
                    self.send_response(code)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

                def do_GET(self):
                    if not self._allow():
                        self._send(401, b"unauthorized", "text/plain")
                        return
                    path = urllib.parse.urlparse(self.path).path
                    try:
                        if path == "/health":
                            self._send(200, b'{"ok":true}', "application/json")
                        elif path == "/status":
                            self._send(200, camera.cgi("get_status.cgi?name=admin&"), "text/plain; charset=utf-8")
                        elif path == "/snapshot":
                            payload = camera.cgi("snapshot.cgi?res=2&", timeout=15)
                            jpeg = find_jpeg(payload)
                            if jpeg is None:
                                self._send(502, b"no jpeg", "text/plain")
                            else:
                                self._send(200, jpeg, "image/jpeg")
                        elif path in ("/light/on", "/light/off"):
                            camera.cgi("trans_cmd_string.cgi?cmd=2109&command=0&light=%s&"
                                       % ("1" if path.endswith("on") else "0"))
                            self._send(200, b"ok", "text/plain")
                        elif path in ("/siren/on", "/siren/off"):
                            camera.cgi("trans_cmd_string.cgi?cmd=2109&command=0&siren=%s&"
                                       % ("1" if path.endswith("on") else "0"))
                            self._send(200, b"ok", "text/plain")
                        elif path.startswith("/ptz/"):
                            direction = path.rsplit("/", 1)[-1]
                            commands = {"up": 0, "down": 2, "left": 4, "right": 6, "stop": 1}
                            if direction not in commands:
                                self._send(400, b"bad direction", "text/plain")
                                return
                            camera.cgi("decoder_control.cgi?command=%d&onestep=1&" % commands[direction])
                            self._send(200, b"ok", "text/plain")
                        else:
                            self._send(404, b"not found", "text/plain")
                    except Exception as exc:
                        self._send(502, str(exc).encode(), "text/plain")

            print("HTTP bridge on http://%s:%d" % (bind, port))
            print("Endpoints: /health /status /snapshot /light/on /light/off /siren/on /siren/off /ptz/{up,down,left,right,stop}")
            if token:
                print("Token required via ?token= or X-Token header")
            server = ThreadingHTTPServer((bind, port), Handler)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print("Stopping")
            finally:
                server.server_close()
                camera.close()
            return 0

        print("Nothing to do. Use --configure, --status, --snapshot, --light, --siren, --ptz or --http.")
        return 2
    finally:
        camera.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print("Error:", exc)
        raise SystemExit(1)
