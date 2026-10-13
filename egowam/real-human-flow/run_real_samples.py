"""Actually run published Track4World/DA3 on three public EgoWAM human videos.

This is offline RGB-only tracking, not future prediction and not a metric GT test.
Existing read-only model/environment caches are reused; output stays task-owned.
"""
import argparse
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import cv2
import numpy as np
import torch
import torch.nn.functional as F

QUERIES = {
    'cup': [(202, 110), (529, 48), (551, 216), (164, 400), (202, 379), (431, 382)],
    'fold': [(157, 68), (399, 98), (106, 310), (310, 250), (347, 180), (508, 256)],
    'bag': [(210, 141), (479, 107), (329, 285), (221, 378), (406, 364), (561, 334)],
}
LABELS = {
    'cup': ['门框', '海报', '桌面后缘', '杯口', '杯把', '杯碟'],
    'fold': ['白板边缘', '墙面竖条', '桌边', '衣服图案', '领口附近', '右侧衣料'],
    'bag': ['门框', '海报', '桌面后缘', '纸袋', '饮料瓶', '右侧罐体'],
}


def digest(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(2**20), b''): h.update(b)
    return h.hexdigest()


def main(args):
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.mps.set_per_process_memory_fraction(0.65)
    spec = importlib.util.spec_from_file_location('readonly_track4world_adapter', args.adapter)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    model, audit = helper.load_model(args.source, args.checkpoint, 'mps')
    checkpoint_hash = digest(args.checkpoint)
    assert checkpoint_hash == '6c589c0f41632a2329920087dcd8cbd6465d4198d574f0d4186eeada78c492c7'
    for key in ['cup', 'fold', 'bag']:
        folder = args.data / key
        folder.mkdir(exist_ok=True)
        if (folder / 'status.json').exists():
            print('Cached task result', key, flush=True)
            continue
        cap = cv2.VideoCapture(str(args.data / (key + '.mp4')))
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        selection = np.rint(np.linspace(0, count - 1, 32)).astype(int)
        frames = []
        for i in selection:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
            ok, im = cap.read()
            assert ok
            frames.append(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
        cap.release()
        images = np.stack(frames)
        T, H, W = images.shape[:3]
        nh, nw = (448, 600)
        resized = np.stack([cv2.resize(im, (nw, nh), interpolation=cv2.INTER_LINEAR) for im in images])
        queries = np.asarray(QUERIES[key], np.float32)
        q = (queries + 0.5) * [nw / W, nh / H] - 0.5
        video = torch.from_numpy(resized).permute(0, 3, 1, 2)[None].float().to('mps')
        geometry = []
        original = model.backbone.inference_v2
        def capture(*a, **kw):
            result = original(*a, **kw)
            geometry.append({k: result[k].detach().float().cpu().numpy() for k in ['intrinsics', 'extrinsics']})
            return result
        model.backbone.inference_v2 = capture
        print('RUN', key, T, 'frames', count / fps, 'seconds', flush=True)
        torch.mps.synchronize()
        started = time.perf_counter()
        try:
            with torch.inference_mode(), torch.autocast(device_type='mps', dtype=torch.float16):
                raw = model.forward_sliding(video, iters=4, is_training=False, tracking3d=True)
            torch.mps.synchronize()
        finally:
            model.backbone.inference_v2 = original
        elapsed = time.perf_counter() - started
        flow2, confidence, _, _, flow3, _, points, mask, _, world_points, poses = raw
        assert len(geometry) == 1
        def sample(values):
            grid = torch.tensor(q, device=values.device, dtype=values.dtype)
            grid = (grid + 0.5) / torch.tensor([nw, nh], device=grid.device, dtype=grid.dtype) * 2 - 1
            grid = grid[None, None].expand(T, 1, -1, -1)
            return F.grid_sample(values[:T].float(), grid.float(), align_corners=False).squeeze(2).permute(0, 2, 1).cpu().numpy()
        uv = (sample(flow2[0]) + q + 0.5) * [W / nw, H / nh] - 0.5
        probability = sample(confidence[0])
        camera = sample(flow3[0].float().cpu() + points[:1].float().cpu())
        source_confidence = sample(mask[:1].expand(T, -1, -1, -1))[..., 0]
        c2w = poses[:T].float().cpu().numpy()
        world = np.einsum('tij,tnj->tni', c2w[:, :3, :3], camera) + c2w[:, None, :3, 3]
        reference = np.linalg.inv(c2w[0])
        world = world @ reference[:3, :3].T + reference[:3, 3]
        c2w = np.einsum('ij,tjk->tik', reference, c2w)
        intrinsics = geometry[0]['intrinsics'][0, :T].copy()
        dh, dw = nh // 14 * 14, nw // 14 * 14
        intrinsics[:, 0] *= W / dw
        intrinsics[:, 1] *= H / dh
        intrinsics[:, 0, 2] += 0.5 * W / dw - 0.5
        intrinsics[:, 1, 2] += 0.5 * H / dh - 0.5
        valid = (probability[..., 0] > 0.5) & (probability[..., 1] > 0.5) & (source_confidence > 2)
        valid &= np.isfinite(camera).all(-1) & (camera[..., 2] > 0)
        valid &= (uv[..., 0] >= 0) & (uv[..., 0] < W) & (uv[..., 1] >= 0) & (uv[..., 1] < H)
        cloud = world_points[0].permute(1, 2, 0).float().cpu().numpy()[::8, ::8].reshape(-1, 3)
        colors = resized[0, ::8, ::8].reshape(-1, 3)
        finite = np.isfinite(cloud).all(1)
        cloud = cloud[finite] @ reference[:3, :3].T + reference[:3, 3]
        colors = colors[finite]
        np.savez_compressed(folder / 'tracks3d.npz', rgb=images, uv=uv, camera_xyz=camera,
            world_xyz=world, valid=valid, probability=probability, source_confidence=source_confidence,
            camera_to_reference=c2w, intrinsics=intrinsics, timestamp=selection / fps,
            source_index=selection, queries=queries, cloud=cloud, cloud_colors=colors)
        np.savez_compressed(folder / 'joint_geometry.npz', points=points[:T].permute(0, 2, 3, 1).float().cpu().numpy(),
            confidence=mask[:T, 0].float().cpu().numpy(), intrinsics=intrinsics, camera_to_reference=c2w)
        status = {'actual_model_run': True, 'model': 'Track4World + DA3-Giant native 3D head',
            'source_video_sha256': digest(args.data / (key + '.mp4')), 'checkpoint_sha256': checkpoint_hash,
            'frames': T, 'original_frames': count, 'fps': fps, 'original_size': [W, H],
            'network_size': [nw, nh], 'model_seconds': elapsed, 'device': 'Apple MPS',
            'torch': torch.__version__, 'queries': QUERIES[key], 'query_labels': LABELS[key],
            'query_groups': ['static_background'] * 3 + ['foreground'] * 3,
            'query_selection': 'fixed visible landmarks manually selected in the first RGB frame before inference',
            'protocol': '32 chronological uniform samples of the complete public observed clip; offline tracking uses later frames',
            'camera_compensation': 'joint DA3 estimated relative camera poses, reference=first camera',
            'Aria_VIO_available': False, 'independent_ground_truth': False,
            'scale': 'joint model-normalized units, not measured meters', 'force_projection': False,
            'smoothing': False, 'filled_occlusions': False, 'valid_fraction': float(valid[1:].mean()),
            'flow_definition': 'endpoint displacement relative to each source point at frame 0, in the reference camera',
            'limitations': 'RGB-only tracker diagnostic; not the deployed EgoWAM future-prediction head and not a full Aria-label extraction reproduction',
            'adapter_file_sha256': digest(args.adapter), 'runner_sha256': digest(__file__), **audit}
        (folder / 'status.json').write_text(json.dumps(status, indent=2, ensure_ascii=False))
        print('DONE', key, 'seconds=', round(elapsed, 2), 'valid=', round(float(valid[1:].mean()), 3), flush=True)
        del raw, video, geometry, images
        gc.collect()
        torch.mps.empty_cache()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ['data', 'source', 'checkpoint', 'adapter']:
        p.add_argument('--' + name, required=True, type=Path)
    main(p.parse_args())
