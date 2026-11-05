"""Field diagnostics: pinned scope, honest collection and streaming failure cases."""

import copy
import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from contextlib import redirect_stderr, redirect_stdout


def module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / 'tools' / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


visit = module('field_visit')
onboard = module('inspect_onboard')


def state_event(index=1, at=0.):
    return {'event': 'state', 'schema_version': 1, 'sequence': index,
            'onboard_receipt_monotonic_s': at, 'jetson_receipt_monotonic_s': at,
            'state': {'position': [0., 0., 0.], 'velocity': [0., 0., 0.],
                      'rpy': [0., 0., 0.], 'yaw_rate': 0., 'frames_verified': False,
                      'source_timestamp_verified': False}}


def events():
    return [state_event(i + 1, i * .11) for i in range(25)] + [
        {'event': 'summary', 'schema_version': 1, 'actuation_requests_sent': 0,
         'counts': {'received': 25, 'finite': 25, 'emitted': 25}}]


class FieldProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'known-hosts').write_text('Synthetic test key\n')
        self.path = self.root / 'profile.json'
        self.config = {'schema_version': 1, 'ssh_destination': 'researcher@fe80::1%eth0',
                       'host_key_alias': 'fe80::1%eth0', 'known_hosts_file': 'known-hosts',
                       'ros_setup': '/opt/ros/foxy/setup.bash',
                       'message_setup': '/opt/verified workspace/install/setup.bash',
                       'native_interface': 'eth0', 'domain_id': 0}

    def load(self):
        self.path.write_text(json.dumps(self.config))
        self.path.chmod(0o600)
        return visit.load_profile(self.path, self.root)

    def test_valid_profile_pins_peer_and_quotes_setup_paths(self):
        config = self.load()
        command = visit.remote_command(config, 'state', 10.)
        self.assertIn('StrictHostKeyChecking=yes', command)
        self.assertIn('HostKeyAlias=fe80::1%eth0', command)
        self.assertIn('ForwardAgent=no', command)
        # Validate the actual remote shell syntax, including a path with spaces.
        checked = subprocess.run(['bash', '-n'], input=command[-1], text=True, capture_output=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertIn('/usr/bin/timeout', command[-1])

    def test_profile_rejects_secret_field_and_nonlocal_peer(self):
        for key, value in [('password', 'synthetic'), ('ssh_destination', 'researcher@2001:db8::1%eth0'),
                           ('native_interface', 'eth0</xml>'), ('domain_id', True)]:
            original = copy.deepcopy(self.config)
            self.config[key] = value
            with self.assertRaises(ValueError):
                self.load()
            self.config = original

    def test_profile_rejects_broad_permissions_and_missing_pin(self):
        self.load()
        self.path.chmod(0o644)
        with self.assertRaises(ValueError):
            visit.load_profile(self.path, self.root)
        (self.root / 'known-hosts').unlink()
        with self.assertRaises(FileNotFoundError):
            self.load()

    def test_default_plan_never_connects(self):
        self.config['known_hosts_file'] = str(self.root / 'known-hosts')
        self.load()
        with patch.object(visit, 'collect', side_effect=AssertionError('No active stage')), redirect_stdout(io.StringIO()):
            self.assertEqual(visit.main(['--config', str(self.path)]), 0)


class StateContractTests(unittest.TestCase):
    def test_continuous_diagnostic_does_not_claim_model_or_frame_validation(self):
        result = visit.summarize('state', events(), 0)
        self.assertTrue(result['transport_passed'])
        self.assertFalse(result['frames_verified'])
        self.assertFalse(result['model_state_integration'])

    def test_zero_samples_batched_samples_and_gaps_fail(self):
        for data in [events()[-1:], events()]:
            if len(data) > 1:
                for e in data[:-1]:
                    e['jetson_receipt_monotonic_s'] = 0.
            self.assertFalse(visit.summarize('state', data, 0)['transport_passed'])
        data = events()
        data[15]['jetson_receipt_monotonic_s'] += 1.
        self.assertFalse(visit.summarize('state', data, 0)['transport_passed'])

    def test_missing_summary_count_mismatch_duplicate_and_ssh_failure_fail(self):
        data = events()
        broken = copy.deepcopy(data)
        broken[-1]['counts']['emitted'] += 1
        duplicate = copy.deepcopy(data)
        duplicate[4]['sequence'] = 1
        nonfinite = copy.deepcopy(data)
        nonfinite[-1]['counts']['received'] += 1
        for sample in [data[:-1], broken, duplicate, nonfinite]:
            self.assertFalse(visit.summarize('state', sample, 0)['transport_passed'])
        self.assertFalse(visit.summarize('state', data, 255)['transport_passed'])

    def test_malformed_state_and_false_timing_claims_are_rejected(self):
        for key, value in [('yaw_rate', math.nan), ('position', [0., 0.]),
                           ('frames_verified', True), ('velocity', [True, 0., 0.])]:
            event = state_event()
            event['state'][key] = value
            with self.assertRaises((ValueError, KeyError)):
                visit.validate_event(event)

    def test_summary_must_contain_consistent_integer_counts(self):
        for values in [{}, {'received': 1, 'finite': 2, 'emitted': 1},
                       {'received': True, 'finite': 1, 'emitted': 1}]:
            with self.assertRaises(ValueError):
                visit.validate_event({'event': 'summary', 'schema_version': 1,
                                      'actuation_requests_sent': 0, 'counts': values})

    def test_inventory_collection_keeps_permission_failure_visible(self):
        event = {'event': 'inventory', 'schema_version': 1, 'actuation_requests_sent': 0,
                 'probes': {'firewall': {'status': 'permission_required'}}}
        result = visit.summarize('inventory', [event], 0)
        self.assertTrue(result['collection_complete'])
        self.assertIsNone(result['transport_passed'])
        self.assertEqual(result['probes_needing_followup'], ['firewall'])


class StreamCaptureTests(unittest.TestCase):
    def collect(self, program, deadline=2.):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        out = Path(temp.name)
        result = visit.collect([sys.executable, '-u', '-c', program], b'', out, 'state', deadline)
        return result, out

    def test_real_child_output_is_saved_with_external_receipt_time(self):
        payload = [state_event(), events()[-1]]
        text = '\n'.join(json.dumps(x) for x in payload) + '\n'
        result, path = self.collect('import sys; sys.stdin.read(); sys.stdout.write(' + repr(text) + ')')
        self.assertFalse(result['transport_passed'])
        saved = [json.loads(x) for x in (path / 'events.jsonl').read_text().splitlines()]
        self.assertEqual(len(saved), 2)
        self.assertTrue(all('jetson_receipt_monotonic_s' in x for x in saved))
        self.assertIsNone(result['error'])

    def test_truncated_json_invalid_json_and_timeout_fail(self):
        for program, deadline in [('print("not-json")', 2.),
                                  ('import sys; sys.stdout.write("{")', 2.),
                                  ('import time; time.sleep(5)', .1)]:
            result, path = self.collect(program, deadline)
            self.assertFalse(result['transport_passed'])
            self.assertIsNotNone(result['error'])
            self.assertTrue((path / 'summary.json').is_file())

    def test_oversized_payload_is_rejected_before_subprocess(self):
        with patch.object(visit.subprocess, 'Popen', side_effect=AssertionError('Must not spawn')):
            with self.assertRaises(ValueError):
                visit.collect([], b'x' * 32769, Path('.'), 'state')


class OnboardInventoryTests(unittest.TestCase):
    def test_missing_tool_and_permission_error_are_not_success(self):
        with patch.object(onboard.shutil, 'which', return_value=None):
            self.assertEqual(onboard.command(['missing'])['status'], 'not_installed')
        result = SimpleNamespace(returncode=1, stdout='', stderr='sudo: a password is required')
        with patch.object(onboard.shutil, 'which', return_value='/usr/bin/sudo'), patch.object(onboard.subprocess, 'run', return_value=result):
            self.assertEqual(onboard.command(['sudo', '-n', 'iptables-save'])['status'], 'permission_required')

    def test_sample_preserves_unverified_clock_and_rejects_bad_vectors(self):
        message = SimpleNamespace(position=[0., 0., 0.], velocity=[0., 0., 0.],
                                  imu_state=SimpleNamespace(rpy=[0., 0., 0.]), yaw_speed=0.,
                                  mode=7, error_code=0, stamp=SimpleNamespace(sec=5, nanosec=6))
        value = onboard.sample(message)
        self.assertEqual(value['robot_timestamp'], {'sec': 5, 'nanosec': 6})
        self.assertFalse(value['source_timestamp_verified'])
        message.position = [0.]
        with self.assertRaises(ValueError):
            onboard.sample(message)

    def test_mapped_dds_binary_is_hashed_without_claiming_source_version(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'libddsc.so.0'
            path.write_bytes(b'Synthetic binary identity')
            maps = Path(directory) / 'maps'
            maps.write_text('0000-1000 r-xp 0000 00:00 1 ' + str(path) + '\n')
            result = onboard.loaded_dds_libraries(maps)
            self.assertEqual(len(result), 1)
            self.assertEqual(len(result[0]['sha256']), 64)
            self.assertNotIn('version', result[0])

    def test_invalid_duration_fails_before_ros_import(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            onboard.main(['--mode', 'state', '--interface', 'eth0', '--domain-id', '0',
                          '--message-setup', '/synthetic/setup.bash', '--seconds', 'nan'])


if __name__ == '__main__':
    unittest.main()
