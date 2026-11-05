# Camera/path demo checks

[日本語](camera-demo-checks.ja.md) · [Records](README.md)

> Document type: **Record**. Evidence of performed configuration and checks, separate from current operating procedures.

## 9. Recorded acceptance on the prepared Jetson

Source `9fe752c`, the existing reference GPU image and approved local assets
completed a real-camera run on 2026-11-03. The producer captured **60/60 frames**
at its one-image/s target. The model loaded **once in 11.235 s** and completed
**five predictions**, all with 30 points, using frames 13, 26, 36, 46 and 57.
Inference took **12.617, 10.435, 10.243, 11.034 and 10.446 seconds**. Each report
retains its exact input image/digest and a standalone HTML display.

Both containers exited 0, the supervisor reported `finished`, cleanup errors
were empty and no run container remained. The final display was rendered and
visually inspected. **177 tests passed on Mac and Jetson**. This verifies the
prepared workflow, not correct navigation or a paper-level reproduction. No
operator camera-reorientation experiment was recorded during that automated
check; perform the visual comparison in section 5 yourself.

A separate Ctrl+C test during an active run reported `stopped_by_operator`,
empty cleanup errors, no remaining containers and no refresh tag in the final
page. Container exit 137 in that interruption test reflects intentional forced
removal, not successful prediction completion or a diagnosed model crash.

The operator confirmed camera-image and predicted-path display on 2026-11-03,
and then reported attaching the powered B2. This confirms the viewer workflow,
not navigation quality, camera-motion compensation or real-state integration.
See [current first-connection findings](../status.md).
