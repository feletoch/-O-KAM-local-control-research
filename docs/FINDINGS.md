# Findings

## Tested setup

An O-KAM battery Wi-Fi camera (BMW1-class firmware) was tested on the same LAN
as a PC and an Android phone. Identifiers and addresses are omitted from this
repository.

## 1. Direct LAN P2P works

Using the camera's transport UID and a cached P2P initialization string, a
CS2/PPPP session established a **direct** path:

```text
path=direct-punch
peer=<camera LAN address>:<random UDP port>
```

No vendor relay was used. The camera's local UDP port changed between sessions,
so the vendor UDP directory was contacted at the start of each new session. The
directory only supplies the current address/port; login, media, and commands
then run directly.

## 2. Camera password derivation

The O-KAM account device record contained an empty `password` field but:

```text
security    32 hex characters
doubleCheck 9 digits
```

The camera password is:

```text
key = MD5(doubleCheck + "_+Vstarcam++20200715")
password = AES-128-CBC-decrypt(security, key, IV=0, PKCS#7 unpad)
```

This matches the vendor `AppCrypto` format. The derived value logs in as
`admin` over P2P. The app/helper never prints the password.

## 3. No local web/RTSP/ONVIF

The camera did not expose a local HTTP CGI, RTSP, or ONVIF listener on the LAN.
The firmware reported:

```text
support_Plaintext_Pwd=0
DualAuthentication=0
```

The O-KAM Pro "Plaintext password settings" option is absent for this model.
The `get_params.cgi` reply may contain a web port, but that port exists only
behind the P2P transport; it is not reachable over TCP.

## 4. Local capabilities verified

- status (`get_status.cgi`)
- JPEG snapshot (`snapshot.cgi`)
- live H.264 keyframe + P-frames
- light on/off
- siren on/off
- PTZ up/down/left/right/stop
- local HTTP bridge for snapshots and controls

Useful status fields include battery, charging, PIR presence, SD status, alarm
status, Wi-Fi, firmware, and `support_*` capability flags. Power state can be
read/written through `trans_cmd_string.cgi?cmd=2106` (`lowPower`, AOV wake
interval, sleep flag).

## 5. Wake is not local

The camera's own UI text distinguishes power-saving, deep-sleep, and
ultra-low-power modes. The tested camera was put into `lowPower=1` and allowed
to sleep.

Results:

- ping stopped; the Wi-Fi module went offline;
- direct P2P wake retries failed;
- the vendor native `P2P_NodeWakeup` did not work through the exposed
  `JNIApi`/initialization path;
- the official low-power service (`liteos-master.eye4.cn`, ports 32320 and
  12320) accepted the VUID and returned sleep states, but the camera came online
  about 12 seconds later;
- direct P2P then worked and `lowPower=0` was written back.

The working remote wake path was therefore the official vendor cloud service,
not a local packet. That service and its signing credentials are intentionally
**not included** in this repository.

## 6. Practical conclusion

There is no fully local solution for a sleeping camera on this firmware:

1. Keep the camera continuously powered/always-on.
2. Use the vendor directory once to learn its current LAN UDP port.
3. Use direct LAN P2P for live video, snapshots, and controls.
4. Accept PIR/physical wake for battery sleep, or another camera model with
   ONVIF/RTSP for true local 24/7 operation.

## 7. Reproducibility

The Python client in `python/` implements the local path:

- VUID → transport UID resolution
- cached init-string fetch
- directory rendezvous and direct punch
- camera login
- CGI control/status/snapshot
- live H.264 reads
- local HTTP bridge

Run `okam_local.py --configure` with your own camera credentials. Do not commit
the resulting config.
