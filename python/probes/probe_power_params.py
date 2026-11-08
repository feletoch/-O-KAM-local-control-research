import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from okam_native.cs2 import (
    CS2Session,
    authenticate_camera,
    make_cgi_request,
    read_command,
    write_command,
)

cfg = json.loads((Path(__file__).resolve().parent.parent / "okam_config.json").read_text())
session = CS2Session(cfg["uid"], cfg["service"], prefer_relay=False)
try:
    session.connect(timeout=30)
    login = authenticate_camera(session, cfg["password"], timeout=30)
    for path in ("get_params.cgi?", "get_camera_params.cgi?"):
        write_command(session, make_cgi_request(path, login.user, login.password))
        _command, payload = read_command(session, timeout=15)
        text = payload.decode("utf-8", "replace")
        print("=====", path)
        for line in text.splitlines():
            if any(key in line.lower() for key in (
                    "power", "sleep", "wake", "aov", "pir", "battery",
                    "charge", "low", "interval", "rtsp", "onvif", "port")):
                print(line)
finally:
    session.close()

