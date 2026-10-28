# First visit: field card

[日本語](field-card.ja.md) · [Detailed steps and troubleshooting](onsite.md)

Bring a copy of this project to the Jetson and open a terminal in its root.
No SSH or GitHub URL is needed. These commands send no motor commands.

On the prepared external Jetson, the source is already present. Activate its
host venv before the project commands below; system Python remains 3.8. This
venv does not yet supply camera/Unitree dependencies. For the onsite boot and
personal-credential checks, use [the system guide](system-overview.md#personal-credentials-sharing-and-return).

```sh
cd ~/Developer/Projects/Robotics/b2/VLN_B2
source .venv/bin/activate
python3 --version
```

## Visit agenda

Follow [the Ethernet/onboard procedure](field-network.md) in this order:

1. Confirm local recovery and the existing B2 remote-controller positioning,
   takeover and stop procedure; verify priority over future SDK commands.
2. Save the external host's current interfaces/routes before plugging Ethernet.
3. Identify the B2 port, documented subnet, unused client IP and DDS domain;
   establish the link while preserving management, then verify route and reachability.
4. Receive B2 state without motor commands; identify accessible onboard computers,
   actual services and control ownership using authorized lab access.
5. Attach the external ZED 2i by USB; map built-in camera/sensor exports and
   Mid-360 wiring separately. Built-in USB access from this Jetson is unavailable.
6. Complete boot/credential tests; validate Windows App/RDP with and without
   HDMI. With no separate AP available, inspect/test a Jetson hotspot and direct
   local SSH with recovery access; then test offline process lifetime without Mac.
7. Record axes/timestamps, sensor origins, remaining dependencies and next action.
   Motion, operator-link-loss behavior and physical stopping require later validation.

These steps are prepared, not already completed. SDK/camera bindings are still
required before the probes below. Keep private values/results in `local/`.

## Observation probes

1. **Inspect the existing installation** — Python 3.8+, no extra dependencies:

   ```sh
   python3 tools/inspect_target.py --output local/target-inventory.json
   ```

2. **Check one camera image** — requires Python 3.10+, working ZED SDK and `pyzed.sl`:

   ```sh
   PYTHONPATH=src timeout -k 5s 30s python3 -m b2_tic_vla camera --output local/camera-01/frame.jpg
   ```

   Open the JPEG locally and check its actual forward view and mounting.

3. **Check B2 state** — requires SDK2/DDS. Replace `IFACE` with the actual wired interface:

   ```sh
   PYTHONPATH=src timeout -k 5s 15s python3 -m b2_tic_vla state --interface IFACE --domain-id DOMAIN_ID --seconds 3 --output local/state-01.json
   ```

   Replace `DOMAIN_ID` with the verified lab value. Check valid counts and active
   topic. DDS discovery/subscription traffic is sent, but no motor request.
   Received fields do not verify frame conventions.

4. **Keep the results locally** — copy `examples/onsite-notes.json` into `local/` and
   record the existing manual control/stop procedure, command-loss behavior,
   coordinate conventions, and camera mounting/time information. Unknown stays null.
   Use the [detailed checklist](onsite.md#3-record-only-the-facts-requiring-physical-access).

If a dependency is missing, keep the inventory and follow the matching setup
instructions before retrying. Do not replace system Python, flash the Jetson, or
copy Go2-W SDK patches just to make a command run. Choose a new numbered output
for every attempt; files are not overwritten.

After the two probes work, use [paired recording and offline inference](onsite.md#4-save-a-paired-observation).
Live asynchronous inference and motor integration remain separate work. Raw
reports and recordings stay in ignored `local/`; review before sharing.
