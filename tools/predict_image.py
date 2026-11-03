"""Predict a path from one recorded image and explicitly assumed stationary state.

No camera, DDS, robot client or command sender is constructed. Run inside the
reviewed offline GPU container; the result is an experiment, not a motion plan
approved for execution. The image serves as both semantic and current input.
"""

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import time


def sha256(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def predict(args):
    if os.environ.get('HF_HUB_OFFLINE') != '1':
        raise ValueError('HF_HUB_OFFLINE=1 is required')
    if not args.assumed_stationary:
        raise ValueError('Explicit --assumed-stationary is required; no B2 state is read')
    if not args.instruction.strip():
        raise ValueError('Provide a nonempty navigation instruction')
    if not args.image.is_file() or not 0 < args.image.stat().st_size <= 32 * 1024 * 1024:
        raise ValueError('Provide a nonempty recorded image of at most 32 MiB')
    if args.checkpoint.suffix != '.safetensors':
        raise ValueError('Only the reviewed converted safetensors checkpoint is accepted')
    if re.fullmatch(r'[0-9a-f]{64}', args.expected_sha256) is None:
        raise ValueError('Provide a lowercase SHA256 digest')
    if sha256(args.checkpoint) != args.expected_sha256:
        raise ValueError('Checkpoint SHA256 mismatch')
    image_sha256 = sha256(args.image)
    from b2_tic_vla.inference import TicVlaPredictor
    from b2_tic_vla.types import RobotState

    started = time.monotonic()
    predictor = TicVlaPredictor(args.base_model, str(args.checkpoint),
                                device='cuda:0', upstream_root=args.upstream_root).load()
    load_seconds = time.monotonic() - started
    reference = time.monotonic()
    state = RobotState(reference, 0., 0., 0., 0., 0., 0.,
                       frame_id='assumed_stationary_world', velocity_frame='body')
    plan = predictor.predict([str(args.image)], args.instruction.strip(), state, reference)
    if sha256(args.image) != image_sha256:
        raise ValueError('Recorded image changed during inference')
    return {'schema_version': 1, 'mode': 'recorded_image_assumed_stationary', 'passed': True,
            'motion_sent': False, 'robot_connected': False,
            'state_source': 'assumed stationary; no robot state received',
            'instruction': args.instruction.strip(), 'image_sha256': image_sha256,
            'image_bytes': args.image.stat().st_size,
            'checkpoint_sha256': args.expected_sha256,
            'load_seconds': load_seconds, 'inference_seconds': time.monotonic() - reference,
            'plan': asdict(plan), 'model': predictor.describe(),
            'coordinate_note': 'Model-relative XY metres; physical B2/camera alignment is unverified',
            'timing_note': 'Offline replay; original capture clock is not verified or made fresh. '
                           'Waypoint interval is the adapter assumption, not a validated control period.',
            'navigation_quality_evaluated': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--base-model', required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--upstream-root', required=True)
    parser.add_argument('--instruction', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--assumed-stationary', action='store_true', required=True)
    args = parser.parse_args(argv)
    # A new report is the completion/failure record; never overwrite a run.
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        try:
            result = predict(args)
        except Exception as error:
            result = {'schema_version': 1, 'mode': 'recorded_image_assumed_stationary',
                      'passed': False, 'motion_sent': False, 'robot_connected': False,
                      'state_source': 'assumed stationary; no robot state received',
                      'error_type': type(error).__name__, 'error': str(error)}
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'passed': result['passed'], 'motion_sent': False,
                      'points': len(result.get('plan', {}).get('points', [])),
                      'output': str(args.output)}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
