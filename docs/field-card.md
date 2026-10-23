# First visit: field card

[日本語](field-card.ja.md) · [Detailed steps and troubleshooting](onsite.md)

Bring a copy of this project to the Jetson and open a terminal in its root.
No SSH or GitHub URL is needed. These commands send no motor commands.

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
   PYTHONPATH=src timeout -k 5s 15s python3 -m b2_tic_vla state --interface IFACE --seconds 3 --output local/state-01.json
   ```

   Check valid counts and active topic. Received fields do not verify frame conventions.

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
