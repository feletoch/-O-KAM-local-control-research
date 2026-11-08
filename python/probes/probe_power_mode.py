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
paths = [
    "trans_cmd_string.cgi?cmd=2106&command=1&",
    "trans_cmd_string.cgi?cmd=2106&command=13&",
    "trans_cmd_string.cgi?cmd=2106&command=21&",
    "trans_cmd_string.cgi?cmd=4104&command=0&",
]
session = CS2Session(cfg["uid"], cfg["service"], prefer_relay=False)
try:
    session.connect(timeout=30)
    login = authenticate_camera(session, cfg["password"], timeout=30)
    for path in paths:
        print("=====", path)
        write_command(session, make_cgi_request(path, login.user, login.password))
        command, payload = read_command(session, timeout=15)
        print("command", command)
        print(payload.decode("utf-8", "replace")[:2000])
finally:
    session.close()

