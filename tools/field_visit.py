"""Plan or run read-only B2 field diagnostics from the external Jetson.

Python 3.8+, standard library. Uses a private, pinned SSH profile. Passwords
are handled by SSH in the operator terminal, never stored or passed in args.
No network configuration, robot requests, model inference or installation.
"""

import argparse
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import platform
import re
import selectors
import shlex
import subprocess
import time


MAX_OUTPUT = 4 * 1024 * 1024
CONFIG_KEYS = {'schema_version', 'ssh_destination', 'known_hosts_file', 'host_key_alias',
               'ros_setup', 'message_setup', 'native_interface', 'domain_id'}


def load_profile(path, project):
    path = Path(path).resolve(strict=True)
    if path.stat().st_mode & 0o077:
        raise ValueError('Private profile must be readable only by its owner (chmod 600)')
    if path.stat().st_size > 16384:
        raise ValueError('Private profile is too large')
    config = json.loads(path.read_text())
    if set(config) != CONFIG_KEYS or config['schema_version'] != 1:
        raise ValueError('Profile keys/schema do not match; never add a password field')
    target = config['ssh_destination']
    user, separator, scoped = target.partition('@')
    address, scope_separator, interface = scoped.partition('%')
    if not separator or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]{0,31}', user):
        raise ValueError('Use an explicit authorized SSH account')
    if not scope_separator or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,64}', interface):
        raise ValueError('Use a scoped onboard IPv6 link-local address')
    if not ipaddress.IPv6Address(address).is_link_local:
        raise ValueError('This diagnostic accepts only the verified directly attached link-local peer')
    alias = config['host_key_alias']
    if not re.fullmatch(r'[0-9A-Fa-f:]+%[A-Za-z0-9_.:-]{1,64}', alias):
        raise ValueError('Invalid pinned host-key alias')
    if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,64}', config['native_interface']):
        raise ValueError('Invalid native robot interface')
    domain = config['domain_id']
    if isinstance(domain, bool) or not isinstance(domain, int) or not 0 <= domain <= 232:
        raise ValueError('Domain must be an integer in 0..232')
    for key in ['ros_setup', 'message_setup']:
        value = config[key]
        if not isinstance(value, str) or not value.startswith('/') or any(c in value for c in '\n\r\0'):
            raise ValueError('Setup paths must be explicit absolute paths')
    keyfile = Path(config['known_hosts_file'])
    if not keyfile.is_absolute():
        keyfile = project / keyfile
    keyfile = keyfile.resolve(strict=True)
    if not keyfile.is_file():
        raise ValueError('Pinned known-hosts file is missing')
    config['known_hosts_file'] = str(keyfile)
    return config


def remote_command(config, stage, seconds):
    arguments = ['--mode', stage, '--interface', config['native_interface'],
                 '--domain-id', str(config['domain_id']), '--message-setup', config['message_setup'],
                 '--seconds', str(seconds)]
    script = ('set -e\nexport PATH=/usr/sbin:/usr/bin:/sbin:/bin:/opt/ros/foxy/bin PYTHONDONTWRITEBYTECODE=1\n'
              'source ' + shlex.quote(config['ros_setup']) + ' 1>&2\nsource '
              + shlex.quote(config['message_setup']) + ' 1>&2\nexec /usr/bin/timeout -k 2s 45s '
              '/usr/bin/python3 - ' + shlex.join(arguments))
    return ['ssh', '-T', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=' + config['known_hosts_file'],
            '-o', 'HostKeyAlias=' + config['host_key_alias'], '-o', 'ForwardAgent=no',
            '-o', 'ConnectTimeout=5', '-o', 'ConnectionAttempts=1',
            '-o', 'NumberOfPasswordPrompts=1', '-o', 'ServerAliveInterval=5',
            '-o', 'ServerAliveCountMax=2', config['ssh_destination'],
            'bash --noprofile --norc -c ' + shlex.quote(script)]


def validate_event(event):
    if not isinstance(event, dict) or event.get('schema_version') != 1:
        raise ValueError('Invalid event schema')
    if event.get('event') not in {'inventory', 'state', 'summary'}:
        raise ValueError('Unknown event type')
    if event['event'] == 'state':
        state = event['state']
        values = [*state['position'], *state['velocity'], *state['rpy'], state['yaw_rate']]
        values += [event['onboard_receipt_monotonic_s']]
        if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in values):
            raise ValueError('Invalid numeric state')
        if [len(state[k]) for k in ['position', 'velocity', 'rpy']] != [3, 3, 3]:
            raise ValueError('Invalid state vector dimensions')
        if state.get('frames_verified') is not False or state.get('source_timestamp_verified') is not False:
            raise ValueError('This diagnostic cannot verify frames or source timestamps')
    elif event.get('actuation_requests_sent') != 0:
        raise ValueError('Read-only event declaration is missing')
    if event['event'] == 'summary':
        counts = event.get('counts', {})
        for key in ['received', 'finite', 'emitted']:
            value = counts.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError('Invalid summary count')
        if not counts['received'] >= counts['finite'] >= counts['emitted']:
            raise ValueError('Inconsistent summary counts')
    return event


def summarize(stage, events, returncode, error=None):
    samples = [e for e in events if e['event'] == 'state']
    summaries = [e for e in events if e['event'] == 'summary']
    inventories = [e for e in events if e['event'] == 'inventory']
    result = {'stage': stage, 'ssh_exit_code': returncode, 'error': error,
              'actuation_requests_sent': 0, 'frames_verified': False,
              'source_timestamp_verified': False, 'model_state_integration': False}
    if stage == 'inventory':
        result['collection_complete'] = not error and returncode == 0 and len(inventories) == 1 and len(events) == 1
        result['probes_needing_followup'] = [] if not inventories else [
            k for k, v in inventories[0]['probes'].items() if v['status'] != 'available']
        result['package_metadata_missing'] = [] if not inventories else [
            k for k, v in inventories[0].get('distribution_versions', {}).items() if v is None]
        result['transport_passed'] = None
    else:
        times = [e['jetson_receipt_monotonic_s'] for e in samples]
        gaps = [b - a for a, b in zip(times, times[1:])]
        result.update(received_samples=len(samples), max_receipt_gap_s=max(gaps) if gaps else None,
                      observed_modes=sorted({e['state'].get('mode') for e in samples
                                             if isinstance(e['state'].get('mode'), int)}),
                      observed_error_codes=sorted({e['state'].get('error_code') for e in samples
                                                   if isinstance(e['state'].get('error_code'), int)}),
                      robot_health_verified=False)
        counts_match = (len(summaries) == 1 and summaries[0]['counts']['emitted'] == len(samples))
        finite_only = counts_match and summaries[0]['counts']['finite'] == summaries[0]['counts']['received']
        ordered = [e['sequence'] for e in samples] == list(range(1, len(samples) + 1))
        event_order = [e['event'] for e in events] == ['state'] * len(samples) + ['summary']
        result['transport_passed'] = bool(not error and returncode == 0 and counts_match
                                          and finite_only and ordered and event_order and len(times) >= 20 and gaps
                                          and 0 <= min(gaps) and max(gaps) <= 0.5
                                          and times[-1] - times[0] >= 2.)
        result['diagnostic_criteria'] = '>=20 finite samples, >=2s span, <=0.5s receipt gap; not control approval'
    return result


def collect(command, payload, output, stage, deadline_s=55.):
    if len(payload) > 32768:
        raise ValueError('Remote source exceeds the bounded stdin payload size')
    events = []
    error = None
    with (output / 'ssh-stderr.log').open('xb') as stderr, (output / 'events.jsonl').open('x') as data:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr)
        selector = selectors.DefaultSelector()
        try:
            process.stdin.write(payload)
            process.stdin.close()
            selector.register(process.stdout, selectors.EVENT_READ)
            end = time.monotonic() + deadline_s
            total = 0
            pending = b''
            while True:
                remaining = end - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('SSH diagnostic deadline exceeded')
                if not selector.select(min(0.2, remaining)):
                    continue
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    if pending:
                        raise ValueError('Truncated JSONL output')
                    break
                total += len(chunk)
                if total > MAX_OUTPUT:
                    raise ValueError('Diagnostic output limit exceeded')
                pending += chunk
                while b'\n' in pending:
                    line, pending = pending.split(b'\n', 1)
                    event = validate_event(json.loads(line))
                    event['jetson_receipt_monotonic_s'] = time.monotonic()
                    events.append(event)
                    data.write(json.dumps(event, allow_nan=False) + '\n')
                    data.flush()
            process.wait(timeout=max(0.1, end - time.monotonic()))
        except (Exception, KeyboardInterrupt) as exc:
            error = type(exc).__name__ + ': ' + str(exc)[:300]
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        finally:
            selector.close()
            process.stdout.close()
            try:
                process.stdin.close()
            except OSError:
                pass
    result = summarize(stage, events, process.returncode, error)
    (output / 'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--stage', choices=['plan', 'inventory', 'state'], default='plan')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--seconds', type=float, default=10.)
    args = parser.parse_args(argv)
    project = Path(__file__).resolve().parents[1]
    config = load_profile(args.config, project)
    if not math.isfinite(args.seconds) or not 1 <= args.seconds <= 15:
        parser.error('Duration must be 1..15 seconds')
    if args.stage == 'plan':
        print('Profile syntax and known-hosts file presence checked. No connection or robot request was made; reachability/authentication are not checked.')
        shell = remote_command(config, 'inventory', args.seconds)[:-1]
        shell[shell.index('-T')] = '-tt'
        print('To open a separate authorized i7 shell, run this command yourself:')
        print(shlex.join(shell))
        return 0
    if platform.system() != 'Linux':
        parser.error('Run active stages in the external Jetson terminal')
    if args.output is None:
        parser.error('Use a new private output directory below project local/')
    output = args.output.resolve()
    try:
        output.relative_to((project / 'local').resolve())
    except ValueError:
        parser.error('Output must remain below project local/')
    if output == (project / 'local').resolve():
        parser.error('Use a new child directory, not local/ itself')
    os.umask(0o077)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    payload = (project / 'tools/inspect_onboard.py').read_bytes()
    (output / 'method.json').write_text(json.dumps({
        'stage': args.stage, 'seconds': args.seconds, 'transport': 'SSH to authorized i7',
        'source_revision': (project / 'local/source-revision.txt').read_text().strip()
        if (project / 'local/source-revision.txt').is_file() else 'not_recorded',
        'actuation_requests_sent': 0, 'payload_sha256': hashlib.sha256(payload).hexdigest(),
        'profile_sha256': hashlib.sha256(args.config.read_bytes()).hexdigest()}, indent=2) + '\n')
    result = collect(remote_command(config, args.stage, args.seconds), payload, output, args.stage)
    print(json.dumps(result, indent=2))
    print('Private results:', output)
    passed = result.get('collection_complete') if args.stage == 'inventory' else result['transport_passed']
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
