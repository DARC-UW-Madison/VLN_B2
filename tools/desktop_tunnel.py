"""Manage a dedicated loopback SSH tunnel for Windows App; Python 3.8+.

The SSH master runs in the background, independently of this CLI and chat.
No password, host address configuration, or GUI credential is saved here.
"""

import argparse
import contextlib
import errno
import fcntl
import hashlib
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys

RUNTIME_DIRECTORY = Path('/tmp') / ('vln-b2-rdp-' + str(os.getuid()))


class TunnelError(RuntimeError):
    """A local tunnel could not be safely inspected or changed."""


def validate(target, local_port, remote_port):
    if not re.fullmatch(r'[A-Za-z0-9_\[][A-Za-z0-9_.@:%\[\]-]*', target):
        raise TunnelError('Use an SSH alias or USER@HOST without spaces or SSH options.')
    if not all(isinstance(p, int) and 1 <= p <= 65535 for p in (local_port, remote_port)):
        raise TunnelError('Ports must be integers from 1 to 65535.')


def runtime_directory(create=False):
    if create:
        try:
            RUNTIME_DIRECTORY.mkdir(mode=0o700)
        except FileExistsError:
            pass
    try:
        info = RUNTIME_DIRECTORY.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise TunnelError('The tunnel runtime directory must be an owned private directory (0700), not a symlink.')
    return RUNTIME_DIRECTORY


def control_path(target, local_port, remote_port, create=False):
    validate(target, local_port, remote_port)
    directory = runtime_directory(create)
    if directory is None:
        return None
    identity = '{}\0{}\0{}'.format(target, local_port, remote_port).encode()
    path = directory / (hashlib.sha256(identity).hexdigest()[:20] + '.sock')
    if len(os.fsencode(path)) >= 100:
        raise TunnelError('The SSH control socket path is too long for macOS.')
    return path


def socket_present(path):
    if path is None:
        return False
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
        raise TunnelError('Refusing a control path that is not an owned UNIX socket.')
    return True


def control_command(path, target, operation):
    return ['ssh', '-S', str(path), '-O', operation, '--', target]


def running(path, target):
    if not socket_present(path):
        return False
    try:
        result = subprocess.run(control_command(path, target, 'check'), stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=3)
    except subprocess.TimeoutExpired as error:
        raise TunnelError('The dedicated SSH control master did not answer.') from error
    return result.returncode == 0


@contextlib.contextmanager
def operation_lock(path):
    flags = os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0)
    descriptor = os.open(str(path.with_suffix('.lock')), flags, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise TunnelError('The tunnel lock must be an owned private regular file (0600).')
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise TunnelError('Another operation for this tunnel is in progress.') from error
        yield
    finally:
        os.close(descriptor)


def remove_refused_socket(path):
    """Remove only an owned socket with no accepting process, under our lock."""
    if not socket_present(path):
        return
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
        probe.settimeout(1)
        try:
            probe.connect(str(path))
        except OSError as error:
            if error.errno == errno.ENOENT:
                return
            if error.errno != errno.ECONNREFUSED:
                raise TunnelError('Cannot establish that the old control socket is inactive.') from error
        else:
            raise TunnelError('An existing control socket accepts connections but did not answer SSH; leaving it intact.')
    # Revalidate ownership/type immediately before unlinking the stale socket.
    if socket_present(path):
        path.unlink()


def require_free_port(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(('127.0.0.1', port))
    except OSError as error:
        raise TunnelError('Local port {} is unavailable; no existing listener was stopped.'.format(port)) from error


def manage(action, target, local_port=13389, remote_port=3389):
    path = control_path(target, local_port, remote_port, create=action == 'start')
    if action == 'status':
        return running(path, target)
    if path is None:
        return False
    with operation_lock(path):
        active = running(path, target)
        if action == 'stop':
            if not active:
                return False
            result = subprocess.run(control_command(path, target, 'exit'), timeout=5)
            if result.returncode:
                raise TunnelError('The dedicated SSH master could not be stopped.')
            return False
        if active:
            return True
        remove_refused_socket(path)
        require_free_port(local_port)
        command = [
            'ssh', '-fNT', '-M', '-S', str(path),
            '-o', 'ControlPersist=no', '-o', 'ExitOnForwardFailure=yes',
            '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=15',
            '-o', 'ServerAliveCountMax=3', '-o', 'ForwardAgent=no',
            '-o', 'ForwardX11=no', '-o', 'PermitLocalCommand=no',
            '-L', '127.0.0.1:{}:127.0.0.1:{}'.format(local_port, remote_port),
            '--', target,
        ]
        # Keep SSH's normal host-key, password and identity-check prompts visible.
        result = subprocess.run(command)
        if result.returncode:
            raise TunnelError('SSH failed to start the tunnel; inspect its message above.')
        if not running(path, target):
            raise TunnelError('SSH returned without a responsive dedicated control master.')
        return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'status', 'stop'])
    parser.add_argument('target', help='An existing SSH alias or USER@HOST; no credentials are stored.')
    parser.add_argument('--local-port', type=int, default=13389)
    parser.add_argument('--remote-port', type=int, default=3389)
    args = parser.parse_args(argv)
    try:
        active = manage(args.action, args.target, args.local_port, args.remote_port)
    except (TunnelError, OSError, subprocess.SubprocessError) as error:
        print('Tunnel error: {}'.format(error), file=sys.stderr)
        return 2
    if active:
        print('Tunnel running: 127.0.0.1:{} -> Jetson loopback:{}'.format(args.local_port, args.remote_port))
        print('Open Windows App profile "B2 Jetson (SSH tunnel)" (adjust its port if overridden).')
        print('This checks the SSH tunnel only, not RDP login or desktop health.')
    else:
        print('This dedicated tunnel is not running.')
    return 0 if args.action != 'status' or active else 1


if __name__ == '__main__':
    sys.exit(main())
