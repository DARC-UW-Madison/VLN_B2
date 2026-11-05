# Receiving B2 built-in sensors

[日本語](built-in-sensors.ja.md) · [Documentation](README.md) · [Network procedure](field-network.md)

## What was verified

The first onboard sensor inspection received front/back video, inertial and
joint telemetry, and sport/odometry state without requesting movement. It used
the existing i7 ROS 2 Foxy installation and message workspace. No package,
driver, service, network or firmware changes were made on B2.

```text
Existing B2 camera/state producers
                | native robot Ethernet / DDS domain 0
Onboard i7: temporary ROS 2 subscriptions + existing video decoder
                | authenticated SSH stdout over USB Ethernet
External Jetson: private JSON, derived JPEGs and standalone HTML
```

SSH transported results from a program running on the i7. It did not forward
DDS discovery or make the external SDK container a native robot-LAN participant.
The script was supplied through SSH stdin and exited after capture; no probe
source or capture files were installed on the i7. Mac only initiated management
commands; camera images were retained on the external Jetson.

| Source | Result in the final 15-second subscription window |
|---|---|
| `/front_videohub/videostream` | 21 messages; a derived JPEG decoded at 1280×720 |
| `/back_videohub/videostream` | 21 messages; a derived JPEG decoded at 640×360 |
| `/lf/sportmodestate` | 14 messages |
| `/lf/odommodestate` | 13 messages |
| `/lf/lowstate` | 13 messages; IMU and joint telemetry available |
| Panorama video, wireless controller and LIO odometry topics | No messages received during this window |
| Point cloud / `/pctoimage_local` | No confirmed usable payload; driver ownership and message compatibility remain open |

The earlier eight-second capture decoded only the back stream at 1920×1080.
The front stream produced bytes but did not decode in that attempt; a longer
capture decoded both streams. The exact first failure cause is unconfirmed.
Both captures selected the `video720p` field. Its name does **not** establish
the actual resolution; decoded dimensions differed between attempts. No stable
resolution configuration or camera-to-topic physical mapping was established.

These are **DDS message counts**, not video frame counts or a measured camera
frame rate. LowState exposed 20 joint-state slots; that is a message layout,
not evidence of 20 physical joints. Zero reception does not establish that a
sensor is absent: publisher activity, QoS and available message bindings need
separate checks. Topic names alone do not establish sensor ownership.

## View the saved images without powering B2

On the **external Jetson desktop**, open a terminal and run:

```sh
cd ~/Developer/Projects/Robotics/b2/VLN_B2
xdg-open "$PWD/local/b2-damping-sensors-01/retry-01/index.html"
```

This opens the saved front/back previews. The parent directory's `index.html`
belongs to the earlier attempt and contains only the successfully decoded back
preview. Neither page is live video or a TIC-VLA prediction. They need no robot,
internet connection, web server or model load. Check the physical view,
orientation and image quality with the operator at the next visit.

## Repeat a passive capture

The public [probe](../tools/probe_onboard_sensors.py) requires Python 3.8+,
matching ROS 2/message bindings, and existing Pillow/FFmpeg for video decoding.
It does not install dependencies. The project venv and GPU model container do
not automatically contain the onboard Foxy bindings. The standalone probe can
run independently of the project's Python 3.10+ package.

The following is a **template**, not a new completed trial. Run it on the
external Jetson only after B2 is powered, authorized access is available and
the native interface/domain/workspace have been rechecked. Replace every
`VERIFIED_*` value, including the path inside the remote command. Use the
private inventory for the pinned host key; do not disable host-key checks.
The target may be a scoped link-local address rather than a working native-LAN
IPv4 address. Authentication is interactive in the terminal, never in a file.

```sh
bash --noprofile --norc <<'SH'
set -e
cd ~/Developer/Projects/Robotics/b2/VLN_B2
umask 077
mkdir local/built-in-sensors-02
B2_TARGET='VERIFIED_AUTHORIZED_SSH_TARGET'
B2_KNOWN_HOSTS='VERIFIED_PRIVATE_KNOWN_HOSTS_FILE'
ssh -T -o StrictHostKeyChecking=yes -o ConnectTimeout=5 \
  -o UserKnownHostsFile="$B2_KNOWN_HOSTS" "$B2_TARGET" \
  'bash --noprofile --norc -c "
set -e
export PATH=/usr/bin:/bin:/opt/ros/foxy/bin PYTHONDONTWRITEBYTECODE=1
source /opt/ros/foxy/setup.bash
source VERIFIED_MESSAGE_WORKSPACE/install/setup.bash
exec /usr/bin/python3 - --interface VERIFIED_NATIVE_INTERFACE --domain-id 0 --seconds 15 --include-images
"' \
  < tools/probe_onboard_sensors.py \
  > local/built-in-sensors-02/sensors.json
SH
```

Domain 0 was measured on this unit; replace it if the verified domain differs.
No source or capture files are written on B2 by this command. The final redirect
writes private JSON on the external Jetson. Check SSH's exit status and the
report's topic counts and `not_subscribed`/`decode_error` entries. An empty or
invalid JSON file is failure, not an empty successful observation. Keep stderr
visible for authentication, workspace and decoding errors. Use a new output
directory on every attempt rather than overwriting evidence.

The probe discovers for about two seconds, subscribes for at most 15 seconds,
then attempts preview decoding with an eight-second timeout per stream.
Compressed buffers are capped at 8 MiB per stream. Without `--include-images`,
it reports counts/state and does not retain/decode video. All subscriptions
use best-effort, volatile QoS with depth one. The script creates no command
publisher or robot service request. DDS discovery still exchanges network data;
explicit native-interface selection keeps this diagnostic off campus Wi-Fi.

To extract JPEGs from a successful new private JSON report:

```sh
python3 - <<'PY'
import base64
import hashlib
import json
from pathlib import Path

folder = Path('local/built-in-sensors-02')
report = json.loads((folder / 'sensors.json').read_text())
assert report['actuation_requests_sent'] is False
for topic, item in report.get('previews', {}).items():
    if not item.get('decoded'):
        print(topic, item.get('decode_error', 'No decoded preview'))
        continue
    payload = base64.b64decode(item['jpeg_base64'], validate=True)
    assert hashlib.sha256(payload).hexdigest() == item['jpeg_sha256']
    assert topic in ['/front_videohub/videostream', '/back_videohub/videostream',
                     '/panorama_videohub/videostream']
    path = folder / (topic.split('/')[1] + '.jpg')
    with path.open('xb') as output:
        output.write(payload)
    path.chmod(0o600)
    print(path, item['width'], item['height'])
PY
```

Open a printed JPEG path using the Jetson file manager. The probe's JSON can
contain images and private state; keep the whole directory outside Git. Do not
upload it as a public issue attachment.

## What remains before using these images in TIC-VLA

The model demo still uses the **external ZED**. This inspection did not switch
its input to a built-in camera or run inference on the built-in images. First
establish camera identity, mounting transform, field of view, exposure timing,
buffering and decoded-image format. The message's raw `time_frame` value has
unverified units and clock origin; do not subtract it from Jetson time. A frame
decoded from a compressed sequence is not necessarily the first received frame.

Then pair actual state and images on verified clocks/frames, implement the
observation adapter, and evaluate predictions without commands. LiDAR has a
separate localization/obstacle-processing role; receiving a cloud would not by
itself add it to TIC-VLA's RGB input. This is independent of commissioning a
continuous state/control path, command expiry and physical stopping.

The official [video message definition](https://raw.githubusercontent.com/unitreerobotics/unitree_ros2/master/cyclonedds_ws/src/unitree/unitree_go/msg/Go2FrontVideoData.msg)
defines the byte arrays and timestamp field. It does not document their
codec, timestamp units or this unit's physical camera mapping. The official
[ROS 2 repository](https://github.com/unitreerobotics/unitree_ros2) documents
the native interface; local reception and decoding provide the evidence above.
