"""Sensor payload bounds and truthful metadata; no ROS or hardware imports."""

import importlib.util
import io
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace
import unittest


spec = importlib.util.spec_from_file_location(
    'onboard_sensors', Path(__file__).resolve().parents[1] / 'tools/probe_onboard_sensors.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class OnboardSensorTests(unittest.TestCase):
    def message(self, a=b'', b=b'', c=b'', stamp=1):
        return SimpleNamespace(video720p=a, video360p=b, video180p=c, time_frame=stamp)

    def test_video_keeps_one_resolution_and_never_exceeds_compressed_limit(self):
        buffer = probe.VideoBuffer(6)
        buffer.add(self.message(a=b'large', b=b'ab', c=b'tiny'))
        buffer.add(self.message(a=b'large', b=b'', c=b'xyz', stamp=2))
        buffer.add(self.message(b=b'cdef', stamp=3))
        buffer.add(self.message(b=b'g', stamp=4))
        self.assertEqual(buffer.field, 'video360p')
        self.assertEqual(b''.join(buffer.parts), b'abcdef')
        self.assertEqual(buffer.size, 6)
        self.assertEqual((buffer.first_time_frame, buffer.last_time_frame), (1, 3))

    def test_absent_video_does_not_invent_a_frame(self):
        buffer = probe.VideoBuffer(6)
        buffer.add(self.message())
        result = probe.preview(buffer)
        self.assertFalse(result['decoded'])
        self.assertEqual(result['compressed_bytes'], 0)
        self.assertFalse(result['image_timestamp_verified'])
        self.assertNotIn('jpeg_base64', result)

    def test_nonfinite_sensor_values_are_explicitly_missing(self):
        self.assertEqual(probe.finite_values([1., float('nan'), float('inf')]), [1., None, None])

    def test_invalid_scope_and_duration_fail_before_ros_import(self):
        for flags in [['--interface', 'eth0', '--domain-id', '0', '--seconds', 'nan'],
                      ['--interface', 'eth0</x>', '--domain-id', '0'],
                      ['--interface', 'eth0', '--domain-id', '233']]:
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                probe.main(flags)


if __name__ == '__main__':
    unittest.main()
