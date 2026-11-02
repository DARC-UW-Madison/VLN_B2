"""Check the dedicated Tailscale IPv4 and restrict its RDP ingress before startup.

Run as root through the optional b2-rdp systemd drop-in. This neither enrolls
Tailscale nor changes its access policy, Wi-Fi, SSH, default firewall policy or
existing rules. A single labelled INPUT rule rejects non-Tailscale ingress to
this exact address and TCP port 3389; repeated starts reuse that rule.
"""

import ipaddress
import json
from pathlib import Path
import subprocess


ADDRESS_FILE = Path('/opt/b2-remote/etc/xrdp/tailnet-address')


def run(arguments, check=True):
    return subprocess.run(arguments, check=check, capture_output=True, text=True, timeout=10)


def prepare(address_text, command=run):
    address = ipaddress.ip_address(address_text.strip())
    if address.version != 4 or address not in ipaddress.ip_network('100.64.0.0/10'):
        raise ValueError('Expected the dedicated Tailscale IPv4 address')
    address = str(address)
    current = command(['/usr/bin/tailscale', 'ip', '-4']).stdout.splitlines()
    if current != [address]:
        raise RuntimeError('The enrolled Tailscale address differs from the configured RDP address')
    interfaces = json.loads(command(['/usr/sbin/ip', '-j', '-4', 'address', 'show',
                                     'dev', 'tailscale0']).stdout)
    if not any('UP' in item.get('flags', []) and any(
        value.get('local') == address for value in item.get('addr_info', [])
    ) for item in interfaces):
        raise RuntimeError('The configured address is not ready on tailscale0')
    rule = ['INPUT', '-d', address + '/32', '-p', 'tcp', '--dport', '3389',
            '!', '-i', 'tailscale0', '-m', 'comment', '--comment',
            'b2-rdp-tailnet-only', '-j', 'DROP']
    result = command(['/usr/sbin/iptables', '-w', '5', '-C', *rule], check=False)
    if result.returncode == 1:
        command(['/usr/sbin/iptables', '-w', '5', '-I', 'INPUT', '1', *rule[1:]])
    elif result.returncode != 0:
        raise RuntimeError('Could not verify the dedicated RDP ingress rule')
    print('Tailscale RDP address and ingress restriction are ready')


if __name__ == '__main__':
    prepare(ADDRESS_FILE.read_text())
