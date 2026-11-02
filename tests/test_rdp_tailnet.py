"""Narrow host-network guard behavior; no real firewall or Tailscale mutation."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

SPEC = importlib.util.spec_from_file_location(
    'rdp_tailnet_ready', Path(__file__).resolve().parents[1] / 'deploy/rdp-tailnet-ready.py')
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)
ADDRESS = '100.64.0.10'


class TailnetReadinessTests(unittest.TestCase):
    def command(self, rule_status=0, flags=None, local=ADDRESS):
        return Mock(side_effect=[SimpleNamespace(stdout=ADDRESS + '\n'),
                                SimpleNamespace(stdout=json.dumps([
                                    {'flags': flags if flags is not None else ['UP'],
                                     'addr_info': [{'local': local}]}])),
                                SimpleNamespace(returncode=rule_status),
                                SimpleNamespace(returncode=0)])

    def test_repeated_start_checks_existing_rule_without_inserting_another(self):
        command = self.command()
        helper.prepare(ADDRESS, command)
        self.assertEqual(command.call_count, 3)
        arguments = command.call_args.args[0]
        self.assertIn('-C', arguments)
        self.assertIn(ADDRESS + '/32', arguments)
        self.assertEqual(arguments[-2:], ['-j', 'DROP'])
        self.assertIn('tailscale0', arguments)
        self.assertIn('3389', arguments)

    def test_missing_rule_inserts_only_scoped_rule_without_flush_or_policy_change(self):
        command = self.command(rule_status=1)
        helper.prepare(ADDRESS, command)
        arguments = command.call_args.args[0]
        self.assertEqual(arguments[:6], ['/usr/sbin/iptables', '-w', '5', '-I', 'INPUT', '1'])
        self.assertIn(ADDRESS + '/32', arguments)
        self.assertNotIn('-F', arguments)
        self.assertNotIn('-P', arguments)

    def test_non_tailnet_or_malformed_address_never_touches_network(self):
        command = Mock()
        for address in ['192.0.2.1', '0.0.0.0', '::1', ADDRESS + '\n100.64.0.11']:
            with self.subTest(address=address), self.assertRaises(ValueError):
                helper.prepare(address, command)
        command.assert_not_called()

    def test_unready_or_changed_address_never_touches_firewall(self):
        for command in [self.command(flags=[]), self.command(local='100.64.0.11'),
                        Mock(return_value=SimpleNamespace(stdout='100.64.0.11\n'))]:
            with self.assertRaises(RuntimeError):
                helper.prepare(ADDRESS, command)
            self.assertLessEqual(command.call_count, 2)

    def test_firewall_inspection_failure_never_becomes_success_or_policy_replacement(self):
        command = self.command(rule_status=2)
        with self.assertRaises(RuntimeError):
            helper.prepare(ADDRESS, command)
        self.assertEqual(command.call_count, 3)


if __name__ == '__main__':
    unittest.main()
