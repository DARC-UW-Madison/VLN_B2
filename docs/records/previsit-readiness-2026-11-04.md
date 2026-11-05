# Pre-visit readiness review, 2026-11-04

[日本語](previsit-readiness-2026-11-04.ja.md) · [Records](README.md) · [Next-visit procedure](../how-to/next-visit.md)

> Document type: **Record**. Scope: repository/documentation review, external-Jetson runtime checks, and preparation of read-only field diagnostics. B2 remained off and was not contacted.

## Findings and changes

| Finding | Change and reason |
|---|---|
| Existing field card mixed general connection setup with this unit's next visit | Replace it with a short checklist and a separate executable procedure using the existing USB/Anker attachment |
| The documentation index contained an isolated table row | Repair both languages and recheck rendered structure/navigation |
| Missing i7 SDK/library/filter facts still depended on ad hoc commands | Add a bounded inventory payload; report missing permissions/metadata explicitly rather than infer versions |
| Previous state checks did not establish a stream delivered to Jetson | Add JSONL capture with Jetson receipt times, completeness/count checks and continuity diagnostics |

The new `field_visit.py` runs a standard-library Python payload through pinned
SSH, and `inspect_onboard.py` contains only inventory/state subscriptions. It
creates no command publisher or robot client. It reads firewall rules with
noninteractive sudo; denied reads remain unresolved. State recording can identify
actually mapped DDS binary files/hashes but does not certify their source version.
No bridge, routes, firewall rules, system services, packages or robot firmware
were changed. Two private profiles were prepared on Jetson for previously
verified i7 link-local endpoints; neither contains a password.

## Checks completed before the visit

| Check | Result and interpretation |
|---|---|
| Published Git references | Refreshed; published main was already incorporated; the field work branch is separate |
| External Jetson access/storage | SSH worked; Tailscale/RDP services active; available root/SSD capacity checked |
| Camera/model preflight | Existing paths, checkpoint digest, image and ZED device mapping passed |
| Actual bounded camera/model run | 20 camera JPEGs; one prediction with 30 finite XY points; load 11.362 s, inference 12.640 s |
| Runtime cleanup | Camera/model container exits both 0, no cleanup errors; no movement sent |
| SDK/DDS image | Synthetic import/serialization verifier passed in an explicitly network-disabled, read-only container |
| Local software tests | 201 passed, including malformed/truncated output, timeout, zero samples, gaps, batching, key/profile scope and metadata permissions |
| Target tests and prepared profile plan | Pending synchronization of the new tools; completion is recorded in the follow-up below |

The fresh model trial used assumed stationary state and did not evaluate
navigation accuracy or continuous control. It ran the existing reviewed GPU
image. Private evidence is under `local/previsit-camera-check-01` and
`local/previsit-sdk-check-01` on Jetson; images and generated text were not
copied to Mac. The SDK verifier reports its own isolation flag as unverified;
isolation is established by the recorded Docker invocation with `--network none`,
not by the Python verifier alone.

## What remains onsite

The new tools have not been executed against B2. The visit must verify i7
access, installed/runtime versions and rules, followed by actual continuous
state delivery. The recording's axes, source clocks and image pairing remain
unverified. Direct external DDS, a bridge/router configuration, an application
relay, actual-state model integration and physical feedback/stopping are not
commissioned by this review.

Proceed with [the next-visit procedure](../how-to/next-visit.md), saving the
failed checks as evidence as well as successes. A readable report or passing
synthetic test is not acceptance of an untested physical path.
