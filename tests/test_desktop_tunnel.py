"""Check dedicated tunnel ownership and lifecycle without contacting a host."""

import importlib.util
import errno
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    'desktop_tunnel', Path(__file__).resolve().parents[1] / 'tools/desktop_tunnel.py'
)
tunnel = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tunnel)


class DesktopTunnelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/tmp')
        self.addCleanup(self.temp.cleanup)
        self.runtime = Path(self.temp.name) / 'runtime'
        self.runtime_patch = patch.object(tunnel, 'RUNTIME_DIRECTORY', self.runtime)
        self.runtime_patch.start()
        self.addCleanup(self.runtime_patch.stop)

    def test_status_missing_socket_is_read_only_and_never_authenticates(self):
        with patch.object(tunnel.subprocess, 'run') as run:
            self.assertFalse(tunnel.manage('status', 'research@host'))
        run.assert_not_called()
        self.assertFalse(self.runtime.exists())

    def test_start_detaches_with_only_loopback_forward_and_no_saved_secret(self):
        with patch.object(tunnel, 'running', side_effect=[False, True]), patch.object(
            tunnel, 'remove_refused_socket'
        ), patch.object(tunnel, 'require_free_port') as free, patch.object(
            tunnel.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)
        ) as run:
            self.assertTrue(tunnel.manage('start', 'research@host'))
        free.assert_called_once_with(13389)
        command = run.call_args.args[0]
        self.assertEqual(command[:3], ['ssh', '-fNT', '-M'])
        self.assertEqual(command[-2:], ['--', 'research@host'])
        self.assertEqual(command[command.index('-L') + 1], '127.0.0.1:13389:127.0.0.1:3389')
        for value in ['ExitOnForwardFailure=yes', 'ServerAliveInterval=15',
                      'ServerAliveCountMax=3', 'ForwardAgent=no', 'ForwardX11=no']:
            self.assertIn(value, command)
        self.assertFalse(any('password' in arg.lower() for arg in command))
        self.assertEqual(self.runtime.stat().st_mode & 0o777, 0o700)

    def test_existing_master_start_does_not_start_another_or_probe_its_port(self):
        with patch.object(tunnel, 'running', return_value=True), patch.object(
            tunnel, 'require_free_port'
        ) as free, patch.object(tunnel.subprocess, 'run') as run:
            self.assertTrue(tunnel.manage('start', 'host'))
        free.assert_not_called()
        run.assert_not_called()

    def test_busy_port_never_stops_or_replaces_existing_listener(self):
        with patch.object(tunnel, 'running', return_value=False), patch.object(
            tunnel, 'remove_refused_socket'
        ), patch.object(tunnel, 'require_free_port', side_effect=tunnel.TunnelError('occupied')), patch.object(
            tunnel.subprocess, 'run'
        ) as run:
            with self.assertRaises(tunnel.TunnelError):
                tunnel.manage('start', 'host')
        run.assert_not_called()

    def test_stop_uses_only_its_target_and_ports_control_socket(self):
        own = tunnel.control_path('host-a', 13389, 3389, create=True)
        other = tunnel.control_path('host-b', 13389, 3389)
        other_port = tunnel.control_path('host-a', 13390, 3389)
        self.assertNotEqual(own, other)
        self.assertNotEqual(own, other_port)
        with patch.object(tunnel, 'running', return_value=True), patch.object(
            tunnel.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)
        ) as run:
            self.assertFalse(tunnel.manage('stop', 'host-a'))
        self.assertEqual(run.call_args.args[0], ['ssh', '-S', str(own), '-O', 'exit', '--', 'host-a'])

    def test_insecure_directory_or_symlink_is_rejected_before_ssh(self):
        for symlink in [False, True]:
            with self.subTest(symlink=symlink), patch.object(tunnel.subprocess, 'run') as run:
                if symlink:
                    self.runtime.symlink_to(Path(self.temp.name), target_is_directory=True)
                else:
                    self.runtime.mkdir(mode=0o755)
                with self.assertRaisesRegex(tunnel.TunnelError, 'private directory'):
                    tunnel.manage('status', 'host')
                run.assert_not_called()
                if symlink:
                    self.runtime.unlink()
                else:
                    self.runtime.rmdir()

    def test_regular_file_at_control_path_is_not_removed_or_used(self):
        path = tunnel.control_path('host', 13389, 3389, create=True)
        path.write_text('preserve')
        with patch.object(tunnel.subprocess, 'run') as run:
            with self.assertRaisesRegex(tunnel.TunnelError, 'UNIX socket'):
                tunnel.manage('start', 'host')
        self.assertEqual(path.read_text(), 'preserve')
        run.assert_not_called()

    def test_invalid_target_or_ports_are_rejected_without_runtime_creation(self):
        for host, port in [('-oProxyCommand=bad', 13389), ('host;command', 13389),
                           ('host\ncommand', 13389), ('host', 0), ('host', 65536)]:
            with self.subTest(host=host, port=port), self.assertRaises(tunnel.TunnelError):
                tunnel.manage('start', host, port)
        self.assertFalse(self.runtime.exists())

    def test_unresponsive_live_socket_is_preserved(self):
        path = tunnel.control_path('host', 13389, 3389, create=True)
        with patch.object(tunnel, 'socket_present', return_value=True), patch.object(
            tunnel.socket, 'socket'
        ), patch.object(Path, 'unlink') as unlink:
            with self.assertRaisesRegex(tunnel.TunnelError, 'leaving it intact'):
                tunnel.remove_refused_socket(path)
        unlink.assert_not_called()

    def test_stale_owned_socket_is_recovered(self):
        path = tunnel.control_path('host', 13389, 3389, create=True)
        with patch.object(tunnel, 'socket_present', return_value=True), patch.object(
            tunnel.socket, 'socket'
        ) as socket_class, patch.object(Path, 'unlink') as unlink:
            socket_class.return_value.__enter__.return_value.connect.side_effect = OSError(errno.ECONNREFUSED, 'inactive')
            tunnel.remove_refused_socket(path)
        unlink.assert_called_once_with()

    def test_port_probe_binds_only_ipv4_loopback(self):
        with patch.object(tunnel.socket, 'socket') as socket_class:
            tunnel.require_free_port(13389)
        socket_class.return_value.__enter__.return_value.bind.assert_called_once_with(('127.0.0.1', 13389))

    def test_lock_symlink_is_rejected_without_touching_destination(self):
        path = tunnel.control_path('host', 13389, 3389, create=True)
        destination = Path(self.temp.name) / 'preserve'
        destination.write_text('existing data')
        path.with_suffix('.lock').symlink_to(destination)
        with patch.object(tunnel.subprocess, 'run') as run, self.assertRaises(OSError):
            tunnel.manage('start', 'host')
        self.assertEqual(destination.read_text(), 'existing data')
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
