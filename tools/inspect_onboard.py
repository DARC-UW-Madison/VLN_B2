"""Read-only onboard inventory or bounded ROS state stream; Python 3.8+.

No publisher, robot request, service/network configuration, installation or
filesystem output. Stdout is JSONL; the external caller saves private evidence.
"""

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time


def emit(value):
    print(json.dumps(value, allow_nan=False), flush=True)


def command(argv):
    if shutil.which(argv[0]) is None:
        return {'status': 'not_installed'}
    try:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=3, text=True, encoding='utf-8', errors='replace',
                                env={**os.environ, 'LC_ALL': 'C', 'GIT_OPTIONAL_LOCKS': '0'})
    except subprocess.TimeoutExpired:
        return {'status': 'timeout'}
    except OSError as error:
        return {'status': 'error', 'error': str(error)[:300]}
    if len(result.stdout.encode()) > 65536:
        return {'status': 'output_limit', 'exit_code': result.returncode}
    status = 'available' if result.returncode == 0 else 'error'
    if any(word in result.stderr.lower() for word in ['password is required', 'permission denied',
                                                     'operation not permitted']):
        status = 'permission_required'
    return {'status': status, 'exit_code': result.returncode,
            'stdout': result.stdout.strip(), 'stderr': result.stderr.strip()[:600]}


def inventory(message_setup):
    modules = {}
    for name in ['rclpy', 'unitree_go', 'unitree_api', 'unitree_sdk2py', 'cyclonedds']:
        try:
            spec = importlib.util.find_spec(name)
            modules[name] = {'origin': None if spec is None else spec.origin,
                             'search_paths': [] if spec is None else list(spec.submodule_search_locations or [])}
        except (ImportError, ValueError, AttributeError) as error:
            modules[name] = {'error': type(error).__name__}
    distributions = {}
    for name in ['rclpy', 'unitree-sdk2py', 'cyclonedds']:
        try:
            distributions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            distributions[name] = None
    commands = {
        'addresses': ['ip', '-j', 'address'],
        'links': ['ip', '-j', '-d', 'link'],
        'routes': ['ip', '-j', 'route', 'show', 'table', 'all'],
        'rules': ['ip', '-j', 'rule'],
        'bridges': ['bridge', '-j', 'link'],
        'ipv4_forwarding': ['sysctl', '-n', 'net.ipv4.ip_forward'],
        'bridge_filtering': ['sysctl', '-n', 'net.bridge.bridge-nf-call-iptables'],
        'ros_packages': ['dpkg-query', '-W', '-f=${binary:Package}\t${Version}\n',
                         'ros-foxy-rclpy', 'ros-foxy-rmw-cyclonedds-cpp', 'cyclonedds*'],
        'library_candidates': ['ldconfig', '-p'],
        'message_source': ['git', '-C', str(Path(message_setup).parent.parent),
                           'rev-parse', 'HEAD'],
        'ipv4_firewall': ['sudo', '-n', 'iptables-save'],
        'ipv6_firewall': ['sudo', '-n', 'ip6tables-save'],
        'nft_firewall': ['sudo', '-n', 'nft', 'list', 'ruleset'],
    }
    probes = {key: command(value) for key, value in commands.items()}
    if probes['library_candidates']['status'] == 'available':
        probes['library_candidates']['stdout'] = '\n'.join(
            line for line in probes['library_candidates']['stdout'].splitlines()
            if any(word in line.lower() for word in ['ddsc', 'cyclone', 'rmw']))
    return {'event': 'inventory', 'schema_version': 1, 'actuation_requests_sent': 0,
            'python': sys.version.split()[0], 'architecture': platform.machine(),
            'kernel': platform.release(), 'ros_distro': os.environ.get('ROS_DISTRO'),
            'modules': modules, 'distribution_versions': distributions, 'probes': probes,
            'loaded_dds_version_verified': False,
            'notes': ['Missing distribution metadata does not prove a source installation is absent.',
                      'Library candidates are not proof of the library loaded during DDS execution.',
                      'Permission errors leave firewall review incomplete; no password is stored.']}


def sample(message):
    if any(len(v) != 3 for v in [message.position, message.velocity, message.imu_state.rpy]):
        raise ValueError('State vectors must have three components')
    values = [float(v) for v in message.position] + [float(v) for v in message.velocity]
    values += [float(v) for v in message.imu_state.rpy] + [float(message.yaw_speed)]
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Nonfinite state')
    stamp = getattr(message, 'stamp', None)
    source_stamp = None
    if stamp is not None and hasattr(stamp, 'sec') and hasattr(stamp, 'nanosec'):
        source_stamp = {'sec': int(stamp.sec), 'nanosec': int(stamp.nanosec)}
    return {'position': values[:3], 'velocity': values[3:6], 'rpy': values[6:9],
            'yaw_rate': values[9], 'mode': int(message.mode),
            'error_code': int(message.error_code), 'robot_timestamp': source_stamp,
            'frames_verified': False, 'source_timestamp_verified': False}


def loaded_dds_libraries(maps_path='/proc/self/maps'):
    """Identify actually mapped DDS binaries; hashes do not assert a source version."""
    result = []
    try:
        lines = Path(maps_path).read_text().splitlines()
    except OSError:
        return [{'error': 'Cannot read process maps'}]
    paths = {line.split(maxsplit=5)[5] for line in lines if len(line.split(maxsplit=5)) == 6}
    for value in sorted(paths):
        path = Path(value)
        if not path.name.startswith(('libddsc.', 'librmw_cyclonedds_cpp.')):
            continue
        item = {'path': value, 'sha256': None}
        try:
            if path.stat().st_size > 32 * 1024 * 1024:
                raise ValueError('Mapped DDS binary exceeds hash bound')
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            item['sha256'] = digest.hexdigest()
        except (OSError, ValueError) as error:
            item['error'] = str(error)[:200]
        result.append(item)
    return result


def state_stream(interface, domain, seconds):
    os.environ.update(ROS_DOMAIN_ID=str(domain), ROS_LOCALHOST_ONLY='0',
                      RMW_IMPLEMENTATION='rmw_cyclonedds_cpp')
    os.environ['CYCLONEDDS_URI'] = ('<CycloneDDS><Domain><General><NetworkInterfaceAddress>'
                                   + interface + '</NetworkInterfaceAddress><AllowMulticast>true'
                                   '</AllowMulticast></General></Domain></CycloneDDS>')
    import rclpy
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
    from unitree_go.msg import SportModeState

    rclpy.init(args=['--ros-args', '--disable-rosout-logs', '--disable-external-lib-logs'])
    node = rclpy.create_node('b2_field_state_recorder', enable_rosout=False,
                            start_parameter_services=False)
    counts = {'received': 0, 'finite': 0, 'emitted': 0, 'over_limit': 0}
    topic = '/lf/sportmodestate'
    try:
        def receive(message):
            counts['received'] += 1
            try:
                data = sample(message)
            except (ValueError, TypeError, AttributeError, OverflowError):
                return
            counts['finite'] += 1
            if counts['emitted'] >= 500:
                counts['over_limit'] += 1
                return
            counts['emitted'] += 1
            emit({'event': 'state', 'schema_version': 1, 'sequence': counts['emitted'],
                  'onboard_receipt_monotonic_s': time.monotonic(), 'state': data})
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT,
                         durability=DurabilityPolicy.VOLATILE)
        subscription = node.create_subscription(SportModeState, topic, receive, qos)
        started = time.monotonic()
        while time.monotonic() - started < seconds:
            rclpy.spin_once(node, timeout_sec=0.05)
        emit({'event': 'summary', 'schema_version': 1, 'actuation_requests_sent': 0,
              'topic': topic, 'observation_seconds': time.monotonic() - started,
              'counts': counts, 'frames_verified': False,
              'source_timestamp_verified': False, 'loaded_dds_libraries': loaded_dds_libraries(),
              'loaded_dds_source_version_verified': False})
        del subscription
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=['inventory', 'state'])
    parser.add_argument('--interface', required=True)
    parser.add_argument('--domain-id', required=True, type=int)
    parser.add_argument('--message-setup', required=True)
    parser.add_argument('--seconds', type=float, default=10.)
    args = parser.parse_args(argv)
    if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,64}', args.interface):
        parser.error('Invalid native interface')
    if not 0 <= args.domain_id <= 232 or not math.isfinite(args.seconds) or not 1 <= args.seconds <= 15:
        parser.error('Domain must be 0..232 and duration 1..15 seconds')
    if args.mode == 'inventory':
        emit(inventory(args.message_setup))
    else:
        state_stream(args.interface, args.domain_id, args.seconds)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
