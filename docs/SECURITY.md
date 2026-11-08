# Security and public-repo hygiene

## Sensitive values that must never be committed

- camera VUID and transport UID
- camera-level password
- O-KAM account email/password
- `security` and `doubleCheck` account fields
- MAC address and LAN IPs
- `okam_config.json`
- P2P init strings and packet captures
- vendor wake-service access/secret keys
- vendor SDK binaries and extracted SDK sources

`.gitignore` excludes the common local artifacts. Check with:

```bash
git grep -n -E "password|loginpas|security|doubleCheck|VUID|UID|192\\.168\\.|([0-9A-Fa-f]{2}:){5}"
```

before publishing.

## Camera security

This camera family has a documented history of weak P2P/credential handling.
Use it on an isolated IoT VLAN or trusted LAN. Do not expose the local HTTP
bridge, P2P ports, RTSP, or ONVIF to the internet.

The camera password is a device credential. Deriving it from an account record
is for your own device and your own account only.

## Bridge

The Python HTTP bridge binds to `127.0.0.1` by default. If you bind it to a LAN
address, use a firewall and a token; do not port-forward it. The bridge has no
TLS.

## Scope

This repository contains interoperability research and a local client. It does
not include the vendor wake service or its credentials. Vendor components
remain subject to their own licenses.
