"""Operator demo correctness, input identity, isolation and bounded cleanup."""

from argparse import Namespace
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from b2_tic_vla.types import Frame, Plan, Waypoint


TOOLS = Path(__file__).resolve().parents[1] / 'tools'
spec = importlib.util.spec_from_file_location('camera_demo', TOOLS / 'camera_demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class CameraDemoTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'camera/frames').mkdir(parents=True)
        (self.root / 'predictions').mkdir()
        self.image = self.root / 'camera/frames/frame-000001.jpg'
        self.image.write_bytes(b'\xff\xd8\xffcamera fixture')
        self.digest = hashlib.sha256(self.image.read_bytes()).hexdigest()

    def args(self):
        checkpoint = self.root / 'model.safetensors'
        checkpoint.write_bytes(b'fixture weights')
        return Namespace(checkpoint=checkpoint, assumed_stationary=True,
                         instruction='Move ahead.', duration=6., base_model='unused',
                         upstream_root='unused', stream=self.image.parent,
                         output=self.root / 'predictions')

    def publish_frame(self):
        manifest = {'frame': {'path': self.image.name, 'received_at': 0.},
                    'image_sha256': self.digest}
        demo.publish_json(self.image.parent / 'latest.json', manifest)

    def test_preview_and_exact_prediction_are_separated_and_stopped_page_does_not_refresh(self):
        self.publish_frame()
        demo.publish_json(self.root / 'predictions/status.json', {
            'stage': 'predicting', 'completed': 1, 'last_report': 'prediction-001.html',
            'last_input': 'frame-000001.jpg', 'inference_seconds': 12.3})
        demo.publish_view(self.root, '<script>bad</script>', True)
        page = (self.root / 'index.html').read_text()
        self.assertIn('http-equiv="refresh"', page)
        self.assertIn('not the changing preview', page)
        self.assertIn('&lt;script&gt;', page)
        self.assertNotIn('<script>', page)
        self.assertNotIn('src="http', page)
        self.assertIn('predictions/prediction-001.html', page)
        demo.publish_view(self.root, 'Go.', False, 'stopped_by_operator')
        page = (self.root / 'index.html').read_text()
        self.assertNotIn('http-equiv="refresh"', page)
        self.assertIn('stopped_by_operator', page)

    def test_preview_rejects_substituted_image_and_traversal(self):
        self.publish_frame()
        self.image.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'hash'):
            demo.publish_view(self.root, 'Go.', True)
        demo.publish_json(self.image.parent / 'latest.json', {'frame': {'path': '../secret.jpg'}})
        with self.assertRaisesRegex(ValueError, 'filename'):
            demo.publish_view(self.root, 'Go.', True)

    def test_model_is_loaded_once_and_reports_preserve_each_input(self):
        args = self.args()
        now, received = [100.], []
        model = Mock()
        def load():
            now[0] += 2
            return model
        def predict(images, instruction, state, reference):
            received.append(Path(images[0]).read_bytes())
            self.assertEqual((state.vx, state.vy, state.yaw_rate), (0., 0., 0.))
            now[0] += 2
            return Plan((Waypoint(float(len(received)), 0., .1),), now[0], reference, 'fixture')
        model.load.side_effect = load
        model.predict.side_effect = predict
        model.describe.return_value = {'loaded': True}
        factory = Mock(return_value=model)
        def observation(directory, instruction, seen, stamp):
            index = len(received) + 1
            path = self.image.with_name('frame-%06d.jpg' % index)
            path.write_bytes(b'\xff\xd8\xffinput' + str(index).encode())
            return SimpleNamespace(frame=Frame(str(path), stamp)), demo.sha256(path)
        with patch.dict('os.environ', HF_HUB_OFFLINE='1'), \
             patch.object(demo, 'CHECKPOINT_SHA', demo.sha256(args.checkpoint)), \
             patch.object(sys, 'path', [str(TOOLS)] + sys.path):
            result = demo.run_predictor(args, factory, observation, lambda: now[0])
        self.assertTrue(result['passed'])
        self.assertEqual(result['completed'], 2)
        factory.assert_called_once()
        model.load.assert_called_once()
        for i in [1, 2]:
            stem = 'prediction-%03d' % i
            report = json.loads((args.output / (stem + '.json')).read_text())
            self.assertEqual(report['image_sha256'], hashlib.sha256(received[i-1]).hexdigest())
            self.assertEqual(report['plan']['points'][0]['x'], float(i))
            self.assertFalse(report['motion_sent'])
            self.assertFalse(report['robot_connected'])
            self.assertIn('assumed stationary', report['state_source'])
            self.assertTrue((args.output / (stem + '.html')).is_file())

    def test_worker_rejects_original_pickle_or_online_mode_before_loading(self):
        args = self.args()
        factory = Mock()
        for environment, checkpoint in [('0', args.checkpoint), ('1', self.root / 'model.ckpt')]:
            args.checkpoint = checkpoint
            with patch.dict('os.environ', HF_HUB_OFFLINE=environment), self.assertRaises(ValueError):
                demo.run_predictor(args, factory)
        factory.assert_not_called()

    def test_predictor_has_no_usb_or_network_and_only_explicit_writable_outputs(self):
        inputs = {key: self.root / key for key in [
            'src', 'tools', 'camera_api', 'sdk', 'turbojpeg', 'settings',
            'base', 'checkpoint', 'upstream']}
        names, invocations = demo.commands('sha256:' + 'a'*64, inputs, self.root,
                                         [Path('/dev/video4')], 60., 'Turn left.', 44, 1002)
        camera, prediction = invocations
        self.assertEqual(len(names), 2)
        self.assertIn('/dev/video4', camera)
        self.assertNotIn('--device', prediction)
        self.assertEqual(prediction[prediction.index('--network') + 1], 'none')
        self.assertIn('Turn left.', prediction)
        self.assertNotIn('--privileged', camera + prediction)
        self.assertNotIn('/var/run/docker.sock', str(camera + prediction))
        self.assertIn('dst=/camera,readonly', ' '.join(prediction))
        self.assertIn('--assumed-stationary', prediction)
        self.assertIn('120s', prediction)

    def test_operator_interrupt_removes_both_owned_containers_and_retains_final_page(self):
        project = self.root.resolve()
        (project / 'local').mkdir()
        args = Namespace(output=project / 'local/demo-01', duration=60., instruction='Go.')
        processes = [Mock(), Mock()]
        for process in processes:
            process.poll.return_value = None
            process.returncode = -9
        original_stat = demo.os.stat
        def stat(path, *args, **kwargs):
            return original_stat(project if str(path) == '/dev/nvmap' else path, *args, **kwargs)
        with patch.object(demo, 'commands', return_value=(['own-a', 'own-b'], [['a'], ['b']])), \
             patch.object(demo.os, 'stat', side_effect=stat), \
             patch.object(demo.subprocess, 'Popen', side_effect=processes), \
             patch.object(demo.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as cleanup, \
             patch.object(demo.time, 'sleep', side_effect=KeyboardInterrupt):
            result = demo.supervise(args, project, {'sdk': project}, [], 'image')
        self.assertEqual(result, 0)
        self.assertEqual([call.args[0][-1] for call in cleanup.call_args_list], ['own-a', 'own-b'])
        summary = json.loads((args.output / 'summary.json').read_text())
        self.assertEqual(summary['outcome'], 'stopped_by_operator')
        self.assertFalse(summary['motion_sent'])
        self.assertNotIn('http-equiv="refresh"', (args.output / 'index.html').read_text())

    def test_absent_camera_does_not_guess_a_device(self):
        usb, video = self.root / 'sys_usb', self.root / 'sys_video'
        usb.mkdir()
        video.mkdir()
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            demo.discover_camera(usb, video, self.root / 'dev')


if __name__ == '__main__':
    unittest.main()
