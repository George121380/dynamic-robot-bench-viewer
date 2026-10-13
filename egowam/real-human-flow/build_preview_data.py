"""Package actual saved inference, without changing trajectories or validity masks."""
import base64
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
NAMES = {'cup': '放杯子', 'fold': '折衣服', 'bag': '装购物袋'}
source_file = ROOT / 'data/sources.json'
if not source_file.exists():
    source_file = ROOT / 'sources.json'
sources = json.loads(source_file.read_text())
print('source metadata structure', type(sources).__name__)
result, receipts = [], []

def rounded(a, n=4):
    a = np.round(a, n)
    assert np.isfinite(a).all()
    return a.tolist()

for key, name in NAMES.items():
    a = np.load(ROOT / 'data' / key / 'tracks3d.npz')
    status = json.loads((ROOT / 'data' / key / 'status.json').read_text())
    depth = float(np.median(a['world_xyz'][0, :3, 2]))
    drift = {}
    for field in ['camera_xyz', 'world_xyz']:
        d = np.linalg.norm(a[field][:, :3] - a[field][0, :3], axis=-1) / depth * 100
        drift[field] = {'per_frame_mean_percent': rounded(d.mean(1), 3),
                        'median_percent': float(np.median(d[1:])),
                        'p95_percent': float(np.percentile(d[1:], 95))}
    reproj = np.einsum('tij,tnj->tni', a['intrinsics'], a['camera_xyz'])
    reproj = reproj[..., :2] / reproj[..., 2:]
    discrepancy = np.linalg.norm(reproj - a['uv'], axis=-1)
    frames = []
    for im in a['rgb']:
        out = io.BytesIO()
        Image.fromarray(im).resize((320, 240), Image.Resampling.LANCZOS).save(
            out, format='JPEG', quality=42, optimize=True)
        frames.append('data:image/jpeg;base64,' + base64.b64encode(out.getvalue()).decode())
    cloud_idx = np.rint(np.linspace(0, len(a['cloud']) - 1, 850)).astype(int)
    record = {'id': key, 'name': name, 'frames': frames, 'timestamps': rounded(a['timestamp'], 3),
              'sourceIndices': a['source_index'].tolist(), 'labels': status['query_labels'],
              'uv': rounded(a['uv'], 2), 'reprojection': rounded(reproj, 2),
              'camera': rounded(a['camera_xyz']), 'world': rounded(a['world_xyz']),
              'valid': a['valid'].astype(int).tolist(),
              'cloud': rounded(a['cloud'][cloud_idx]), 'colors': a['cloud_colors'][cloud_idx].tolist(),
              'depth': round(depth, 5), 'drift': drift,
              'source': 'https://gatech-rl2.github.io/egowam.github.io/videos/data/' + key + '_inwild_0.mp4',
              'validFraction': round(float(a['valid'][1:].mean()), 5),
              'reprojectionMedian': round(float(np.median(discrepancy)), 2)}
    result.append(record)
    receipt = {'sample': key, 'name': name, 'source': record['source'], 'status': status,
               'background_reference_depth_model_units': depth,
               'static_self_consistency': drift,
               'metric_definition': 'For 3 manually selected presumed-static background queries, endpoint displacement from sample 0 divided by the median initial estimated background Z. Median and p95 pool all 31 later samples x 3 points, without validity filtering. Not GT error or metric-unit accuracy.',
               'background_valid_fraction': float(a['valid'][1:, :3].mean()),
               'foreground_valid_fraction': float(a['valid'][1:, 3:].mean()),
               'native_2d_3d_projection_difference_px_median': float(np.median(discrepancy)),
               'native_2d_3d_projection_difference_px_p95': float(np.percentile(discrepancy, 95)),
               'preview': 'All 32 actual sampled frames, JPEG preview320x240q42; 850 real estimated first-frame cloud points; 3D rounded to 4 decimals; all six tracks and masks retained.'}
    receipts.append(receipt)
payload = json.dumps({'samples': result}, separators=(',', ':'), ensure_ascii=False)
(ROOT / 'preview-data.json').write_text(payload)
(ROOT / 'measurement-receipt.json').write_text(json.dumps(receipts, indent=2, ensure_ascii=False))
print('actual-data JSON bytes:', len(payload.encode()))
for r in receipts:
    print(r['sample'], 'camera/reference median normalized drift',
          r['static_self_consistency']['camera_xyz']['median_percent'],
          r['static_self_consistency']['world_xyz']['median_percent'])
