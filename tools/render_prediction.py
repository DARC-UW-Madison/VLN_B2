"""Render one private recorded-image prediction as a standalone HTML inspection page.

Standard library only; no server, network access or browser automation. The
model-relative top view is separate from the photo: no calibrated projection,
obstacle map or physical B2 validation is implied.
"""

import argparse
import base64
import hashlib
import html
import json
import math
import os
from pathlib import Path


MAX_BYTES = 32 * 1024 * 1024


def render(report, image):
    if (report.get('schema_version') != 1 or report.get('passed') is not True
            or report.get('mode') != 'recorded_image_assumed_stationary'
            or report.get('motion_sent') is not False or report.get('robot_connected') is not False):
        raise ValueError('Expected a successful no-robot recorded-image demo report')
    if not 0 < len(image) <= MAX_BYTES:
        raise ValueError('Image must be nonempty and at most 32 MiB')
    if hashlib.sha256(image).hexdigest() != report.get('image_sha256'):
        raise ValueError('Image differs from the prediction input SHA256')
    if image.startswith(b'\xff\xd8\xff'):
        mime = 'image/jpeg'
    elif image.startswith(b'\x89PNG\r\n\x1a\n'):
        mime = 'image/png'
    else:
        raise ValueError('Only JPEG and PNG preview images are supported')
    points = report.get('plan', {}).get('points')
    if not isinstance(points, list) or not 0 < len(points) <= 1000:
        raise ValueError('Expected between 1 and 1000 path points')
    for point in points:
        for key in ['x', 'y', 'time_from_now']:
            value = point.get(key)
            if (not isinstance(value, (float, int)) or isinstance(value, bool)
                    or not math.isfinite(value) or abs(value) > 1000000):
                raise ValueError('Path coordinates/times must be finite bounded numbers')
    xs, ys = [0.] + [p['x'] for p in points], [0.] + [p['y'] for p in points]
    lo_x, hi_x, lo_y, hi_y = min(xs), max(xs), min(ys), max(ys)
    span_x, span_y = max(1., hi_x - lo_x), max(1., hi_y - lo_y)
    scale = 480. / max(span_x, span_y)
    mid_x, mid_y = (hi_x + lo_x) / 2., (hi_y + lo_y) / 2.

    def xy(x, y):
        return 300. - (y - mid_y) * scale, 300. - (x - mid_x) * scale

    origin_x, origin_y = xy(0., 0.)
    line = ' '.join('%.3f,%.3f' % xy(p['x'], p['y']) for p in points)
    circles = ''.join('<circle cx="%.3f" cy="%.3f" r="4"><title>Point %d: x=%.4f m, '
                      'y=%.4f m, assumed t=%.2f s</title></circle>' %
                      (*xy(p['x'], p['y']), i + 1, p['x'], p['y'], p['time_from_now'])
                      for i, p in enumerate(points))
    rows = ''.join('<tr><td>%d</td><td>%.4f</td><td>%.4f</td><td>%.2f</td></tr>' %
                   (i + 1, p['x'], p['y'], p['time_from_now']) for i, p in enumerate(points))
    instruction = html.escape(str(report.get('instruction', '')))
    state = html.escape(str(report.get('state_source', '')))
    digest = html.escape(report['image_sha256'])
    return '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TIC-VLA recorded-image prediction</title>
<style>body{font:16px/1.6 system-ui,sans-serif;background:#f3f6fa;color:#18283a;margin:0}
main{max-width:1200px;margin:auto;padding:32px}h1{line-height:1.2}.notice{background:#fff0ce;padding:16px;border-left:5px solid #b16c00}
.panels{display:grid;grid-template-columns:1fr 1fr;gap:24px}section{background:white;padding:20px;border-radius:12px;margin:20px 0;min-width:0}
img,svg{width:100%%;height:auto}svg{background:#f5f8fc}table{border-collapse:collapse;width:100%%;font-variant-numeric:tabular-nums}
th,td{padding:8px;text-align:right;border-bottom:1px solid #d6dee8}code{overflow-wrap:anywhere}.muted{color:#52667b}
@media(max-width:760px){main{padding:16px}.panels{grid-template-columns:1fr}}</style>
<main><h1>TIC-VLA recorded-image prediction</h1><p class="notice"><strong>Assumed stationary state. No robot commands.</strong><br>
This is an offline numerical prediction, not validated navigation or obstacle clearance.</p>
<p><strong>Instruction:</strong> %s</p><p class="muted">State source: %s</p>
<div class="panels"><section><h2>Input camera image</h2><img alt="Exact recorded model input" src="data:%s;base64,%s">
<p class="muted">The photo is not a calibrated path overlay.</p></section><section><h2>Predicted path: model top view</h2>
<svg role="img" aria-label="Model-relative trajectory; forward x points up and left y points left" viewBox="0 0 600 600">
<path d="M 80,565 L 80,515 M 80,565 L 30,565" stroke="#45556a" stroke-width="2" fill="none"/>
<text x="15" y="505" fill="#45556a">x forward</text><text x="15" y="590" fill="#45556a">y left ←</text>
<polyline points="%s" fill="none" stroke="#2268ba" stroke-width="3"/>
<g fill="#2268ba">%s</g><circle cx="%.3f" cy="%.3f" r="7" fill="#c23b32"><title>Assumed robot origin (0, 0)</title></circle>
<text x="300" y="28" text-anchor="middle" fill="#45556a">Distance scale: %.2f m across 480 pixels</text></svg>
<p class="muted">Red: assumed origin. Blue: future XY positions in metres, without cumulative sum.
B2/camera coordinate alignment is unverified. Hover over points for coordinates.</p></section></div>
<section><h2>Prediction coordinates</h2><p>Time uses the adapter's assumed waypoint interval.
It is not a measured control period. See the JSON report for model/timing provenance.</p>
<table><thead><tr><th>Point</th><th>Forward x (m)</th><th>Left y (m)</th><th>Assumed time (s)</th></tr></thead><tbody>%s</tbody></table>
<p>Input SHA256: <code>%s</code></p></section></main></html>''' % (
        instruction, state, mime, base64.b64encode(image).decode(), line, circles,
        origin_x, origin_y, 480. / scale, rows, digest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if not 0 < args.report.stat().st_size <= MAX_BYTES:
        raise ValueError('Report exceeds the 32 MiB input bound')
    if not 0 < args.image.stat().st_size <= MAX_BYTES:
        raise ValueError('Image exceeds the 32 MiB input bound')
    document = render(json.loads(args.report.read_text()), args.image.read_bytes())
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        stream.write(document)
    print('Wrote private inspection page: ' + str(args.output))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
