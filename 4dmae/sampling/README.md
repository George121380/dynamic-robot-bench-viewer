# Point sampling preview

Implemented an independent sampling prototype and an English interactive viewer. No policy, tokenizer, decoder, training configuration or dataset loader was changed. This artifact is for reviewing the proposed sampling behavior before training integration.

Viewer: https://peiqil.com/dynamic-robot-bench-viewer/4dmae/sampling/

## Implemented behavior

- PullCubeTool demonstration `traj_416`, environment seed 420, frames 255 / 510 / 765. Camera geometry is fixed; RGB is rendered at 512 × 512 from saved simulation states without physics steps.
- Ten sampling seeds (0–9), with three independent seed selectors displayed side by side.
- Scene sampling: 24 points, randomly split into 12 condition and 12 query points. `stratified_random` takes one valid visible pixel per 4 × 6 image cell. `dino_diversity` starts with six points from a randomly permuted stratified set, then selects 18 by farthest-minimum joint feature/spatial distance. The distance is 0.75 × cosine distance / 2 + 0.25 × squared normalized image distance / 2. One randomly located valid candidate is drawn per DINO patch.
- Object holdout: cube, tool or gripper is selected as the query entity. Cube/tool each receive three points; gripper receives three per visible rigid part (palm, left finger, right finger). Finger pads belong to their corresponding finger. Selection is random first point, farthest second point, maximum triangle area third point in current world coordinates. Missing or degenerate candidates may reduce the count. The current three frames all yield the full count.
- Condition consists of the other selected entities plus three uniformly sampled visible static background points. The robot arm is eligible for scene sampling but is not an extra semantic entity in this object-holdout prototype.
- Counts: cube/tool holdout = 15 C + 3 Q; gripper holdout = 9 C + 9 Q. No target history point enters condition. RGB appearance and query anchors stay visible.
- Optional C history and explicitly labeled Q reference history. Reference trajectories are reconstructed by transforming each current surface anchor into its physical body's coordinates and applying saved poses. The 16 historical states cover 0.75 s at 20 Hz. Fifteen future states are included in the downloadable reference data but are never consulted for selecting points. Past occlusion does not invalidate these oracle tracks.
- A standalone offline HTML contains all interactive data and images. Static downloads are separate files; the dynamic PNG exporter also works from the single HTML. Three 3840 × 2160 figures and their editable SVG sources are provided. The 512 × 512 source images are enlarged inside these figures, not rerendered at 4K.

## Evidence and limitations

All 150 sample sets (3 frames × 5 modes × 10 seeds; 3,060 point records) pass seed reproducibility, seed variation, unique C/Q membership, current visibility, whole-entity exclusion and anchor round-trip checks. Invalidating all future body poses leaves every selected index unchanged. Zeroing DINO features changes the selected sets in all 30 scene/frame/seed comparisons. The maximum world-to-image projection residual is 0.002491 px; restored cube/tool pose error is zero.

This is one demonstration, not a model-performance comparison. Across these three frames and ten seeds, random sampling selects an average of 19.23 background points out of 24; DINO selects 16.20. DINO diversity does not guarantee small-object coverage. The fixed camera leaves only 10–14 visible pixels on the left finger, and sampled finger anchors can be approximately one pixel apart. Three non-collinear noiseless 3D correspondences can determine a rigid transform; three almost coincident image points are not a robust practical guarantee. The tool and gripper are partly outside the image. These limitations are retained in the preview for design review.

`proposed_training_mode_weights` in the JSON is a proposal (0.5 scene / 0.5 object holdout), not an active training mechanism. The preview explicitly selects each mode. Main training configuration, actual mixture dispatch, visibility/conditioning thresholds, and the shared-token model change remain future work pending sampling review.

## Reproduction and files

Source scripts are in `scripts/`; raw render geometry and features in `raw/`; numerical reports and rendering logs in `qa/`; deliverables in `public/`. Run from this directory with a Python environment containing NumPy, OpenCV, PyTorch, torchvision and Pillow:

```sh
python scripts/extract_dino.py --root .
python scripts/build_samples.py --root .
python scripts/verify_samples.py --root .
python scripts/build_viewer.py --root .
node scripts/build_figures.mjs .
inkscape public/seed-comparison.svg --export-width=3840 --export-filename=public/seed-comparison.png
inkscape public/object-holdout.svg --export-width=3840 --export-filename=public/object-holdout.png
inkscape public/sampling-methods.svg --export-width=3840 --export-filename=public/sampling-methods.png
```

To regenerate the raw inputs, `scripts/export_scene.py --source <benchmark-data-dir> --output raw` additionally needs SAPIEN 3.0.3, ManiSkill and the existing demonstration HDF5/index. The renderer used the verified ManiSkill commit `95ea99d4eaad36477823d97077ab935caeb73359` and pinned task source hash. The DINOv2 model is the official frozen `dinov2_vits14_reg`, repo commit `7764ea0f912e53c92e82eb78a2a1631e92725fc8`. Full source/checkpoint hashes and per-frame visibility counts are in `public/verification.json`.

Rendering was completed on one idle developer GPU; DINO inference ran locally on CPU. No training job or whole-node allocation was created. Publication uses the existing viewer repository's `4dmae/sampling/` directory in an isolated worktree.
