import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from okam_native.cs2 import (
    LIVE_STREAM_RESPONSE_COMMANDS,
    CS2Session,
    authenticate_camera,
    inspect_h264,
    make_cgi_request,
    read_command_result,
    read_video_frame,
    write_command,
)

cfg = json.loads((Path(__file__).resolve().parent.parent / "okam_config.json").read_text())
uid = cfg["uid"]
service = cfg["service"]
password = cfg["password"]

for substream in (2, 1, 0):
    print("=== substream", substream)
    session = CS2Session(uid, service, prefer_relay=False)
    try:
        session.connect(timeout=30)
        print("path", session.connect_path, "peer", session._peer)
        login = authenticate_camera(session, password, timeout=30)
        print("login", login.candidate)
        write_command(
            session,
            make_cgi_request(
                f"livestream.cgi?streamid=10&substream={substream}&",
                login.user,
                login.password,
            ),
        )
        answer = read_command_result(
            session, LIVE_STREAM_RESPONSE_COMMANDS, timeout=10.0
        )
        print("start answer", answer)
        deadline = time.monotonic() + 15.0
        frames = 0
        while time.monotonic() < deadline and frames < 6:
            payload, frame_type = read_video_frame(session, timeout=10.0)
            valid, keyframe = inspect_h264(payload)
            print(
                "frame",
                frames,
                "type",
                hex(frame_type),
                "bytes",
                len(payload),
                "valid",
                valid,
                "key",
                keyframe,
                "head",
                payload[:16].hex(),
            )
            frames += 1
        print("frames", frames)
    except Exception as exc:
        print("ERROR", type(exc).__name__, exc)
    finally:
        session.close()

