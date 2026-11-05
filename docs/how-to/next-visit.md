# Next B2 visit: collect facts and receive state on Jetson

[日本語](next-visit.ja.md) · [Documentation](../README.md) · [Mechanisms](../explanations/network-topology.md)

> Document type: **Procedure**. Goal: inspect the existing i7 setup and record its robot-state stream on the external Jetson. No posture or movement request is sent. Preparation results are in [the readiness record](../records/previsit-readiness-2026-11-04.md).

## 1. Start from the existing attachment

Use the existing B2 USB-C → Anker Ethernet adapter → LAN cable → external Jetson
connection. Power B2 and keep the external Jetson on its current separate supply.
This procedure does not require finding or buying another adapter first.
Have the paired remote and lab operator present. Leave the robot in its existing
resting state. Do not invoke a motion example.

All commands below run in a terminal **on the external Jetson**. Mac SSH or the
Jetson desktop can provide that terminal. Mac is not the robot-state producer.
A profile is a saved JSON connection configuration. A pinned host key identifies
the trusted SSH server. The private profiles were prepared from the previously verified i7 endpoint and
host key; they contain no password. Check their presence before the visit:

```sh
cd ~/Developer/Projects/Robotics/b2/VLN_B2
python3 tools/field_visit.py --config local/field-connection.json
```

The default `plan` stage checks profile syntax and the pinned-host file's
presence. It makes no connection and does not establish reachability. Profile
permissions must be 600. It specifies an authorized account, scoped IPv6 peer,
pinned host-key alias, two existing ROS setup paths, native interface and DDS
domain. Keep those identifiers private. The general profile schema is defined
by `CONFIG_KEYS` in the [tool](../../tools/field_visit.py).

## 2. Save the i7 software, routes and filters

```sh
python3 tools/field_visit.py --config local/field-connection.json \
  --stage inventory --output local/next-visit-01-inventory
```

SSH asks for the onboard Linux account password in your terminal if required.
It is not the external Jetson password or the university Wi-Fi password. Do not
put it in a command, JSON profile, chat or Git. Host-key mismatch is a stop:
check the device and trusted key rather than disabling verification.

The command loads the existing ROS/message environment in a child shell, runs
system Python on the i7, then exits. It installs no file or software there.
It collects package metadata and module origins, addresses/routes, bridge
membership, forwarding settings, message-source revision and available firewall
rules. Firewall reads use `sudo -n`; they cannot ask for or save a sudo password.
A denied read is saved as `permission_required`. Missing distribution metadata
can indicate a source installation and is not proof that the SDK is absent.

The new directory contains:

| File | Meaning |
|---|---|
| `method.json` | Source revision, remote-code/profile hashes and stage |
| `events.jsonl` | Private inventory returned by the i7, wrapped with Jetson receipt time |
| `ssh-stderr.log` | Private authentication/workspace diagnostics |
| `summary.json` | Collection outcome and probes requiring follow-up |

`collection_complete: true` means the report was received intact. Review
`probes_needing_followup`, `package_metadata_missing` and the inventory itself;
it does not mean every software version or firewall rule is known. Read-only
privileged inspection may still be needed onsite. The `plan` output prints a
complete pinned SSH command for opening an i7 shell. Run that printed command
in the external Jetson terminal and authenticate. In the resulting **i7 shell**,
these commands show the IPv4/IPv6 rules without changing them:

```sh
sudo iptables-save
sudo ip6tables-save
```

Read and record the output privately, then run `exit` to return to the Jetson
shell. If access is denied or the command is absent, record
it as unresolved. Do not install tools, flush rules or grant new privileges as
part of this procedure. Confirm the configured internal interface/domain against
the inventory before state capture.

## 3. Record a ten-second stream on Jetson

```sh
python3 tools/field_visit.py --config local/field-connection.json \
  --stage state --seconds 10 --output local/next-visit-01-state
```

The i7 subscribes only to `/lf/sportmodestate` and flushes each state record to
SSH stdout. Jetson reads the stream while it arrives, adds its local receipt
time, and saves JSONL: one JSON record per line. This is not a batch report copied after capture and is
not direct Jetson DDS participation. The i7 process is bounded to 45 seconds;
the caller has its own 55-second deadline. Ctrl+C terminates this diagnostic.
No node, relay or autostart service is left intentionally running.

Read the printed summary and `summary.json`. The diagnostic requires at least
20 finite state samples (numbers other than NaN/infinity) spanning at least two seconds, no receipt gap above
0.5 seconds, a matching final count and clean SSH completion. These thresholds
check continuity for this visit; they are **not approved control-loop limits**.
A nonzero exit or `transport_passed: false` leaves the path unaccepted.
The state report also identifies actually mapped DDS libraries by file/hash
where available; that alone does not establish a source version.

Position, velocity, attitude, mode and error fields remain raw reported values.
Their frames and robot source clock are explicitly unverified. Jetson receipt
time and i7 receipt time are separate monotonic clocks, used for elapsed time without wall-clock adjustment: do not subtract them to
claim one-way latency. This data is not yet an accepted model-input recording.

Use a new output name on every repeat. Existing directories are refused rather
than overwritten.

## 4. If the check fails

| Observation | Next action |
|---|---|
| Missing profile/pin | Restore the private prepared files; do not invent addresses |
| Primary SSH address times out | Check B2 power, cable and Jetson Ethernet carrier. Then select the separately prepared alternate profile below |
| Authentication fails or host key changes | Confirm lab credentials/device identity; do not keep retrying or bypass key checks |
| Missing ROS workspace/module | Inspect `ssh-stderr.log` and inventory; do not use conda Python or reinstall ROS automatically |
| Zero state / missing final summary | Recheck the i7-native interface, domain, publisher and errors |
| Large gaps or all samples arrive in a burst | Preserve the record; investigate scheduling/network delivery before model integration |
| Firewall reads denied | Complete authorized read-only inspection; mark bridge/routing feasibility unresolved |

The alternate profile is for another previously verified link-local address of
the same i7 with the same pinned key. Use it only after the primary address has
timed out, with a fresh output directory:

```sh
python3 tools/field_visit.py --config local/field-connection-alternate.json \
  --stage inventory --output local/next-visit-02-inventory
```

## 5. Finish with a concrete network decision

Use the inventory to determine whether the current USB/internal interfaces
could be bridged or routed while preserving management and existing robot
services. Compare that with an application relay and, if physically identified,
an Ethernet connection already attached to the internal LAN. A working SSH
stream does not settle that choice or authorize network changes.

Save the chosen proposal with the required interface/address/filter changes,
recovery path and a repeatable receive-only acceptance test. Make no bridge,
route or firewall changes in this diagnostic procedure. Then the next separate
work is state/image time and frame validation, followed by command-free model
integration. Posture/translation and physical stopping require their own site
and test procedure.

For an optional built-in camera check, use [the sensor procedure](built-in-sensors.md).
For the external camera/model demonstration, use [the short demo](live-camera-demo.md).
Do not replace this state test with either demo: they answer different questions.
