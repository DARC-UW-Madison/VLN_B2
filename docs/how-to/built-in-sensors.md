# View and capture built-in sensor images

[日本語](built-in-sensors.ja.md) · [Procedures](../README.md)

> Document type: **Procedure**.

View saved results or repeat passive capture during a powered visit. Measurements belong to [the sensor record](../records/built-in-sensors.md).

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

The public [probe](../../tools/probe_onboard_sensors.py) requires Python 3.8+,
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
