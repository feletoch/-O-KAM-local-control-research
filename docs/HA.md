# Home Assistant

## What works locally

The Python client exposes a small HTTP bridge:

```bash
python okam_local.py --http --bind 0.0.0.0 --port 8098
```

Endpoints:

```text
/health
/status
/snapshot
/light/on
/light/off
/siren/on
/siren/off
/ptz/up
/ptz/down
/ptz/left
/ptz/right
/ptz/stop
```

This is enough for:

- REST sensors from `/status`
- a generic camera/snapshot entity from `/snapshot`
- REST commands for light, siren, and PTZ
- a binary sensor from `/health`

Keep the bridge on a trusted LAN/VPN. It has no TLS. If you bind it beyond
localhost, use a token and a firewall.

## Wake caveat

The bridge does **not** wake a sleeping camera. The camera must be in
continuous/always-on mode, or have been woken by PIR/physical motion. Remote
wake is a vendor cloud service and is intentionally not implemented here.

For 24/7 local Home Assistant use, prefer a mains-powered camera with
ONVIF/RTSP. This BMW1-class battery model has no local RTSP/ONVIF endpoint.

## Status parsing

`/status` returns JavaScript-like text, not JSON:

```text
var batteryRate=100;
var isCharge=1;
var alarm_status=0;
var sdstatus=2;
```

Parse with a regex or a small template in Home Assistant.

## Network

Give the camera a DHCP reservation. The camera's P2P port changes, but the
directory lookup handles it. The client only needs the camera to be reachable
on the LAN and the vendor directory to be reachable for rendezvous.
