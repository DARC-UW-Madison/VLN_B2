# B2 visit checklist

[日本語](field-card.ja.md) · [Executable next-visit procedure](next-visit.md) · [Status](../status.md)

> Document type: **Checklist**. Use the linked procedure for commands and interpretation.

## Bring and connect

- External Jetson and its existing separate power supply; Mac if remote management is needed.
- Existing Anker Ethernet adapter and LAN cable. Start with the attachment already inspected; another connector is not a prerequisite for these diagnostics.
- Powered B2, paired controller, lab operator and the unit-matched handling/stop procedure.
- Working Jetson login and private field profiles. Confirm local recovery if management Wi-Fi fails.

## Execute in order

1. Check the private profile with the default no-connection `plan` stage.
2. Collect i7 versions, routes, bridge membership and readable firewall rules; identify unanswered items.
3. Record ten seconds of state arriving on Jetson; inspect continuity and completion.
4. Compare bridge/routing, an application relay and an identified internal-LAN Ethernet access point. Save a concrete proposal and recovery/acceptance plan.
5. Optionally repeat the built-in camera check or external camera/model demo as separate tests.

All commands, output paths, success conditions and failure actions are in
[next-visit.md](next-visit.md). Keep reports/images private. These diagnostics
send no posture or movement requests. The [development procedure](../reference/development.md)
defines separate physical trials once site, control ownership, override and
stopping have been established.
