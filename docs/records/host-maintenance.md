# Access incidents and host maintenance

[日本語](host-maintenance.ja.md) · [Records](README.md)

> Document type: **Record**. Evidence of performed configuration and checks, separate from current operating procedures.

## Diagnosing access loss and desktop failures

The 2026-11-03 inspection separated three observations rather than treating a
popup, lost connectivity and a desktop freeze as one proven fault:

- Before the operator's restart, persistent syslog recorded repeated eduroam
  association/authentication timeouts. NetworkManager explicitly said stored
  secrets existed, requested new secrets and finally failed with `no-secrets`.
  That final reason alone does not prove the saved password was absent or wrong.
  After restart the same stored profile completed PEAP and connected before the
  desktop login. AP/authentication-service/supplicant responsibility remains
  unresolved. No Wi-Fi credentials, CA checks or retry settings were changed.
- The legacy desktop account was the previously retained autologin target.
  The operator changed it to the research account after restarting; the agent
  did not make that change. Before restart Linux login authentication had
  succeeded, followed by a GNOME FIFO warning and XRDP audio environment values
  in the local desktop launch. Session residue/conflict is a hypothesis, not a
  proven freeze cause. Current local and RDP GUI sessions share one account;
  avoid assuming that a disconnected RDP client has logged that session out.
  No session was terminated, GNOME reset or graphics driver replaced.
- One pending crash report belonged to the project's **intentional readiness
  failure test** on 2026-11-01. An unhandled expected exception had invoked the
  host crash-report mechanism. The helper now catches expected address/file/
  subprocess failures, logs a concise diagnostic and exits 1 for systemd retry.
  Its own identified old test report was archived privately; an unrelated older
  browser report was left alone. Which report the operator's popup displayed
  was not independently observed. The helper failure does not explain Wi-Fi loss.

Journal storage was volatile and held only the current boot. Persistent syslog
and authentication logs supplied partial previous-boot evidence; raw excerpts
stay in ignored `local/access-incident-20261103-01`. The boot clock was corrected
by time synchronization. A Tailscale message describing a large apparent sleep
interval during that correction is not independent proof of physical suspend.
Use monotonic time within a boot and verify time corrections before interpreting
cross-boot wall-clock durations. Both inspected desktop accounts currently had
AC suspend action `nothing`; that does not reconstruct earlier settings.

For a recurrence, preserve current/previous boot availability, NetworkManager/
supplicant messages and login/session state before restarting if possible. Read
crash **metadata** first; do not upload reports, collect browser content or print
network passwords. Check the exact active connection and secret-storage flags
without displaying secrets. Distinguish missing credentials, authentication
failure and failure to obtain an IP. Keep peer identities and raw logs private.
The [upstream XRDP discussion](https://github.com/neutrinolabs/xrdp/issues/2027)
is a related GNOME/FIFO case, not proof that this device has the same cause.
The expected-failure handler and installed-helper check passed, with all 164
ordinary tests passing on Mac and Jetson. Recovery after one restart does not
establish automatic recovery from a future eduroam authentication stall.


A later screen inspection on the same day captured the actual generic
`update-notifier` system-program-problem dialog. The sole remaining crash file
was an older Chrome SIGTRAP report dated 2026-10-28. The dialog itself did not
identify a newly failing component or establish Chrome's detailed crash cause.
No report was uploaded and the browser report was not deleted. At the operator's
request, only the physical research GUI session was logged out after saving the
window evidence. The remote GUI and SSH were preserved; GNOME and an EWMH window
manager then became available on the RDP display. The operator subsequently
confirmed client-side desktop access. Persistent GUI autologin was left unchanged, so this one-time
logout does not prevent console/RDP overlap after a future automatic login.



## Manual updates and desktop notifications

After the notification-only change described below, a separate operator-authorized
maintenance transaction on **2026-11-03** refreshed APT indexes and upgraded
OpenSSH client/server/SFTP from `1:8.2p1-4ubuntu0.12` to `1:8.2p1-4ubuntu0.13`,
and Chrome from `156.0.8078.47-1` to `156.0.8078.79-1`. No additions/removals
or other installed version changes occurred; SSH configuration and service
checks passed. GPU images, JetPack/CUDA and kernel were preserved. Additional
Ubuntu 20.04 fixes can require the lab's ESM entitlement; no subscription was
attached. This is not complete security coverage. See [the maintenance record](milestone-2026-11-03.md#6-maintenance-applied-on-2026-11-03).

The external Jetson deliberately retains Ubuntu 20.04, JetPack 5.1.2 / L4T
35.4.1 and CUDA 11.4 for the measured runtime. Host release/kernel/GPU updates
need a compatibility and recovery plan; a container does not isolate them from
host driver changes. NVIDIA documents coupled BSP packages and the release's
supported update paths in its [35.4.1 update guide](https://docs.nvidia.com/jetson/archives/r35.4.1/DeveloperGuide/text/SD/SoftwarePackagesAndTheUpdateMechanism.html).
This is not a claim that all security updates are unnecessary.

Inspection on 2026-11-03 found release prompting already set to `never`, no
installed unattended-upgrades service, daily package-index refreshing enabled
and no package holds. A simulation using the existing local index proposed
143 upgrades, no additions/removals; no package transaction or fresh index
refresh was executed for this notification change. That cached proposal is not
a current vulnerability audit or a compatibility approval. Cache refresh and
notification are different from automatic package installation.

The installed `update-notifier` 3.192.30.19 launches Update Manager before its
`no-show-notifications` branch. Inspection of the matching
[official Ubuntu source archive](https://ports.ubuntu.com/ubuntu-ports/pool/main/u/update-notifier/update-notifier_3.192.30.19.tar.xz)
showed that changing that GSettings key alone would not suppress automatic
updater windows. Its source archive/hash and selected settings were retained
privately, without modifying the packaged executable.

The operator explicitly selected suppression of **both update and crash-report
GUI notifications**. A research-account-only override at
`~/.config/autostart/update-notifier.desktop` copies the system desktop entry
and sets `Hidden=true`. The running research-account notifier was stopped.
The [XDG autostart specification](https://specifications.freedesktop.org/autostart/latest/)
defines this user-level override. The desktop file validated with only its
inherited deprecated-Encoding warning; no updater GUI process remained. Other
accounts and the system autostart file were unchanged. No background monitor,
Mac setting, package removal or replacement update service was added.

Crash collection, `/var/crash`, journal/syslog and manual analysis remain.
New crash reports will no longer automatically prompt through this notifier in
this research GUI. RDP, Tailscale and Wi-Fi notification/authentication services
are separate. This does not prohibit deliberately launching a manual updater or
running APT. Existing cache-refresh timers remain unchanged.

APT can still be used, as described in [Ubuntu's package guide](https://ubuntu.com/server/docs/how-to/software/package-management/).
`apt update` refreshes the index; it does not upgrade installed software. First
inspect candidates, then simulate and review a **selected** package transaction:

```sh
sudo apt update
apt list --upgradable
sudo apt-get -s install --only-upgrade PACKAGE_NAME
```

Only after reviewing versions, dependencies, restarts and recovery, apply the
selected transaction:

```sh
sudo apt install --only-upgrade PACKAGE_NAME
```

`PACKAGE_NAME` is a placeholder, not a literal command target. Do not substitute
an unreviewed bulk `upgrade`, `full-upgrade`, generic desktop NVIDIA driver or
Ubuntu release upgrade for Jetson maintenance. BSP/CUDA/ROS/ZED changes and
security patches require their own reviewed scope and appropriate checks.
Local GPU images and Python model dependencies are separate versioned artifacts;
updating host APT does not update those images or their pinned model inputs.

Private before/applied/verified records are in `local/update-policy-01`. To undo
this GUI policy, restore the prior user override if one existed, or remove only
the newly created user override and log in again. No previous override existed
on this target. Retain the system file and do not alter crash logs to restore
notification behavior.
