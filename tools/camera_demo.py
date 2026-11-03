"""Run a bounded, no-robot camera/path demonstration on the prepared Jetson.

The host supervisor starts two temporary offline containers and atomically
refreshes a local HTML file. There is no web server, listening port, motor
sender, autostart service or model download. The internal predictor loads once.
"""

import argparse
import base64
from dataclasses import asdict
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time


BASE_REV = '4415a3b810e636d11dfa86b0e9ba40bb00535aa8'
CHECKPOINT_SHA = '2d2cab167ef723cf6644729128016ccbb0ab5b131a3aa561c7418a3318ea51e4'
STATE_SOURCE = 'assumed stationary; no robot state received'


def atomic_write(path, data):
    """Replace only a supervisor-owned publication, never an immutable input."""
    descriptor, name = tempfile.mkstemp(prefix='.publish-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def publish_json(path, data):
    atomic_write(path, (json.dumps(data, indent=2, allow_nan=False) + '\n').encode())


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def discover_camera(sys_usb=Path('/sys/bus/usb/devices'), video=Path('/sys/class/video4linux'),
                    dev=Path('/dev')):
    """Require one identified ZED video device; never guess a video/USB number."""
    videos, companions = [], []
    for node in sys_usb.iterdir():
        try:
            identity = ((node / 'idVendor').read_text().strip(),
                        (node / 'idProduct').read_text().strip())
            if identity[0] != '2b03' or identity[1] not in {'f880', 'f881'}:
                continue
            bus = int((node / 'busnum').read_text())
            number = int((node / 'devnum').read_text())
            entry = (node.resolve(), dev / 'bus/usb' / ('%03d' % bus) / ('%03d' % number))
            (videos if identity[1] == 'f880' else companions).append(entry)
        except (FileNotFoundError, ValueError):
            continue
    if len(videos) != 1 or len(companions) > 1:
        raise ValueError('Connect exactly one supported ZED 2i; ambiguous/absent USB devices')
    parent, endpoint = videos[0]
    nodes = [dev / node.name for node in sorted(video.iterdir())
             if parent in (node / 'device').resolve().parents]
    if not nodes:
        raise ValueError('No video nodes belong to the identified ZED USB device')
    devices = nodes + [endpoint] + [item[1] for item in companions]
    if not all(node.is_char_device() for node in devices):
        raise ValueError('Camera device mapping changed; inspect USB and retry')
    return devices


def local_inputs(project):
    hub = (Path.home() / '.cache/huggingface').resolve() / 'hub'
    return {'src': project / 'src', 'tools': project / 'tools',
            'camera_api': project / 'local/camera-runtime/attempt-01/python',
            'settings': project / 'local/camera-runtime/attempt-01/settings',
            'sdk': Path('/usr/local/zed'),
            'turbojpeg': Path('/usr/lib/aarch64-linux-gnu/libturbojpeg.so.0').resolve(),
            'base': hub / 'models--OpenGVLab--InternVL3-1B',
            'checkpoint': (project / 'models/tic-vla-671de608-01/model.safetensors').resolve(),
            'upstream': Path.home() / 'Developer/External/TIC-VLA'}


def validate_inputs(inputs):
    for name, path in inputs.items():
        if not path.exists():
            raise ValueError('Missing prepared input: ' + name + '; see the setup guide')
    if not (inputs['base'] / 'snapshots' / BASE_REV / 'config.json').is_file():
        raise ValueError('The approved base-model snapshot is missing')
    if sha256(inputs['checkpoint']) != CHECKPOINT_SHA:
        raise ValueError('Derived checkpoint SHA256 differs from the approved conversion')
    if not (inputs['camera_api'] / 'pyzed').is_dir():
        raise ValueError('The private camera binding prefix is missing')


def docker_command(image, name, memory, mounts, devices=(), groups=()):
    command = ['sudo', '-n', 'docker', 'run', '--rm', '--pull', 'never', '--name', name,
               '--runtime', 'nvidia', '--network', 'none', '--read-only',
               '--user', '%d:%d' % (os.getuid(), os.getgid()),
               '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
               '--memory', memory, '--cpus', '2', '--pids-limit', '128',
               '--tmpfs', '/tmp:rw,nosuid,nodev,size=256m']
    for group in sorted(set(groups)):
        command += ['--group-add', str(group)]
    for device in devices:
        command += ['--device', str(device)]
    for source, destination, readonly in mounts:
        command += ['--mount', 'type=bind,src=%s,dst=%s%s' %
                    (source, destination, ',readonly' if readonly else '')]
    environment = {
        'HOME': '/tmp/home', 'PYTHONDONTWRITEBYTECODE': '1',
        'PYTHONPATH': '/workspace/src:/workspace/tools:/camera-api',
        'HF_HOME': '/tmp/hf', 'HF_MODULES_CACHE': '/tmp/hf-modules',
        'XDG_CACHE_HOME': '/tmp/cache', 'TORCH_HOME': '/tmp/torch',
        'CUDA_CACHE_PATH': '/tmp/cuda', 'HF_HUB_OFFLINE': '1',
        'TRANSFORMERS_OFFLINE': '1', 'HF_DATASETS_OFFLINE': '1',
        'HF_HUB_DISABLE_TELEMETRY': '1', 'HF_HUB_DISABLE_IMPLICIT_TOKEN': '1',
        'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2',
        'TOKENIZERS_PARALLELISM': 'false', 'NVIDIA_DRIVER_CAPABILITIES': 'compute,utility',
        'LD_LIBRARY_PATH': '/camera-libs:/usr/local/zed/lib:/usr/local/cuda/lib64:'
                           '/usr/lib/aarch64-linux-gnu/tegra'}
    for key, value in environment.items():
        command += ['-e', key + '=' + value]
    return command + ['--entrypoint', 'timeout', image, '-k', '5s', '120s', 'python3.11']


def commands(image, inputs, work, devices, duration, instruction, gpu_group, sdk_group):
    capture_mounts = [(inputs['src'], '/workspace/src', True),
                      (inputs['tools'], '/workspace/tools', True),
                      (inputs['camera_api'], '/camera-api', True),
                      (inputs['sdk'], '/usr/local/zed', True),
                      (inputs['turbojpeg'], '/camera-libs/libturbojpeg.so.0', True),
                      (inputs['settings'], '/camera-settings', False),
                      (work / 'camera', '/camera', False)]
    predict_mounts = [(inputs['src'], '/workspace/src', True),
                      (inputs['tools'], '/workspace/tools', True),
                      (inputs['base'], '/input/base-repo', True),
                      (inputs['checkpoint'], '/input/model.safetensors', True),
                      (inputs['upstream'], '/opt/upstream', True),
                      (work / 'camera', '/camera', True),
                      (work / 'predictions', '/reports', False)]
    # Random run names identify only this invocation for bounded cleanup.
    token = hashlib.sha256(str(work).encode()).hexdigest()[:12]
    names = ['b2-demo-camera-' + token, 'b2-demo-predict-' + token]
    capture = docker_command(image, names[0], '4g', capture_mounts, devices,
                             [gpu_group, sdk_group])
    capture += ['/workspace/tools/record_camera_stream.py', '--output-dir', '/camera/frames',
                '--settings-dir', '/camera-settings', '--duration', str(duration), '--fps', '1']
    prediction = docker_command(image, names[1], '24g', predict_mounts, groups=[gpu_group])
    prediction += ['/workspace/tools/camera_demo.py', 'predict',
                   '--stream', '/camera/frames', '--output', '/reports',
                   '--duration', str(duration), '--instruction', instruction,
                   '--base-model', '/input/base-repo/snapshots/' + BASE_REV,
                   '--checkpoint', '/input/model.safetensors',
                   '--upstream-root', '/opt/upstream', '--assumed-stationary']
    return names, [capture, prediction]


def run_predictor(args, factory=None, read_observation=None, clock=time.monotonic, wait=time.sleep):
    """Load once, then predict on new immutable frames without semantic reuse."""
    if os.environ.get('HF_HUB_OFFLINE') != '1' or not args.assumed_stationary:
        raise ValueError('Offline mode and explicit assumed-stationary state are required')
    if not args.instruction.strip() or not math.isfinite(args.duration) or not 1 <= args.duration <= 60:
        raise ValueError('Provide a nonempty instruction and duration from 1 to 60 seconds')
    if args.checkpoint.suffix != '.safetensors' or sha256(args.checkpoint) != CHECKPOINT_SHA:
        raise ValueError('Only the hash-verified derived safetensors checkpoint is accepted')
    if factory is None:
        from b2_tic_vla.inference import TicVlaPredictor
        factory = TicVlaPredictor
    if read_observation is None:
        from observe_async import load_observation
        read_observation = load_observation
    from render_prediction import render
    from b2_tic_vla.types import RobotState

    started, count, seen, last_image = clock(), 0, {}, None
    status = {'stage': 'loading_model', 'motion_sent': False, 'robot_connected': False,
              'state_source': STATE_SOURCE, 'completed': 0}
    publish_json(args.output / 'status.json', status)
    try:
        model = factory(args.base_model, str(args.checkpoint), device='cuda:0',
                        upstream_root=args.upstream_root).load()
        load_seconds = clock() - started
        deadline = started + args.duration
        while clock() < deadline:
            status['stage'] = 'waiting_for_new_image'
            publish_json(args.output / 'status.json', status)
            try:
                observation, expected = read_observation(args.stream, args.instruction, seen, clock())
            except FileNotFoundError:
                wait(.1)
                continue
            if observation.frame.path == last_image or clock() - observation.frame.received_at > 2:
                wait(.1)
                continue
            last_image = observation.frame.path
            source = Path(last_image)
            input_bytes = source.read_bytes()
            if hashlib.sha256(input_bytes).hexdigest() != expected:
                raise ValueError('Camera image differs from its manifest')
            count += 1
            stem = 'prediction-%03d' % count
            image_path = args.output / (stem + '.jpg')
            with image_path.open('xb') as stream:
                stream.write(input_bytes)
            reference = clock()
            status.update(stage='predicting', input_image=source.name)
            publish_json(args.output / 'status.json', status)
            # Camera motion is not measured; never manufacture real odometry.
            state = RobotState(reference, 0., 0., 0., 0., 0., 0.,
                               frame_id='assumed_stationary_world', velocity_frame='body')
            plan = model.predict([str(image_path)], args.instruction, state, reference)
            if hashlib.sha256(image_path.read_bytes()).hexdigest() != expected:
                raise ValueError('Immutable prediction image changed during inference')
            report = {'schema_version': 1, 'mode': 'recorded_image_assumed_stationary',
                      'passed': True, 'motion_sent': False, 'robot_connected': False,
                      'state_source': STATE_SOURCE, 'instruction': args.instruction,
                      'image_sha256': expected, 'checkpoint_sha256': CHECKPOINT_SHA,
                      'frame': asdict(observation.frame), 'load_seconds': load_seconds,
                      'inference_seconds': clock() - reference, 'plan': asdict(plan),
                      'model': model.describe(), 'navigation_quality_evaluated': False,
                      'coordinate_note': 'Model-relative metres; physical alignment unverified',
                      'timing_note': 'Stationary synchronous replay; source clock unverified; '
                                     'waypoint interval assumed, not a B2 control period'}
            # Validate the same image/plan before publishing any success marker.
            encoded = json.dumps(report, indent=2, allow_nan=False)
            document = render(json.loads(encoded), input_bytes)
            with (args.output / (stem + '.json')).open('x') as stream:
                stream.write(encoded + '\n')
            with (args.output / (stem + '.html')).open('x') as stream:
                stream.write(document)
            status.update(completed=count, last_report=stem + '.html',
                          last_input=source.name, inference_seconds=report['inference_seconds'],
                          input_received_at=observation.frame.received_at)
            publish_json(args.output / 'status.json', status)
        status.update(stage='finished', passed=count > 0)
    except (Exception, KeyboardInterrupt) as error:
        status.update(stage='failed', passed=False, error_type=type(error).__name__, error=str(error))
    publish_json(args.output / 'status.json', status)
    return status


def read_status(path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {}


def publish_view(work, instruction, running, outcome=None):
    """Keep current preview and older prediction provenance visibly separate."""
    status = read_status(work / 'predictions/status.json')
    manifest = read_status(work / 'camera/frames/latest.json')
    preview = '<p>Waiting for the first camera image.</p>'
    if manifest:
        name = manifest.get('frame', {}).get('path', '')
        if re.fullmatch(r'frame-[0-9]{6}\.jpg', name) is None:
            raise ValueError('Invalid camera preview filename')
        image = work / 'camera/frames' / name
        data = image.read_bytes()
        if hashlib.sha256(data).hexdigest() != manifest.get('image_sha256'):
            raise ValueError('Camera preview hash mismatch')
        age = max(0., time.monotonic() - manifest['frame']['received_at'])
        preview = ('<p>Latest camera: %s. Receipt age: %.1f s (capture clock unverified).</p>'
                   '<img alt="Latest camera preview, not necessarily the prediction input" '
                   'src="data:image/jpeg;base64,%s">' %
                   (html.escape(name), age, base64.b64encode(data).decode()))
    report = status.get('last_report')
    completed = int(status.get('completed', 0))
    result = '<p>No completed prediction yet. Initial model load and prediction take time.</p>'
    if report:
        if re.fullmatch(r'prediction-[0-9]{3}\.html', report) is None:
            raise ValueError('Invalid prediction report filename')
        result = ('<p>Completed: %d. Input: %s. Inference: %.2f s. '
                  'This path belongs to that saved input, not the changing preview.</p>'
                  '<p><a target="_blank" href="predictions/%s">Open full prediction and coordinates</a></p>'
                  '<iframe title="Exact prediction input and model path" src="predictions/%s"></iframe>' %
                  (completed, html.escape(status['last_input']), status['inference_seconds'], report, report))
    state = status.get('stage', 'starting') if running else (outcome or 'stopped')
    error = '<p role="alert">%s</p>' % html.escape(status.get('error', ''))
    document = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">%s
<title>TIC-VLA camera demo</title><style>
body{font:16px/1.6 system-ui;background:#f3f6fa;color:#18283a;margin:0}main{max-width:1200px;margin:auto;padding:24px}
section{background:white;border-radius:12px;padding:20px;margin:20px 0}.notice{padding:16px;background:#fff0ce}
img{width:100%%;max-width:800px;height:auto}iframe{width:100%%;height:1250px;border:1px solid #d6dee8}
code{overflow-wrap:anywhere}</style><main><h1>TIC-VLA camera demo</h1>
<p class="notice"><strong>Assumed stationary state. No robot commands.</strong><br>
Moving the camera changes the image but supplies no measured robot motion.
Paths are unvalidated numerical predictions, not obstacle clearance.</p>
<p><strong>Stage:</strong> %s · <strong>Instruction:</strong> %s</p>%s
<section><h2>1. Current camera preview (target 1 image/s)</h2>%s</section>
<section><h2>2. Last completed prediction and its exact input</h2>%s</section>
<p>%s</p></main></html>''' % (
        '<meta http-equiv="refresh" content="2">' if running else '',
        html.escape(state), html.escape(instruction), error, preview, result,
        'Refreshes every 2 seconds. Stop the terminal with Ctrl+C or wait for the bounded run.'
        if running else 'Run ended. This saved page no longer refreshes. No robot was controlled.')
    atomic_write(work / 'index.html', document.encode())


def supervise(args, project, inputs, devices, image):
    requested = args.output.expanduser()
    work = requested.parent.resolve(strict=True) / requested.name
    if not str(work).startswith(str(project / 'local') + os.sep):
        raise ValueError('Choose a new output directory below the project local/ directory')
    work.mkdir(mode=0o700, exist_ok=False)
    (work / 'camera').mkdir(mode=0o700)
    (work / 'predictions').mkdir(mode=0o700)
    names, invocations = commands(image, inputs, work, devices, args.duration,
                                 args.instruction, os.stat('/dev/nvmap').st_gid,
                                 os.stat(inputs['sdk']).st_gid)
    publish_json(work / 'invocation.json', {'image': image, 'commands': invocations,
                                           'instruction': args.instruction, 'motion_sent': False})
    processes, streams, outcome = [], [], 'failed'
    try:
        publish_view(work, args.instruction, True)
        print('Open on the Jetson: ' + (work / 'index.html').as_uri(), flush=True)
        print('No web server or robot commands. Ctrl+C stops this bounded demo.', flush=True)
        for role, command in zip(['camera', 'predict'], invocations):
            stream = (work / (role + '.log')).open('x')
            streams.append(stream)
            processes.append(subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT))
        deadline = time.monotonic() + 125
        while any(p.poll() is None for p in processes):
            publish_view(work, args.instruction, True)
            if any(p.poll() not in (None, 0) for p in processes):
                raise RuntimeError('A demo container failed; inspect private camera.log/predict.log')
            if time.monotonic() >= deadline:
                raise TimeoutError('Demo exceeded its external supervision deadline')
            time.sleep(.5)
        status = read_status(work / 'predictions/status.json')
        if not status.get('passed') or not status.get('completed'):
            raise RuntimeError('No successful completed prediction; inspect private logs/status')
        outcome = 'finished'
    except KeyboardInterrupt:
        outcome = 'stopped_by_operator'
    except Exception as error:
        print(type(error).__name__ + ': ' + str(error), file=sys.stderr)
    finally:
        cleanup_errors = []
        for name in names:
            # Remove only this run's containers; an independent inner timeout is also present.
            try:
                cleanup = subprocess.run(['sudo', '-n', 'docker', 'rm', '-f', name],
                                         capture_output=True, text=True, timeout=15)
                if cleanup.returncode and 'No such container' not in cleanup.stderr:
                    cleanup_errors.append('Could not remove run container: ' + name)
            except Exception as error:
                cleanup_errors.append(type(error).__name__ + ': ' + str(error))
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for stream in streams:
            stream.close()
        if cleanup_errors:
            outcome = 'failed'
            print('Cleanup needs attention: ' + '; '.join(cleanup_errors), file=sys.stderr)
        publish_json(work / 'summary.json', {'outcome': outcome, 'cleanup_errors': cleanup_errors,
                                             'motion_sent': False,
                                             'robot_connected': False,
                                             'container_exits': [p.returncode for p in processes]})
        publish_view(work, args.instruction, False, outcome)
    print('Demo ' + outcome + '; results retained in ' + str(work), flush=True)
    return 0 if outcome in {'finished', 'stopped_by_operator'} else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ['check', 'run']:
        item = sub.add_parser(name)
        item.add_argument('--image', default='vln-b2-runtime:jp5')
        item.add_argument('--camera-api', type=Path)
        item.add_argument('--settings-dir', type=Path)
        if name == 'run':
            item.add_argument('--output', type=Path, required=True)
            item.add_argument('--duration', type=float, default=60.)
            item.add_argument('--instruction', required=True)
    item = sub.add_parser('predict', help=argparse.SUPPRESS)
    item.add_argument('--stream', type=Path, required=True)
    item.add_argument('--output', type=Path, required=True)
    item.add_argument('--duration', type=float, required=True)
    item.add_argument('--instruction', required=True)
    item.add_argument('--base-model', required=True)
    item.add_argument('--checkpoint', type=Path, required=True)
    item.add_argument('--upstream-root', required=True)
    item.add_argument('--assumed-stationary', action='store_true', required=True)
    args = parser.parse_args(argv)
    os.umask(0o077)
    if args.command == 'predict':
        result = run_predictor(args)
        return 0 if result.get('passed') else 1
    if os.getuid() == 0:
        parser.error('Run as the research user after sudo -v; do not sudo this Python program')
    if args.command == 'run' and (not math.isfinite(args.duration) or not 1 <= args.duration <= 60
                                  or not args.instruction.strip() or len(args.instruction) > 1000):
        parser.error('Use a duration in [1, 60] and an instruction of 1 to 1000 characters')
    try:
        project = Path(__file__).resolve().parents[1]
        inputs = local_inputs(project)
        if args.camera_api:
            inputs['camera_api'] = args.camera_api.expanduser().resolve(strict=True)
        if args.settings_dir:
            inputs['settings'] = args.settings_dir.expanduser().resolve(strict=True)
        validate_inputs(inputs)
        devices = discover_camera()
        result = subprocess.run(['sudo', '-n', 'docker', 'image', 'inspect', args.image,
                                 '--format', '{{.Id}}'], capture_output=True, text=True, timeout=15)
        if result.returncode:
            raise RuntimeError('Cannot inspect the existing image. Run sudo -v; no image is pulled.')
        image = result.stdout.strip()
        if re.fullmatch(r'sha256:[0-9a-f]{64}', image) is None:
            raise ValueError('Docker did not return an immutable image ID')
        if args.command == 'check':
            print(json.dumps({'prepared_inputs_verified': True, 'image': image,
                              'devices': [str(node) for node in devices],
                              'model_loaded': False, 'camera_opened': False,
                              'motion_sent': False}, indent=2))
            return 0
        return supervise(args, project, inputs, devices, image)
    except Exception as error:
        print(type(error).__name__ + ': ' + str(error), file=sys.stderr)
        return 1


def interrupt(signum, frame):
    raise KeyboardInterrupt()


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, interrupt)
    raise SystemExit(main())
