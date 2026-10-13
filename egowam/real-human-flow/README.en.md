# Real human video 3D flow diagnostic

Track4World + DA3-Giant was actually run on three public EgoWAM egocentric videos: placing a cup, folding clothes, and packing a shopping bag. The viewer synchronizes real RGB, native 2D/3D tracks and camera-compensated trajectories, retaining invalid points and residual drift. This is an RGB tracker diagnostic with no independent 3D ground truth. It does not establish centimeter accuracy or evaluate the deployed EgoWAM future-prediction head.

Public viewer: <https://peiqil.com/dynamic-robot-bench-viewer/egowam/real-human-flow/>. `README.zh.md` provides the Chinese version. `measurement-receipt.json` contains exact values, input hashes and runtime records; `sources.json` lists the original public videos.

## Observed results

The videos come from the Human In-the-Wild gallery on the [official EgoWAM website](https://gatech-rl2.github.io/egowam.github.io/), each 640×480 at 30 fps.

- Cup: 418 original frames, 13.93 s, 43.50 s model runtime. Median presumed-static background endpoint displacement / initial estimated background depth: 4.22% in per-frame camera coordinates and 3.07% after compensation. Compensated p95: 11.05%. Validity rate across six queries and subsequent samples: 45.70%.
- Clothes: 405 frames, 13.50 s, 44.21 s runtime. Background median: 18.85% → 7.32%; compensated p95: 14.96%. Validity: 56.99%.
- Bag: 604 frames, 20.13 s, 54.92 s runtime. Background median: 5.75% → 4.08%; compensated p95: 9.88%. Validity: 36.56%.

These numbers describe static self-consistency, pooling all 31 later samples × 3 background queries, including invalid outputs. They are neither ground-truth errors nor object-motion accuracy. Compensation does not improve every sample: the cup's compensated p95 exceeds its raw p95, and the bag's final average background displacement increases. Native 2D tracks and native 3D reprojections also differ; the optional crosses and receipts expose that discrepancy.

## Auditable protocol

Each complete clip is sampled into 32 chronological frames and resized to 600×448 for four-iteration sliding-window inference. Mean time steps are approximately 0.45, 0.43 and 0.65 s. Three presumed-static landmarks and three foreground landmarks are fixed manually in frame zero before inference, then sampled from actual dense outputs. Sparse sampling and long tracks mean these failure rates cannot be generalized to the official framewise label extractor.

The [official Track4World pretrained checkpoint](https://github.com/TencentARC/Track4World) was loaded strictly with all keys matching. Checkpoint SHA256: `6c589c0f41632a2329920087dcd8cbd6465d4198d574f0d4186eeada78c492c7`; model source SHA256: `4470aed42cdf8ef76df2a4ef381390459b977f006f5a666275b5603d3cc69e75`. Execution used local Apple MPS, PyTorch 2.14.1 and read-only existing caches, with no cluster GPU job. Receipts include device-adapter hashes, same-operator CPU pooling and attention zero-padding details.

Native 3D endpoints are retained without `force_projection`, then transformed by joint DA3 estimated camera poses into the first-camera reference. Coordinates use joint model-normalized units; there is no Aria VIO, calibrated camera or measured scale. This differs from EgoWAM's `infer_pair + force_projection + Aria pose` label-extraction pipeline. Later observed frames are used, making this offline tracking. No smoothing, occlusion filling or manual correction is applied.

Validity requires both native probabilities >0.5, source geometry confidence >2, finite positive depth and in-image native UV. Invalid outputs remain hollow; valid trajectories have gaps at invalid samples; offscreen points are not clamped into the image. RGB, tracks and charts share the exact sampled frame IDs; both 3D panels share the same scale.

## Files and reproduction

- `index.html` is the public standalone page; `real-human-flow.html` is the inline fragment. It contains all 32 real preview frames per clip (JPEG 320×240), 850 actual estimated first-frame cloud points per clip, six complete tracks and validity masks. Displayed 3D values are rounded to four decimals. Only pinned D3 loads from a CDN; data is embedded.
- `native-output-{cup,fold,bag}.npz` retains unrounded six-query coordinates, probabilities, masks, poses, intrinsics, original frame IDs and timestamps, without RGB or dense geometry. Receipts identify manually fixed query pixels and source hashes.
- `run_real_samples.py` is the actual runner. `track4world_device_adapter.py` is a byte-identical snapshot of the read-only adapter used during inference. `build_preview_data.py` packages previews and computes statistics without altering tracks. Public originals remain linked by `sources.json`; no private or gated data was downloaded or published.

Download the three originals from `sources.json` into `data/{cup,fold,bag}.mp4`, verifying their hashes. In an existing compatible Track4World environment on Apple MPS:

```bash
PYTORCH_ENABLE_MPS_FALLBACK=1 python run_real_samples.py \
  --data data --source /path/to/track4world-source \
  --checkpoint /path/to/track4world_da3.pth \
  --adapter track4world_device_adapter.py
python build_preview_data.py
```

The large model requires sufficient unified memory. The successful run used a 65% recommended-memory MPS cap; an earlier 35% cap attempt ran out of memory before the successful run.

Verified interactions: all three samples, first/last sampled frame IDs, native reprojection crosses, equal-scale front/side views, finite playback using original timestamps and stopping at the final sample, and 1024 / 320 px layouts. Metric accuracy requires independent camera/depth or 3D trajectory ground truth.
