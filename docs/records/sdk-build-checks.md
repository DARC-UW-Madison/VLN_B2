# SDK state-image checks

[日本語](sdk-build-checks.ja.md) · [Records](README.md)

> Document type: **Record**. Evidence of performed configuration and checks, separate from current operating procedures.

## Verified local result

The revised build and offline probe passed on the external Jetson. The image is
`vln-b2-unitree:jp5`, ID
`sha256:4a61fa33e9c016b8cc21829c3b254553e20b75379fcda83ff64592529fe72f1b`.
The verifier checked 202 Python source files, the dedicated loaded native library
and a 516-byte synthetic SportModeState serialization round trip. It created no
DDS entities or robot client. Build attempt 02 and `local/unitree-check-01` retain
the exact invocations, reports and successful exit codes. This is software
readiness for a receive test, not an actual B2 connection result.
