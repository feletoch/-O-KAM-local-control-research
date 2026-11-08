# O-KAM local control research

This repository documents what is actually possible with an O-KAM battery
Wi-Fi camera (BMW1-class firmware) **without the vendor relay**, and includes a
working pure-Python local client.

## Short version

- **Local control works** once the camera is awake:
  - direct LAN P2P (`direct-punch`, no relay)
  - login with the camera-level password
  - status, JPEG snapshot, live H.264
  - light, siren, PTZ
- **Fully local operation does not.**
  - The camera has no local HTTP CGI, RTSP, or ONVIF listener.
  - The camera's UDP port changes per session; the vendor P2P directory is
    needed for rendezvous.
  - Wake from sleep is a vendor low-power service. Direct P2P wake did not work
    on the tested firmware.
- The camera password can be derived from the O-KAM account record without
  asking the user to know it.

The practical local mode is: keep the camera in **continuous/always-on** mode,
use the vendor directory once for rendezvous, then do video and control over
direct LAN P2P.

## What is in the box

```text
README.md                 this summary
docs/FINDINGS.md          detailed results and limitations
docs/PROTOCOL.md          CS2/PPPP, CGI, password derivation
docs/SECURITY.md          public-repo hygiene and threat model
docs/HA.md                Home Assistant options
python/                   working pure-Python local client and probes
```

## Quick start

```bash
cd python
python -m pip install -r requirements.txt
python okam_local.py --configure
python okam_local.py --status
python okam_local.py --snapshot snapshot.jpg
python okam_local.py --http --bind 127.0.0.1 --port 8098
```

You need the camera VUID/transport UID and the **camera-level password**. The
O-KAM account password is not the camera password.

If the account does not expose a plaintext password, `okam_get_password.py`
derives it from the account record:

```bash
python okam_get_password.py
```

It saves only the camera credentials to `okam_config.json`. Never commit that
file.

## What is deliberately not included

- No camera/account identifiers, passwords, MAC addresses, LAN IPs, or init
  strings.
- No vendor wake-service signing credentials.
- No vendor SDK binaries or proprietary libraries.
- No Android application source in this repository.

## Local vs cloud

| Function | Local-only? | Notes |
|---|---|---|
| Login | yes | once the camera password is known |
| Status/snapshot | yes | direct P2P |
| Live H.264 | yes | direct P2P, no relay |
| Light/siren/PTZ | yes | direct P2P |
| Initial rendezvous | no | vendor UDP directory, port changes |
| Wake from sleep | no | vendor low-power service |
| RTSP/ONVIF | no | not exposed on this model |

The directory sees the device UID and network address, but not the camera
password, video, or commands. The relay is not used.

## Security

This camera family has a documented history of weak/plaintext credentials and
P2P protocol weaknesses. Keep the camera on an isolated IoT VLAN or trusted
LAN, do not expose the HTTP bridge to the internet, and do not publish
captures, `okam_config.json`, or device identifiers.

This is an independent interoperability project. It is not affiliated with
O-KAM, VStarcam, Eye4, or their vendors.
