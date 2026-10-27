# Jetson account, Tailscale SSH, and isolated workspaces

[日本語](jetson-bootstrap.ja.md) · [Network design](network-topology.md) · [Home](../README.md)

This is an operator-run procedure for an Ubuntu/systemd Jetson with internet
access and a current administrator login. The operator has completed bootstrap,
and subsequent SSH inspection is independently verified in the
[target baseline](target-baseline.md). Account/installation commands below are
reference instructions, not a request to recreate the existing login. Keep its
directly attached display and keyboard available during setup. Account names, passwords, authentication URLs, tailnet identities, and
actual addresses belong in approved local storage, not this repository.

## 1. Create a new host login

Replace every `RESEARCH_USER` below with the approved account name. From the
Jetson's existing administrator session, create only if both the account and
its intended home are absent:

```sh
if getent passwd RESEARCH_USER >/dev/null || [ -e /home/RESEARCH_USER ] || [ -L /home/RESEARCH_USER ]; then
    echo "Account or home already exists; stop and inspect before continuing."
else
    sudo adduser RESEARCH_USER && sudo usermod -aG sudo RESEARCH_USER
fi
```

If the account/home exists, stop; reusing it would not create a fresh workspace.
The initial sudo prompt needs the current administrator's password. The later
password prompts set the new login's password interactively; do not put it in a
command or script. Leave optional personal-information fields blank. If site
password policy rejects a value, inspect the error without weakening global
policy. The sudo membership permits host administration; it is not a security
sandbox. See [Ubuntu user management](https://ubuntu.com/server/docs/how-to/security/user-management/).

After successful creation:

```sh
sudo -iu RESEARCH_USER
whoami
pwd
```

Verify the new login and home before creating project files. Existing accounts
and their files remain in place. Do not copy an old user's entire home or shell
configuration into the new workspace.

## 2. Inspect existing Tailscale state

Run on the Jetson host, not in an application container:

```sh
command -v tailscale
```

If installed, inspect `tailscale status` locally before making changes. A new
Linux user does not create a separate Tailscale enrollment. If the host already
belongs to a tailnet or serves other people, establish its intended enrollment
and existing settings first; do not log it out, reset it, or replace its identity.

For a fresh host without Tailscale, the official Linux installer is:

```sh
curl -fsSL https://tailscale.com/install.sh | sh
```

If curl is absent, install only that prerequisite with `sudo apt update` and
`sudo apt install curl`, then retry. The installer changes shared host packages
and installs a system service; it is not isolated inside the new home. A manual
package-repository installation is also available in the
[official Linux guide](https://tailscale.com/docs/install/linux).

## 3. Enroll the host and enable Tailscale SSH

For the fresh installation, run on the Jetson:

```sh
sudo systemctl enable --now tailscaled
sudo tailscale up
```

Open the authentication URL yourself and join the lab-approved tailnet used by
the Mac. Do not send the login URL or an authentication key into a chat or commit
it. After enrollment:

```sh
sudo tailscale set --ssh
tailscale ip -4
```

This selects **Tailscale SSH**: tailnet identity and policy authorize the SSH
connection. The local Linux password remains relevant to local login and sudo.
The feature serves the host's Tailscale address; an additional OpenSSH server is
not required for this path. Tailnet policy must allow both network access and
SSH access to the intended Linux account. If denied, have the tailnet administrator
review the specific rule; do not replace a shared policy with an allow-all rule.
See [Tailscale SSH](https://tailscale.com/docs/features/tailscale-ssh).

Do not enable subnet advertisement or an exit node for this management path.
Reaching the Jetson itself is sufficient; robot Ethernet is a separate connection.

## 4. Connect from Mac

Reuse an existing Tailscale installation if present. Connect the Mac to the same
approved tailnet, then run in its terminal, replacing both placeholders:

```sh
ssh RESEARCH_USER@JETSON_TAILSCALE_IP
```

A browser identity check may be requested. In the resulting remote Jetson shell:

```sh
whoami
pwd
cat /etc/nv_tegra_release
```

Confirm that the login/home belong to the new account. No SSH connection to the
robot or its onboard Jetson is involved. Keep actual device status and addresses
outside public docs.

## 5. Separate project files and dependencies

| Layer | What it separates | Boundary |
|---|---|---|
| Host login | Home, shell settings and credentials | Same OS and system packages; sudo can administer the host |
| pyenv | Python interpreter versions for that user | Not package isolation, not GPU-driver isolation |
| Project `.venv` | Python packages for one project | Uses a selected interpreter; does not isolate OS libraries |
| Docker image/container | Application packages and process environment | Shares the host kernel and explicitly exposed files/devices/network |

Use `~/Developer/Projects/Robotics/b2/b2-tic-vla` for the project in the new home.
Transfer source files rather than an existing virtual environment. Keep pyenv
per-user when needed and select Python per project; use `.venv` for host tools.
Do not choose the newest Python before checking vendor binding and PyTorch
compatibility. Do not install project packages using `sudo pip` or replace system
Python. Start from [pyenv's description](https://github.com/pyenv/pyenv),
[Python virtual environments](https://docs.python.org/3/library/venv.html), and
[Docker's container model](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/).

For inference, prefer a compatible container to package the runtime. A Python
interpreter already inside the image generally does not need another pyenv layer.
Mount only the needed project/data paths, not another user's entire home. Driver,
JetPack and device access still require host compatibility. First diagnose SDK
state reception on the host when B2 is connected, then test the selected container.

## 6. Make graphical login optional after remote access works

CLI development and the current observation tools do not require a Jetson desktop
session. Leave the desktop installed during initial setup. Before changing boot
mode, verify remote login, boot-time Wi-Fi connectivity, and automatic tailscaled
startup; some Wi-Fi profiles depend on a user's graphical session.

Record the current target locally using `systemctl get-default`. Once unattended
network access is verified, CLI boot can be selected with:

```sh
sudo systemctl set-default multi-user.target
```

This changes the next boot target, not the current desktop session. If the prior
target was graphical and that environment remains installed, it can be restored
with `sudo systemctl set-default graphical.target`. No reboot or desktop removal
is part of the initial account/Tailscale procedure.
