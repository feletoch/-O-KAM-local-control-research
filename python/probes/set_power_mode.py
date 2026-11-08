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

mode = sys.argv[1] if len(sys.argv) > 1 else "1"
if mode not in ("0", "1", "2", "3"):
    raise SystemExit("mode must be 0..3")

cfg = json.loads((Path(__file__).resolve().parent.parent / "okam_config.json").read_text())
session = CS2Session(cfg["uid"], cfg["service"], prefer_relay=False)
try:
    session.connect(timeout=30)
    login = authenticate_camera(session, cfg["password"], timeout=30)
    for path in (
        "trans_cmd_string.cgi?cmd=2106&command=2&lowPower=%s&" % mode,
        "trans_cmd_string.cgi?cmd=2106&command=1&",
    ):
        print("=====", path)
        write_command(session, make_cgi_request(path, login.user, login.password))
        _command, payload = read_command(session, timeout=15)
        print(payload.decode("utf-8", "replace")[:1200])
finally:
    session.close()

