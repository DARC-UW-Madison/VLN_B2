# External camera checks

[日本語](camera-checks.ja.md) · [Records](README.md)

> Document type: **Record**. Evidence of performed configuration and checks, separate from current operating procedures.

## Current acceptance

On 2026-10-29, the existing Jetson SDK headers/library reported ZED SDK 4.1.2.
The SDK directory was owned by an existing lab login and its SDK group, with no
access for the research login. The research venv did not contain `pyzed`.
Those host permissions, group memberships and Python installations were preserved.

A separate private Python prefix now contains official `pyzed` 4.1 for ARM64
CPython 3.11 and Cython 3.0.12. The existing GPU image provides NumPy 1.26.4.
An offline non-root container imported `pyzed.sl`, returned SDK version 4.1.2,
exposed `DEPTH_MODE.NONE` and `optional_settings_path`, and passed `pip check`.
It did not open a camera. No ZED/video device was present at that inspection.
Import success does not validate USB capture, calibration or image quality.

### First physical capture passed

The subsequently connected camera identified as one ZED 2i. Its video interface
negotiated 5 Gbps and exposed two V4L2 nodes; its companion HID/USB endpoint was
mapped separately. Only the identified camera nodes were passed to the container.
The existing matching 1,568-byte calibration file was copied into private settings
storage; the original SDK was unchanged and no calibration/model download was
needed. With depth disabled, the project camera adapter captured a 1280×720 left
rectified JPEG, 196,592 bytes, and exited successfully within the 45-second
supervisor. The saved image was visually inspected and was upright and nonblank.
This is a desk scene, not a mounted robot's navigation view. Source/receipt times
were recorded separately; capture-clock alignment is still unverified.

Raw images, serial numbers and exact device mappings stay in ignored private
records, not in this repository. The CLI now accepts `--settings-dir` for both
`camera` and `record`, so SDK calibration can use the separate writable mount.


A separate short stream check then completed **90/90 SDK grabs**, zero failed
grabs, over 2.968 seconds between first/last receipts (about 29.99 grabs/s).
Source timestamps increased strictly. This loop did not encode/write every
frame, so it is not JPEG throughput or a long-duration reliability test. Clock
alignment, mounted-view calibration and live inference remain unvalidated.
An optional HID node was no longer present at the later preflight; the successful
stream mapped the still-present camera video/USB endpoints without it. Reinspect
actual devices after SDK use/reconnection rather than retaining old node names.
