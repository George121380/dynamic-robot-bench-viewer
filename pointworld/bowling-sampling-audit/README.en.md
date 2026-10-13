# Bowling sampling and scale audit

**Verified: small-object resolution is a credible concern, but the adapter also has a correctable RGB-D consistency issue and substantial time/action distribution shifts. The current failure does not establish PointWorld's multi-object capability limit.** This round reads 296 existing inputs and saved contacts, runs official CPU loaders and sampling/pooling functions, and changes no forecasts, weights or training protocol.

[Public interactive evidence](https://peiqil.com/dynamic-robot-bench-viewer/pointworld/bowling-sampling-audit/) · [Chinese evidence](README.zh-CN.md) · [Archived forecasts](https://peiqil.com/dynamic-robot-bench-viewer/pointworld/bowling-v3/)

## Sampling does not remove the pins

Across 296 inputs and 2,960 pins, each pin has 49–174 input points, median 96. Official deterministic test-mode 1.5 cm voxel sampling retains 20–54, median 37; training randomly picks a point in each voxel. The adapter's `batch_from_arrays` calls `gather_features` without `grid_sample_transform`: median scene count is 1,804 versus 942 after release sampling, and robot count is 500 versus median 189 per timestep. Inputs are already denser; density mismatch may still affect pretrained sparse-convolution features. No accuracy gain from restoring sampling has been demonstrated.

The small-DROID model's four stride-two pools give 1.5 / 3 / 6 / 12 / 24 cm grid widths. Seed3004 pins occupy 30–52 base cells, 3–9 cells at 6 cm, and 1–2 cells at 24 cm, where they mix with other scene points. Fine decoder points and skip connections remain; coarse grouping does not delete objects.

Eight inputs spanning all four splits match the official FNV sampler's scene and robot indices exactly. CPU Torch depth-gate masks differ from the NumPy reconstruction at zero points in both cameras. Actual `GridPooling.forward(skip_postprocess=True)` cluster counts match the reconstructed counts at every level. This executes real clustering and torch_scatter reduction, skipping sparse-tensor construction/postprocessing that does not change cluster membership.

## A stronger interface concern: pixel resolution and resized-depth consistency

`collect_bowling.visible_inputs` backprojects 224×224 source depth. `letterbox` then resizes RGB/depth to 180×180 and pads 70 pixels on each side to 320×180. RGB uses bilinear resize, depth uses nearest; intrinsics correctly follow pixel-center scaling. The encoder bilinearly samples resized depth at projected points with a 3 mm behind / 1.5 mm front gate.

- Median selected visible pin bounds in their source view are **4.018×13.661 px**, versus DINOv3 ViT-L16's **16×16 px** patches. Fine object separation is plausibly difficult; this does not imply features contain no information or geometry disappears.
- Median per-pin coverage after combining two views is **50.0%**. Only one pin (seed76) has no valid image features in either camera.
- Median per-pin/per-source-view coverage is **39.639%**. A geometry-only diagnostic that backprojects current points directly from the *same resized depth pixels* yields **100%** own-view gate coverage, with median per-view point count decreasing from 58 to 37. This uses a different hypothetical point set, with no future labels or network forward.
- The result exposes preprocessing/depth-interpolation losses; more points alone cannot remedy them. The 100% value is pixel self-consistency, not DINO recognition quality, forecast accuracy, or an isolated causal performance ablation.
- A read-only 10 mm threshold diagnostic gives median two-view coverage 67.96%. It may mix features across surfaces and has not been evaluated as a forecast modification.

The [official limitations appendix](https://arxiv.org/html/2601.03782v1#A1) discusses thin objects under depth/calibration error. Here GT simulator depth is available, yet image resizing and feature visibility still lose information; this is distinct from estimation noise in native real-world annotations.

## Physical units match; time and motion scales do not

The compiled simulator at OCBench `6939a1e84f7ce9dbdd20c9f80d4cf335e8f83b49` has an **8.5 cm** diameter, **64.311 g** ball and **4.5448×4.5448×15.0027 cm**, **4.5 g** pin. Full body-local mesh bounds use transformed compiled vertices, not MuJoCo `geom_size` as a half-extent. Units are metres; no ×1000 conversion bug was found. Pin width is roughly three base voxels.

Native references use the official deterministic CPU train pipeline: 64 DROID clips from 8 episodes and 32 BEHAVIOR clips from 2, with geometric/color augmentation disabled but random per-voxel training selection retained. These are locked downloaded subsets, not full-corpus statistics.

- Both use Robotiq 2F-85. Median current robot XYZ spans are Bowling **13.9 / 7.5 / 16.7 cm**, DROID **7.6 / 14.0 / 16.9 cm**. Axes depend on pose; overall gripper dimensions are comparable.
- Median scene XYZ spans are Bowling **0.796 / 1.647 / 0.150 m**, DROID **0.890 / 1.597 / 1.351 m**. Height reflects foreground/table ROI versus room/background coverage. Workspace bounds are not object dimensions.
- DROID lacks passive-object GT identities, so the full pretraining object-size distribution cannot be established. BEHAVIOR/task0000 radio visible link dimensions are about 14×32×20 cm; this secondary domain did not pretrain small-DROID.
- Timestamps from all 62 restored DROID episodes have episode-median frame intervals **0.134–0.150 s**, and a median of episode-median 10-step clip durations of **1.417 s** (approximately 1.400–1.433 s). Bowling uses **0.4 s / 4 s**. Distinguish the paper's nominal one-second setting from this restored release's measured timing.
- `time_steps=torch.linspace(0,1,11)` encodes relative index, with no physical-dt input. `compute_flow_derivatives` does not divide by seconds. Median per-trajectory mean robot-point shift per step is **5.902 cm** for Bowling versus **2.082 cm** for the DROID reference.
- Under released DROID normalization, median trajectory `p95(abs(z))` for Bowling's 206 train inputs is **13.90σ** in the y velocity-like channel and **19.73σ** in the y acceleration-like channel; DROID references give **1.51σ / 1.77σ**. These are index finite differences, not m/s or m/s². Timing, paths and coordinate directions all contribute; their individual effects are unisolated.
- Official `compute_helper_variables` clips relative GT per axis at **±0.5 m**, without hard-clipping network predictions. Bowling's physical Huber uses full GT. Median episode maximum ball-axis displacement is **0.946 m**, maximum **1.506 m**. Median episode fraction of ball point/future-time targets outside any 0.5 m axis is **55.20%**; pins have zero such exceedance. Clipping Bowling GT would conceal real motion rather than solve it.

## What was ruled out, and what remains

All positive-force 500 Hz robot–ball contact rows across 296 episodes occur on Robotiq bodies covered by the current sampled gripper. Missing arm/wrist contact bodies are not the explanation, although body coverage does not prove pointwise visual/collision-mesh equality. For 122/296 episodes no sampled 0.4 s output timestamp coincides with robot–ball contact within ±2.1 ms; discrete path samples may still encode contact, so this is not proof that the action input is absent.

Previous model selection favors conservative outputs: validation step2750 has 24 TP / 19 FP / 24 FN but loses to the selected score. Selected-model 0/76 does not demonstrate an architecture limit. Do not select a different checkpoint on already-viewed tests. Query ball speed is essentially zero; missing initial ball velocity is not the simple explanation here.

The defensible conclusion is that **small-DROID with the current adapter, training and selection does not learn these fast, long-range collision cascades reliably**. The result cannot establish failure of larger PointWorld variants or all multi-object scenes.

## Next discriminating checks — training not executed

Keep physical sizes, masses and dynamics unchanged. First align post-resize RGB-D point generation and calibration, restore release sampling, and measure geometry/image-feature coverage. Check fitting on 8–16 training trajectories and short robot→ball prediction before expanding fresh hold-outs. Compare ~1.4-second/10-step windows and inspect normalized action ranges; short windows need not complete the original four-second cascade and must be reported separately. Independently change camera distance/FOV to increase pin pixels. Freeze validation tradeoffs among moving FDE, tipping detection and static false motion before new tests. Extra point density, scaling the simulation, or relaxing depth gates does not substitute for these ablations.

## Evidence and reproduction

Reports: `reports/bowling-sampling-audit.json`, `bowling-contact-scale-audit.json`, `bowling-native-reference.json`, `bowling-resized-depth-audit.json`, `bowling-sampling-function-check.json`. Sampling records include SHA256 for all 296 original NPZ files. Initial sampling source `d6465ac`, native-reference source `94202d5`, official-function-check source `9636322`. Audit/renderer scripts live under `benchmark_adapters/`; collector, training entrypoints and checkpoints are unchanged.

```bash
python -m benchmark_adapters.audit_bowling_sampling --prepared .runtime/bowling-prepared/main-v3 --raw .runtime/bowling-raw/main-v3 --output reports/bowling-sampling-audit.json --display .runtime/bowling-sampling-display
python -m benchmark_adapters.audit_bowling_rgbd --prepared .runtime/bowling-prepared/main-v3 --output reports/bowling-resized-depth-audit.json
python -m benchmark_adapters.audit_pointworld_reference --output reports/bowling-native-reference.json --batch-output .runtime/bowling-native-reference-input.npz
python -m benchmark_adapters.check_bowling_sampling --prepared .runtime/bowling-prepared/main-v3 --native .runtime/bowling-native-reference-input.npz --output reports/bowling-sampling-function-check.json
```

The first two need NumPy/h5py/Pillow; the latter two need the deployed official dependency environment. Contact geometry also needs pinned OCBench/MuJoCo: `python -m benchmark_adapters.audit_bowling_contacts --benchmark-root /path/to/benchmark --prepared .runtime/bowling-prepared/main-v3 --raw .runtime/bowling-raw/main-v3 --output reports/bowling-contact-scale-audit.json`. This round uses CPU only and adds no GPU occupancy.
