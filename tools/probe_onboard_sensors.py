"""Bounded, subscription-only B2 sensor probe for an existing ROS 2 host.

Python 3.8+; source the matching ROS/message workspace before running. Images
are optional derived previews in private JSON output, not calibrated model inputs.
No publisher, robot client, service request, package install or file write.
"""

import argparse
import base64
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import time


VIDEO_TOPICS = ['/front_videohub/videostream', '/back_videohub/videostream',
                '/panorama_videohub/videostream']
STATE_TOPICS = ['/lf/sportmodestate', '/lf/odommodestate', '/lf/lowstate',
                '/wirelesscontroller', '/lio_sam_ros2/mapping/odometry',
                '/lio_sam_ros2/mapping/re_location_odometry', '/pctoimage_local']


class VideoBuffer:
    """Retain one resolution only, with a strict compressed-byte limit."""

    def __init__(self, limit):
        self.limit = limit
        self.parts = []
        self.size = 0
        self.field = None
        self.first_time_frame = None
        self.last_time_frame = None

    def add(self, message):
        if self.field is None:
            self.field = next((key for key in ['video360p', 'video180p', 'video720p']
                               if len(getattr(message, key))), None)
        if self.field is None:
            return
        data = getattr(message, self.field)
        if not len(data) or len(data) > self.limit - self.size:
            return
        self.parts.append(bytes(data))
        self.size += len(data)
        self.last_time_frame = int(message.time_frame)
        if self.first_time_frame is None:
            self.first_time_frame = self.last_time_frame


def preview(buffer):
    data = b''.join(buffer.parts)
    result = {'selected_field': buffer.field, 'compressed_bytes': len(data),
              'first_time_frame': buffer.first_time_frame,
              'last_time_frame': buffer.last_time_frame,
              'image_timestamp_verified': False, 'decoded': False}
    if not data:
        return result
    result['compressed_sha256'] = hashlib.sha256(data).hexdigest()
    result['first_chunk_prefix_hex'] = buffer.parts[0][:24].hex()
    result['annex_b_header_octets'] = sorted({data[m.end()] for m in
                                            re.finditer(b'\x00\x00\x00?\x01', data)
                                            if m.end() < len(data)})[:32]
    try:
        from PIL import Image
        if not data.startswith(b'\xff\xd8\xff'):
            executable = shutil.which('ffmpeg')
            if executable is None:
                raise RuntimeError('Existing ffmpeg is required for compressed video')
            completed = subprocess.run(
                [executable, '-nostdin', '-hide_banner', '-loglevel', 'error',
                 '-threads', '1', '-i', 'pipe:0', '-frames:v', '1',
                 '-f', 'image2pipe', '-vcodec', 'mjpeg', 'pipe:1'],
                input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8)
            result['decoder_exit'] = completed.returncode
            if completed.returncode or not completed.stdout:
                raise RuntimeError('No frame decoded: ' + completed.stderr.decode(errors='replace')[:300])
            data = completed.stdout
        image = Image.open(io.BytesIO(data))
        if not 0 < image.width <= 8192 or not 0 < image.height <= 8192:
            raise ValueError('Unexpected preview dimensions')
        image.load()
        encoded = io.BytesIO()
        image.convert('RGB').save(encoded, format='JPEG', quality=85)
        payload = encoded.getvalue()
        result.update(decoded=True, width=image.width, height=image.height,
                      jpeg_sha256=hashlib.sha256(payload).hexdigest(),
                      jpeg_base64=base64.b64encode(payload).decode('ascii'))
    except Exception as error:
        result['decode_error'] = type(error).__name__ + ': ' + str(error)[:400]
    return result


def finite_values(values):
    return [float(v) if math.isfinite(float(v)) else None for v in values]


def summary(message):
    if hasattr(message, 'mode') and hasattr(message, 'velocity'):
        return {'mode': int(message.mode), 'position': finite_values(message.position),
                'velocity': finite_values(message.velocity),
                'rpy': finite_values(message.imu_state.rpy),
                'yaw_speed': finite_values([message.yaw_speed])[0]}
    if hasattr(message, 'motor_state'):
        return {'joint_slots': len(message.motor_state),
                'joint_positions': finite_values([m.q for m in message.motor_state]),
                'imu_rpy': finite_values(message.imu_state.rpy),
                'imu_gyro': finite_values(message.imu_state.gyroscope),
                'imu_accelerometer': finite_values(message.imu_state.accelerometer),
                'power_v': finite_values([message.power_v])[0]}
    if hasattr(message, 'keys'):
        return {'keys': int(message.keys),
                'sticks': finite_values([message.lx, message.ly, message.rx, message.ry])}
    if hasattr(message, 'pose') and hasattr(message, 'header'):
        p = message.pose.pose.position
        return {'frame_id': message.header.frame_id, 'child_frame_id': message.child_frame_id,
                'position': finite_values([p.x, p.y, p.z]),
                'source_stamp': {'sec': message.header.stamp.sec,
                                 'nanosec': message.header.stamp.nanosec}}
    if hasattr(message, 'point_step'):
        return {'width': int(message.width), 'height': int(message.height),
                'point_step': int(message.point_step), 'data_bytes': len(message.data)}
    return {'fields': message.get_fields_and_field_types()}


def run(args):
    import rclpy
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
    from rosidl_runtime_py.utilities import get_message

    rclpy.init(args=['--ros-args', '--disable-rosout-logs', '--disable-external-lib-logs'])
    node = rclpy.create_node('b2_passive_sensor_probe', enable_rosout=False,
                            start_parameter_services=False)
    report = {'schema_version': 1, 'mode': 'passive_onboard_sensor_probe',
              'actuation_requests_sent': False, 'interface': args.interface,
              'domain_id': args.domain_id, 'topics': {}, 'previews': {}}
    buffers = {topic: VideoBuffer(8 * 1024 * 1024) for topic in VIDEO_TOPICS}
    subscriptions = []
    try:
        end = time.monotonic() + 2
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=0.1)
        graph = dict(node.get_topic_names_and_types())
        report['discovered_sensor_topics'] = {
            name: types for name, types in graph.items()
            if any(key in name.lower() for key in ['video', 'camera', 'image', 'lidar', 'livox', 'cloud', 'odom', 'imu'])}
        clouds = [name for name, types in graph.items()
                  if types == ['sensor_msgs/msg/PointCloud2']][:4]
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT,
                         durability=DurabilityPolicy.VOLATILE)
        for topic in VIDEO_TOPICS + STATE_TOPICS + clouds:
            item = report['topics'][topic] = {'received': 0, 'types': graph.get(topic, [])}
            if len(item['types']) != 1:
                item['not_subscribed'] = 'No single discovered message type'
                continue
            try:
                message_type = get_message(item['types'][0])
            except (ImportError, AttributeError, ValueError) as error:
                item['not_subscribed'] = type(error).__name__ + ': ' + str(error)[:200]
                continue

            def receive(message, name=topic):
                entry = report['topics'][name]
                entry['received'] += 1
                if name in buffers:
                    entry['last_sizes'] = {key: len(getattr(message, key))
                                           for key in ['video720p', 'video360p', 'video180p']}
                    if args.include_images:
                        buffers[name].add(message)
                else:
                    entry['last_sample'] = summary(message)

            subscriptions.append(node.create_subscription(message_type, topic, receive, qos))
        started = time.monotonic()
        end = started + args.seconds
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=0.1)
        report['observation_seconds'] = time.monotonic() - started
        for topic, item in report['topics'].items():
            item['publisher_count'] = node.count_publishers(topic)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    if args.include_images:
        report['previews'] = {topic: preview(buffer) for topic, buffer in buffers.items()}
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interface', required=True)
    parser.add_argument('--domain-id', type=int, required=True)
    parser.add_argument('--seconds', type=float, default=8.)
    parser.add_argument('--include-images', action='store_true',
                        help='Include derived JPEGs in private stdout JSON; never publish this output')
    args = parser.parse_args(argv)
    if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,64}', args.interface):
        parser.error('Specify an explicit valid native robot interface')
    if not 0 <= args.domain_id <= 232 or not math.isfinite(args.seconds) or not 0 < args.seconds <= 15:
        parser.error('Domain must be 0..232 and duration must be 0..15 seconds')
    os.environ.update(ROS_DOMAIN_ID=str(args.domain_id), ROS_LOCALHOST_ONLY='0',
                      RMW_IMPLEMENTATION='rmw_cyclonedds_cpp')
    os.environ['CYCLONEDDS_URI'] = ('<CycloneDDS><Domain><General><NetworkInterfaceAddress>'
                                   + args.interface + '</NetworkInterfaceAddress>'
                                   '<AllowMulticast>true</AllowMulticast></General></Domain></CycloneDDS>')
    print(json.dumps(run(args), allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
