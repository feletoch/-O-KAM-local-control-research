# Python local client

This is the working pure-Python CS2/PPPP client. It connects to the camera over
**direct LAN P2P** and does not use the vendor relay.

## Install

```bash
python -m pip install -r requirements.txt
```

`cryptography` is only needed for deriving the camera password from the account
record. The local client itself uses the standard library.

## Configure

```bash
python okam_local.py --configure
```

You will need:

- the camera VUID (or the 15-character transport UID)
- the camera-level password

The init string is fetched once from the vendor service and cached in
`okam_config.json`. The camera password is stored there; keep the file private
and never commit it.

Alternatively:

```bash
python okam_get_password.py
```

This asks for the O-KAM account email/password, enumerates the camera, derives
the camera password from `security` + `doubleCheck`, and writes only the camera
credentials to `okam_config.json`. The account password is not saved.

## Commands

```bash
python okam_local.py --status
python okam_local.py --snapshot snap.jpg
python okam_local.py --light on
python okam_local.py --light off
python okam_local.py --siren off
python okam_local.py --ptz right
python okam_local.py --ptz stop
```

## HTTP bridge

```bash
python okam_local.py --http --bind 127.0.0.1 --port 8098
```

Endpoints: `/health`, `/status`, `/snapshot`, `/light/on|off`,
`/siren/on|off`, `/ptz/up|down|left|right|stop`.

Bind to `127.0.0.1` unless you have a trusted LAN/VPN. Do not expose the bridge
to the internet.

## Probes

`probes/` contains read-only/controlled experiments:

- `probe_power_mode.py` — reads `lowPower`, correction type, sleep flag
- `probe_power_params.py` — reads power/network parameters
- `set_power_mode.py` — writes `lowPower` (explicit, reversible)
- `capture_live.py` — captures raw H.264 for inspection
- `live_test.py` — prints live frame metadata

## Local limitations

- The camera’s UDP port changes per session, so the vendor P2P directory is
  still needed for rendezvous.
- No local HTTP CGI, RTSP, or ONVIF listener exists on this model.
- Wake from sleep is a vendor cloud service; it is intentionally not included
  in this repository. The camera must be awake (continuous mode or PIR) for
  local control.
