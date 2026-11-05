"""Recorded-image demo guards and truthful standalone output, without GPU/models."""

from argparse import Namespace
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from b2_tic_vla.types import Plan, Waypoint


def load_tool(name):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parents[1] / 'tools' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


predictor_tool, renderer = load_tool('predict_image'), load_tool('render_prediction')


class ImageDemoTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.image = self.root / 'frame.jpg'
        self.image.write_bytes(b'\xff\xd8\xfftest image')
        self.checkpoint = self.root / 'model.safetensors'
        self.checkpoint.write_bytes(b'fixture tensor data')
        self.args = Namespace(image=self.image, checkpoint=self.checkpoint,
                              expected_sha256=hashlib.sha256(self.checkpoint.read_bytes()).hexdigest(),
                              assumed_stationary=True, instruction='Move ahead.',
                              base_model='unused', upstream_root='unused')
        self.plan = Plan((Waypoint(1., .2, .1), Waypoint(2., .4, .2)), 100., 90., 'test')

    def report(self):
        return {'schema_version': 1, 'passed': True, 'mode': 'recorded_image_assumed_stationary',
                'motion_sent': False, 'robot_connected': False,
                'instruction': '<script>alert("test")</script>',
                'state_source': 'assumed stationary; no robot state received',
                'image_sha256': hashlib.sha256(self.image.read_bytes()).hexdigest(),
                'plan': json.loads(json.dumps(asdict(self.plan)))}

    def test_offline_and_assumption_guards_precede_model_construction(self):
        with patch('b2_tic_vla.inference.TicVlaPredictor') as constructor:
            with patch.dict('os.environ', {'HF_HUB_OFFLINE': '0'}), self.assertRaises(ValueError):
                predictor_tool.predict(self.args)
            self.args.assumed_stationary = False
            with patch.dict('os.environ', {'HF_HUB_OFFLINE': '1'}), self.assertRaises(ValueError):
                predictor_tool.predict(self.args)
            constructor.assert_not_called()

    def test_original_checkpoint_and_wrong_hash_are_rejected_before_loading(self):
        with patch('b2_tic_vla.inference.TicVlaPredictor') as constructor, \
             patch.dict('os.environ', {'HF_HUB_OFFLINE': '1'}):
            for checkpoint, digest in [(self.root / 'model.ckpt', self.args.expected_sha256),
                                       (self.checkpoint, '0' * 64)]:
                self.args.checkpoint, self.args.expected_sha256 = checkpoint, digest
                with self.assertRaises(ValueError):
                    predictor_tool.predict(self.args)
            constructor.assert_not_called()

    def test_prediction_preserves_points_and_labels_fake_state(self):
        model = Mock()
        model.load.return_value = model
        model.predict.return_value = self.plan
        model.describe.return_value = {'loaded': True}
        with patch('b2_tic_vla.inference.TicVlaPredictor', return_value=model), \
             patch.dict('os.environ', {'HF_HUB_OFFLINE': '1'}):
            report = predictor_tool.predict(self.args)
        self.assertEqual(report['plan'], asdict(self.plan))
        self.assertFalse(report['motion_sent'])
        self.assertFalse(report['robot_connected'])
        self.assertIn('assumed stationary', report['state_source'])
        args = model.predict.call_args.args
        self.assertEqual((args[2].vx, args[2].vy, args[2].yaw_rate), (0., 0., 0.))

    def test_output_page_is_standalone_and_escapes_text(self):
        page = renderer.render(self.report(), self.image.read_bytes())
        self.assertIn('data:image/jpeg;base64,', page)
        self.assertIn('viewBox="0 0 600 600"', page)
        self.assertIn('id="prediction-panels"', page)
        self.assertIn('Assumed stationary state. No robot commands.', page)
        self.assertIn('&lt;script&gt;', page)
        self.assertNotIn('<script>', page)
        self.assertNotIn('src="http', page)
        self.assertIn('1.0000', page)
        self.assertIn('2.0000', page)

    def test_different_image_failed_report_and_nonfinite_points_are_not_visualized(self):
        report = self.report()
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            renderer.render(report, b'\xff\xd8\xffother')
        report['passed'] = False
        with self.assertRaises(ValueError):
            renderer.render(report, self.image.read_bytes())
        report['passed'] = True
        report['plan']['points'][0]['x'] = float('nan')
        with self.assertRaises(ValueError):
            renderer.render(report, self.image.read_bytes())

    def test_existing_html_is_not_overwritten(self):
        report = self.root / 'prediction.json'
        report.write_text(json.dumps(self.report()))
        output = self.root / 'prediction.html'
        output.write_text('Keep existing result')
        with self.assertRaises(FileExistsError):
            renderer.main(['--report', str(report), '--image', str(self.image),
                           '--output', str(output)])
        self.assertEqual(output.read_text(), 'Keep existing result')

    def test_generated_response_is_escaped_and_distance_uses_the_numeric_path(self):
        report = self.report()
        report['model'] = {'vlm_response': '<script>untrusted</script>\nText target: (99, 99)'}
        page = renderer.render(report, self.image.read_bytes())
        self.assertIn('Generated VLM response', page)
        self.assertIn('&lt;script&gt;untrusted&lt;/script&gt;', page)
        self.assertNotIn('<script>', page)
        self.assertIn('Text target: (99, 99)', page)
        self.assertIn('x=2.000 m, y=0.400 m', page)
        self.assertIn('distance from origin: 2.040 m', page)
        self.assertIn('path length from origin: 2.040 m', page)
        self.assertIn('Final sample time: 0.20 s', page)

    def test_old_reports_do_not_invent_a_response_and_invalid_text_is_rejected(self):
        report = self.report()
        self.assertIn('No VLM response was recorded', renderer.render(report, self.image.read_bytes()))
        report['model'] = {'vlm_response': ['not', 'text']}
        with self.assertRaisesRegex(ValueError, 'VLM response'):
            renderer.render(report, self.image.read_bytes())


if __name__ == '__main__':
    unittest.main()
