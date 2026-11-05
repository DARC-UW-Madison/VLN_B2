# Receiving B2 built-in sensors

[日本語](built-in-sensors.ja.md) · [Documentation](../README.md) · [Network procedure](../how-to/field-network.md)

> Document type: **Record**. Commands and measurements describe the recorded environment; use the how-to guides for current operation.

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
The saved discovery snapshot counted no panorama/LIO publishers and one wireless
publisher. `/pctoimage_local` could not be subscribed to because the existing
Python environment lacked `unitree_interfaces`; its publisher count was also
zero. These are separate findings, not a verified absence of the hardware.

## Procedure

Use the separate [viewing and capture procedure](../how-to/built-in-sensors.md).

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
