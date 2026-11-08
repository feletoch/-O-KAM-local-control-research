import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from okam_native.cs2 import (
    LIVE_STREAM_RESPONSE_COMMANDS,
    CS2Session,
    authenticate_camera,
    make_cgi_request,
    read_command_result,
    read_video_frame,
    write_command,
)

cfg = json.loads((Path(__file__).resolve().parent.parent / "okam_config.json").read_text())
session = CS2Session(cfg["uid"], cfg["service"], prefer_relay=False)
try:
    session.connect(timeout=30)
    login = authenticate_camera(session, cfg["password"], timeout=30)
    write_command(
        session,
        make_cgi_request(
            "livestream.cgi?streamid=10&substream=2&", login.user, login.password
        ),
    )
    read_command_result(session, LIVE_STREAM_RESPONSE_COMMANDS, timeout=10.0)
    output = Path(__file__).resolve().parent / "live.h264"
    total = 0
    with output.open("wb") as handle:
        for _ in range(60):
            payload, _frame_type = read_video_frame(session, timeout=10.0)
            handle.write(payload)
            total += len(payload)
    print("wrote", output, total, "bytes")
finally:
    session.close()

