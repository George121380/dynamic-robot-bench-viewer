# Unified ACT v1

One `UnifiedACT` class now implements a shared observation backbone, gated point conditioning, the native ACT policy interface, and a separate action-conditioned dynamics interface. Optional past completion is disabled by default. This change does not start training, allocate cluster resources, or establish a performance gain.

[Anonymous architecture review](https://peiqil.com/dynamic-robot-bench-viewer/unified-act/) · [overview SVG](architecture.svg) / [PDF](architecture.pdf) · [point branch](point-branch.svg) · [Chinese detailed specification](README.zh-CN.md).

The canonical source is `dynamic_robot_bench/models/unified_act/` on isolated branch `task/unified-act`. All new tasks use this factory; task adapters may change observed state/action dimensions, cameras, physical timing, calibration, coordinates, train-only statistics and horizons. They must not introduce a task-specific DiT, GRU or policy backbone. Frozen legacy code/checkpoints remain reproducible; unrelated active worktrees are not overwritten.

## Architecture

The native LeRobot 0.4.3 ACT core keeps ResNet-18, width512, 8 heads, FFN3200, 4 encoder layers, 1 action decoder layer, 4 posterior layers and latent32. Current image tokens retain native spatial resolution. Real past frames use a 4×4 grid per camera and physical-time encoding. No fake frames fill missing history.

Each observed point has H16 slots of `[current XYZ/0.5m, past displacement/0.05m, time seconds, validity]`. A shared 128→128→128→512 ReLU MLP has99,072 parameters. Recorded camera calibration projects each point into matching historical CNN maps; valid bilinear features are averaged and projected to512. There are no point-ID/object-ID embeddings. Visual time slots are averaged; motion time structure remains explicit in the temporal MLP. This is a falsifiable initial design, not an established optimal point encoder.

After the ACT encoder, `M′ = M + tanh(g) Attn(LN(M), LN(P), LN(P))`, gate initially0.1. The native action decoder/head stays unchanged. No3NN initialization or rigid output correction is used.

- **Policy**: observations→action chunk; native normalized padded L1+10KL training objective. Evaluation uses the actual final action output, z=0, denormalization and padding exclusion for **raw action chunk MSE**, plus first-action MSE. Mixed joint/gripper units must be reported explicitly.
- **Dynamics**: observations+verified precommitted controls→future point displacement. Controls enter only the point head, never the observation backbone, actor or completion head. This baseline is called **ACT-Dynamics**; upstream ACT does not itself supply a point forecasting interface. The common point decoder and SmoothL1 objective are shared across dynamics conditions; EPE/moving EPE measure physical outputs.
- **Optional completion**: observed sparse histories+other currently observed XYZ anchors→hidden past displacements. Hidden history is supervision only, t=0 is excluded. This is past reconstruction, distinct from future forecasting.

Point heads re-encode observations with z=0 so the action posterior cannot leak future action labels into point prediction. Completion now supervises the main ACT encoder/fusion, addressing the old pre-encoder-head limitation. A point query `[XYZ,time]` uses MLP128,4-head cross-attention over projected128 memory, LN+FFN128→512→128, and a linear3 displacement output scaled by0.05m. Future and past heads have separate weights. No query self-attention means chunking128 queries preserves predictions within numerical precision. Re-encoding has a compute cost and must be reported.

## Fairness protocol

Keep native single-frame **ACT**, history-matched **ACT-H**, capacity/encoding-matched **ACT-Stationary-Tracks**, and **ACT-Tracks**. Stationary and observed tracks retain the same current anchors, timestamps, masks, point count, images, weights and architecture; only past displacement changes. Apply this change before image gathering. The old Geometry variant that also erased masks remains a historical result, not the new motion-only control.

Within each task, lock dataset/split/families, train-only statistics, pretrained CNN, ACT core initialization, sample order, seeds, effective batch, optimizer/schedule, precision, updates, validation windows/frequency, selection criterion and execution cadence. ACT-H/point models deliberately have more information and active parameters than single-frame ACT; equal allocation of bypassed extension modules is not equal effective capacity. Stationary-versus-Tracks isolates motion content at equal capacity.

Completion remains OFF initially. A detached head first tests whether reconstruction is learnable without changing actor gradients, RNG or actor clipping. Optional shared completion caps **actual full accumulated update gradients**, not a sampled microbatch: `α=min(1,0.1 ||g_primary||/||g_aux||)`. Head gradients/clipping are separate. Log raw losses, actual α, shared norm ratio, cosine and preclip norms. This cap limits magnitude, not directional conflict or guarantees of benefit.

Suggested sequence: ACT/ACT-H/Stationary/Tracks, all auxOFF; then Tracks+detached and Tracks+bounded after a reconstruction-quality gate. Current example budget is0 steps; the existing training hold remains.

## Entry points and migration boundaries

`configs/unified-act/task-registry.json` declares one model factory across garment folding, OCBench bowling, ManiSkill bowling, hook pull, stress hook pull and the native oracle-history tasks. They remain distinct data/control protocols.

`LeHomeDataset` reads the frozen cache and recorded causal camera poses. RGB-only variants never open point or trajectory archives. `pointworld.current_dynamics` bridges current RGB-D archives, shifted coordinates/calibration and **explicit raw precommitted controls**, including multiple actual cameras and absent proprioception. Repeated current clouds in old PointWorld archives are not real history; nominal robot point plans are not raw controls. Full history studies for these legacy tasks still require causal history/command exports. Old custom PointWAM/GRU datasets require conversion to the common contract, not reuse of their old model classes.

`ContractDataset` separates `obs__`, `condition__`, `target__`, verifies sample hashes and grouped splits, and requires expert-policy provenance before policy training. See [data contract](data-contract.json). Missing observations are not synthesized from future GT. Dataset provenance and full conversion remain formal-training gates; this is not a claim that every historical dataset has already been converted.

```bash
python -m dynamic_robot_bench.models.unified_act.runner preflight --config configs/unified-act/lehome-preflight.json
python -m unittest discover -s tests -p 'test_unified_act*.py' -v
```

Replace the example's cache/source paths. The `unified-act` extra pins Torch2.7.0/torchvision0.22.0/LeRobot0.4.3. Reuse the validated environment; model construction does not download weights. Provide a cached ImageNet path explicitly.

The same runner exposes explicit `train` and `evaluate` commands without scheduler submission. It contains paired deterministic sampling, full microbatch accumulation, raw-output validation, validation-only checkpoint selection, and optimizer/RNG restoration guarded by recipe/code/data fingerprints. An interrupted run retains the last complete saved update; later unsaved updates can replay. No optimizer update or long-run resume acceptance test was performed this turn, so this entry point is not yet formally training-qualified.

See `validation.json` and `real-data-check.json` for verified boundaries. CPU engineering checks do not establish CUDA/BF16 equivalence, closed-loop quality, complete cross-task export correctness or runtime efficiency. The new model has no trained weights.
