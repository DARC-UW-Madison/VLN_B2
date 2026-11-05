# Building and commissioning the isolated RDP server

[日本語](rdp-build.ja.md) · [Documentation](../README.md) · [Remote desktop concepts](../how-to/remote-desktop.md)

> Document type: **Record**. Commands and measurements describe the recorded environment; use the how-to guides for current operation.

The listener settings below describe initial loopback-only commissioning.
On 2026-11-01 the operator requested direct tailnet RDP; the controlled bind,
startup/ingress guard and verification are in [the desktop guide](../how-to/remote-desktop.md).
The existing binary/TLS/login backend was retained; no rebuild was needed.

## Why this build exists

The inspected Ubuntu Focal repository offers xrdp `0.9.12-1ubuntu0.1`.
[USN-8476-1](https://ubuntu.com/security/notices/USN-8476-1) identifies fixes in
an ESM revision not available in that candidate. Installing the ordinary old
package would not meet the reviewed update condition. No Ubuntu Pro enrollment,
OS upgrade or graphics-driver replacement is part of this work.

The candidate recipe [remote-desktop.Dockerfile](../../deploy/remote-desktop.Dockerfile)
builds newer upstream software in a matching L4T container. It produces files
for an explicitly reviewed host installation; it is not a desktop running inside
the model container. Keep build, export, host installation, server startup and
successful graphical login as five separate evidence claims.

## Fixed inputs and output boundaries

| Input | Fixed revision | Purpose |
|---|---|---|
| L4T 35.4.1 base | Digest in the Dockerfile, shared with the verified runtime recipe | Matching ARM64/Focal build userspace |
| xrdp 0.10.6.1 | `80c52879fead585d6347df5b3c587718adf8f5a5` | RDP listener and session manager |
| xorgxrdp 0.10.5 | `c2d3cbafebe00be3221f985c06ef6b97f1c63790` | Additional modules for the existing Xorg server |
| Check 0.15.2 | `11970a7e112dfe243a2e68773f014687df2900e8` | Build-time test framework only; absent from exported runtime |

The [xrdp release](https://github.com/neutrinolabs/xrdp/releases/tag/v0.10.6.1)
and [xorgxrdp release](https://github.com/neutrinolabs/xorgxrdp/releases/tag/v0.10.5)
provide the upstream release context. Full Git revisions and submodule gitlinks
are checked. Additional source-archive SHA256 values are recorded after checkout;
those are provenance records, not independently preapproved release checksums.
APT package versions are recorded but not fully locked, so the recipe is not a
claim of bit-for-bit reproducible builds.

Both configure invocations use strict locations. Prefix alone is insufficient:
upstream may otherwise select system `/etc` and Xorg module directories. The
staged output is `/opt/output/opt/b2-remote`, plus the explicitly staged PAM
file `/opt/output/etc/pam.d/xrdp-sesman`. The bundle includes binaries, libraries,
Xorg modules, configuration/unit templates, notices and build/test/link metadata.
It contains neither a replacement Xorg/GDM/NVIDIA driver nor generated private
keys. Host networking, Wi-Fi secrets and service activation are not build inputs.

The candidate retains the CPU painter/RemoteFX libraries required by upstream
tests. It disables optional GPU desktop rendering, xorgxrdp SIMD, audio, drive
forwarding, smartcard and H264/JPEG codec integrations. Basic settings access is the
initial goal. Reduced features do not themselves prove compatibility, performance
or that every required runtime library is present on the host.

## Build and export procedure

On the prepared Jetson, from a reviewed source revision, the canonical build is:

```sh
sudo env DOCKER_BUILDKIT=0 docker build --pull=false --target bundle \
  --build-arg MAX_JOBS=4 --tag vln-b2-rdp-bundle:jp5 \
  --file deploy/remote-desktop.Dockerfile .
```

`MAX_JOBS=4` bounds compiler parallelism; it is unrelated to model training.
Development packages are installed only in the builder. The expensive GPU Torch
image is neither rebuilt nor replaced. `make check` remains mandatory for xrdp;
unknown configure-option warnings and missing executable libraries fail the build.
The final scratch stage has no shell, default command or listening service.

To export into a new, unused local directory, create a container without starting
it and copy its artifact tree. First verify that both the container name and
output path below are unused:

```sh
mkdir -p local/rdp-export-01
sudo docker create --name b2-rdp-export-01 vln-b2-rdp-bundle:jp5 /not-started
sudo docker cp b2-rdp-export-01:/opt/output local/rdp-export-01/
```

The command name `/not-started` is deliberately never executed. Do not start this
artifact container. Preserve its image ID, recipe SHA256, logs, source revisions,
unit tests and file manifest. A bundle export is not permission to redistribute
its dependencies; keep component notices and review recipients separately.

## Recorded build recovery

The first attempt compiled xrdp itself but stopped while compiling its tests:
Focal's Check 0.10 lacks assertion APIs used by the pinned upstream test source.
The correction builds Check 0.15.2 in the builder and selects its pkg-config file.
It leaves upstream tests intact rather than deleting assertions or skipping them.
Check's LGPL terms remain applicable to the build dependency; its library/test
executables are not included in the exported runtime. Initial logs and failed
containers are retained for diagnosis. A later successful result must be
recorded explicitly; describing the correction alone is not a passed build.

## Host installation preflight

Do not extract over existing installations blindly. Before changing the host:

1. Confirm `/opt/b2-remote`, the selected PAM file, service/unit names and service
   account/group names are absent, or identify their owner and preservation plan.
2. Verify the bundle's file hashes and that it contains no keys or unexpected
   paths. Preserve its source notices and metadata. Check root-owned installation
   paths and prevent ordinary users modifying binaries or authentication config.
3. Run host-side linking checks after staging, and compare the module's Xorg ABI
   with the installed server. Build-time `ldd` is not a host linking result.
4. Keep a working independent management connection. On 2026-10-28 direct LAN
   OpenSSH was established before Tailscale was updated; client and daemon
   1.104.4 and a temporary Tailscale TCP forward then passed.
5. Preserve existing NoMachine, GDM, local sessions and the GPU runtime. Do not
   log a user out to make a test pass without reviewing that session's work.

The intended installation adds only the dedicated prefix, a non-login service
account/group when absent, an allow group for approved researchers, the reviewed
PAM entry and dedicated unit files. TLS keys are generated on the host and are
never transferred into the repository/image. Exact applied configuration,
backups and verification results belong in the installation record.

## Required configuration before the first start

| Area | Required behavior |
|---|---|
| Listener | In xrdp's Globals section, bind only `tcp://127.0.0.1:3389`; inspect the actual socket after starting |
| Transport | TLS with a fresh host certificate/key; root ownership and only the service's required read permission |
| Privilege | Dedicated non-login `xrdp` service identity for the listener; session manager retains only its required root role |
| Login policy | Root login disabled; intended researcher allow group; ordinary PAM authentication retained |
| Runtime sockets | Matching `runtime_group` and `SessionSockdirGroup`; the latter is in sesman Security, according to this pinned parser |
| Xorg | Existing host executable, absolute prefix-owned config and prefix modules plus the existing system module path |
| Lifecycle | Dedicated unit names, matching dependencies, manual initial startup; no automatic boot enablement during first commissioning |
| Redirection | Only needed channels enabled; no automatic home-directory sharing |

Use the fixed-version [xrdp config](https://raw.githubusercontent.com/neutrinolabs/xrdp/v0.10.6.1/xrdp/xrdp.ini.in),
[sesman parser](https://raw.githubusercontent.com/neutrinolabs/xrdp/v0.10.6.1/sesman/libsesman/sesman_config.c)
and [privilege guide](https://github.com/neutrinolabs/xrdp/wiki/Running-the-xrdp-process-as-non-root).
Some helper code expects the group name `xrdp`; do not assume arbitrary group
renaming works. Check `xrdp-chkpriv`, paths, service logs and actual privileges.
Do not weaken polkit globally or replace a graphics driver to bypass a failure.

## Acceptance and rollback

First prove linking, unit syntax, restrictive sockets, TLS identity and session
manager health. Then test Mac's Windows App through the reviewed SSH tunnel.
A currently logged-in research console session can conflict with an RDP session
for the same user; listener readiness is not a completed GUI login. Test desktop
login, settings permission, keyboard, reconnect and HDMI-disconnected boot as
listed in the remote-desktop guide. Verify existing SSH, local GUI and CUDA
separately. No robot motion belongs in these tests.

If a new service fails, stop only those dedicated units and preserve logs.
Disable them if explicitly enabled later. Restore only the configuration changes
made for this installation, preserving existing services/data. The prefix and
added unit/PAM files can be archived with their manifest; review account/group
membership before removing anything. Do not use broad Docker pruning, desktop
reinstallation or credential deletion as rollback.

## Installation and checks recorded on 2026-10-28

The corrected bundle built successfully as
`sha256:15f5a046721dd9d3e2cca7fb71c411203a6ac1b9eab71a0e94ddc52d7d62e993`,
logical image size **19,594,974 bytes**. Its recipe SHA256 is
`e19bf5e283c46c5661e662b313ef52fb6b1bc177bbdb3b92d1fd2a0fbda8a787`.
All **213 reported upstream tests passed**, with zero skips/failures/errors.
Two failed attempts were retained: the older Check assertion API, then disabled
painter/RemoteFX libraries that the upstream test Makefile requires. The final
recipe enables both software libraries and keeps GPU rendering/H264 disabled.
They add no CUDA dependency. No assertions or tests were removed.

The export's 162 manifest entries were checked before installation. The host
then received `/opt/b2-remote`, non-login `xrdp:xrdp`, allow group
`b2-remote-users` containing the intended research login, the upstream Debian PAM
file and dedicated units `/etc/systemd/system/b2-rdp.service` and
`b2-rdp-sesman.service`. Defaults were preserved as
`xrdp.ini.before-b2-setup` and `sesman.ini.before-b2-setup` inside the prefix.
Existing system Xorg, GDM, NoMachine, Wi-Fi profiles and GPU image were retained.

In addition to the configuration table above, applied values include:

| File/section | Applied setting |
|---|---|
| xrdp.ini Globals | `allow_channels=false`; TLS 1.2/1.3; explicit prefix certificate/key paths |
| sesman.ini Globals | `EnableUserWindowManager=false`; absolute prefix `startwm.sh` |
| sesman.ini Security | `MaxLoginRetry=3`; `TerminalServerUsers=b2-remote-users`; `TerminalServerAdmins=xrdp`; `AlwaysGroupCheck=true`; both clipboard restrictions `all` |
| sesman.ini Sessions | `MaxSessions=2` |
| Xorg parameters | `/usr/lib/xorg/Xorg`; module path `/opt/b2-remote/lib/xorg/modules,/usr/lib/xorg/modules`; absolute prefix config; `-noreset -nolisten tcp`; per-display local log |
| Logs | `/opt/b2-remote/var/log/xrdp.log` writable by service identity; `xrdp-sesman.log` root-owned |
| Units | Upstream Type=exec templates with matching dedicated dependencies; sesman owns runtime directory `b2-remote` mode 0755 |
| Keys | Fresh host-generated TLS certificate/key and RSA key file; root:xrdp 0640; no private key copied to Mac or Git |

Host linking passed for 13 executables. Unit verification and `xrdp-chkpriv`
passed; verification also printed warnings about pre-existing unrelated units,
which were not modified. Both RDP units were initially started manually. After the operator confirmed
basic desktop interaction, `b2-rdp.service` was enabled at boot; sesman remains
a required dependency rather than an independently enabled unit. Enablement,
active states and the loopback listener were checked without restarting. The actual listener was **127.0.0.1:3389 only**, the listener process
ran as xrdp:xrdp, and sesman ran as root. Through a temporary SSH tunnel, RDP
selected TLS and a client trusting the separately obtained public certificate
verified TLS 1.3 (`TLS_AES_256_GCM_SHA384`). That test tunnel was stopped.

An isolated authenticated Xorg display answered `xdpyinfo` at 1024×768 and was
stopped afterward. Following the operator's response and a normal logout with no
GNOME inhibitors, Windows App authenticated and displayed the GNOME desktop.
Credentials were not saved. The eight model-free FP32/BF16 GPU operations passed
again after installation. No robot was connected or commanded.

Basic desktop interaction was confirmed by the operator. Settings permission,
extended input checks, disconnect/reconnect and cold boot still require
acceptance evidence. An inherited Chrome crash dialog was visible; no
problem report was sent and its cause was not established. Do not claim a complete
GUI/boot acceptance from a visible background alone. Raw build/install/probe
records remain under ignored `local/remote-desktop-build`, `local/rdp-export-01`
and `local/access-setup` on Jetson; they include machine-local information and
are not public source.

A later controlled software reboot with HDMI disconnected restored the current
non-enterprise Wi-Fi, Tailscale, SSH, both RDP services and Docker; the SSD mount
and SSD Docker data root were verified. The operator then confirmed RDP display
and input through the restored dedicated background Mac tunnel. This was not a
physical power cycle or an eduroam boot test.

The subsequent eduroam credential save, timed-rollback switch and second
headless software reboot also passed. Fresh SSH worked at about 24 seconds of
target uptime; a changed boot ID, automatic eduroam connection, Internet access,
management services, SSD mount and Docker data root were verified. The operator
confirmed Windows App display/input after the Mac tunnel was restarted. No
physical power cycle or GUI autologin change was performed.

The earlier commissioning table records clipboard-disabled defaults. On
2026-11-03 the operator requested usable copy/paste; the host configuration was
changed to text-only bidirectional `cliprdr`, with other channels blocked. See
[the current clipboard and editor procedure](../how-to/remote-desktop.md). Existing GUI
sessions were retained; new-session/client transfer confirmation is pending.
