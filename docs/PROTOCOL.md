# Protocol notes

## Transport

The camera uses a CS2/PPPP-style UDP protocol. A client asks a vendor directory
for the camera's current address, then sends a direct punch. Once the session is
ready, commands and media use acknowledged DRW packets on channels.

The implementation in `python/okam_native/cs2.py` handles:

- directory lookup
- direct punch / readiness
- encrypted packet framing
- acknowledged writes
- retransmission
- channel buffers
- video frame reads
- close/keepalive control packets

The initialization string is fetched from the vendor service at runtime and
cached in `okam_config.json`. It is not committed.

## Login and CGI

Camera authentication is a CGI request over P2P channel 0:

```text
GET /get_status.cgi?name=admin&loginuse=admin&loginpas=<camera-password>&user=admin&pwd=888888&
```

A `result=0` in the response means login succeeded. Subsequent CGI responses are
length-prefixed frames with a small header and a JavaScript-like text body.

Common requests used by the client:

```text
get_status.cgi
get_params.cgi
get_camera_params.cgi
snapshot.cgi?res=2&
livestream.cgi?streamid=10&substream=2&
livestream.cgi?streamid=16&substream=0&
trans_cmd_string.cgi?cmd=2109&command=0&light=1
trans_cmd_string.cgi?cmd=2109&command=0&siren=1
decoder_control.cgi?command=<0|1|2|4|6>&onestep=1
trans_cmd_string.cgi?cmd=2106&command=1&
trans_cmd_string.cgi?cmd=2106&command=2&lowPower=<0..3>&
```

## Live video

Live start is answered on channel 0. H.264 access units arrive on channel 1 with
a 32-byte header beginning `55 AA 15 A8`; the payload length is little-endian at
offset 16. The stream contains SPS/PPS and keyframes, and can be fed to
MediaCodec/ffmpeg.

## Password derivation

The account record's `security` value is AES-128-CBC ciphertext of the camera
password:

```text
key = MD5(doubleCheck + "_+Vstarcam++20200715")
plaintext = AES-128-CBC(security, key, IV=0, PKCS#7)
```

This is the same format as the vendor `AppCrypto` helper. It is implemented in
`python/okam_native/account.py`; values are never logged.

## Directory and wake dependencies

- **Directory:** the camera's LAN UDP port changes between sessions. The vendor
  UDP directory is used to learn the current port. There is no reliable local
  discovery on this firmware.
- **Wake:** the camera's remote wake is a vendor low-power service over TCP with
  signed JSON messages. It is cloud-dependent and is not included here.

## Privacy notes

Do not publish:

- VUID / transport UID
- camera password
- account email or password
- `security` / `doubleCheck`
- MAC address or LAN IPs
- init strings or packet captures containing credentials
- vendor wake signing keys
