# Cloth-flow-conditioned folding policy

**Latest training entry:** [matched RGB-H/FlowACT support](training.md) adds frozen inventories, complete continuation and validation-only selection; all 23 LeHome tests pass. The 500-step numbers below remain earlier single-window engineering records, not comparable to the new garment-disjoint validation metrics. Formal training requires a frozen `--manifest`.

**Implemented: FlowACT, causal online history, synchronized GT replay collection, and four matched training conditions. All ten flow contract tests pass. Formal training and closed-loop flow-policy success rates are not complete.** This supersedes the earlier design-only implementation status. The old 14/20 score still refers exclusively to the public single-frame RGB ACT checkpoint.

`flow_policy.py` implements identical module trees for `rgb_history`, `geometry`, `tracks`, and `tracks_completion`. RGB history is uint8 `[B,16,3,3,480,640]`; a shared Frozen-BN ResNet18 with ImageNet normalization produces 4×4 tokens per camera/frame, with spatial, camera and negative-time embeddings. Backbone chunking/checkpointing limits activation memory. Joint state is measured 12D radians.

Cloth history is `[B,K=16,T=16,XYZ=3]` in world meters over the same 0.5-second observation window. Features are current position, past-minus-current displacement, negative relative time and validity, with a fixed 0.5 m spatial scale. Two temporal and two cross-point Transformer layers (width 256) project to width 512. Mesh indices associate history only; there is no semantic-ID embedding. A two-layer shared observation encoder precedes the four-layer ACT encoder and one-layer action decoder. The training posterior has four layers and a 32D latent; inference uses latent zero and emits 100×12 denormalized joint targets.

The auxiliary decoder branches from observation-only memory **before** the future-action CVAE posterior. Hidden current XYZ/time queries produce 48×15×3 past displacements. Hidden targets/queries and completion outputs never condition the actor. The entire auxiliary head can be removed for inference. The joint objective is action L1 + 10×KL + 0.1×masked SmoothL1, normalized over valid past entries.

`flow_data.py` provides offline windows and `FlowHistory`. Push every 90 Hz physics observation, including steps consuming queued actions; histories sample every three ticks. Missing cold-start observations are masked rather than repeated. Reset both `FlowHistory` and `FlowPolicy` between episodes. The online interface accepts no future actions or hidden supervision. Garments are split before windows: Seen_0–7 train, Seen_8 validation, Seen_9 test.

`collect_flow.py`, through `run.sh collect-flow`, automatically replays existing official controls and saves synchronized lossless RGB, persistent cloth world vertices, camera calibration/poses, visibility, measured joints and every physics tick. Depth is used only for current visible-surface selection, never as actor input. Cameras refresh every step; physics/actions are unchanged. Visibility is an approximate three-camera depth-consistency test (1 cm, 3×3 neighborhood). Occluded-past GT positions are privileged upper-bound inputs. No RGB tracker is implemented. Merged data is restricted to unambiguous episode zero; other episodes require an unmerged single-garment source rather than guessed local-ID offsets.

`train_flow.py` trains all conditions from paired initialization and logs action/auxiliary gradients in the shared encoder. It saves input statistics with model checkpoints. `--pilot --tiny --overfit-index 60 --steps 100 --accumulate 1 --lr 0.0003` is explicitly an engineering overfit check: small Transformers, full ResNet18, native RGB resolution. Formal defaults are 30000 steps, effective batch 16 and lr 1e-5. The [Chinese instructions](flow-model.zh-CN.md) include runnable commands and job names.

Ten tests in `tests/test_lehome_flow.py` cover current-visible selection, ROS projection, hidden-target/query isolation, future-action isolation during training, actual flow influence, auxiliary shared gradients, cold/empty/NaN masks, paired initialization/permutation behavior, checkpoint/queue reset, and offline/online identity/time/action alignment. Full-resolution real-data validation and pilot receipts belong in `flow-validation.json`; tiny tests do not substitute for them.

Outstanding formal work: complete garment-disjoint synchronized data, four conditions at equal budgets and multiple seeds, paired unseen-garment closed-loop success rates, then causal estimated RGB tracks. Report the static-position baseline and moving-point (>5 mm) errors; lower completion error alone does not establish a policy improvement.

## Executed numerical checks

The full 74,929,807-parameter architecture completed native-resolution forward/backward in 4.45 s, peaking at 0.97 GiB allocated CUDA memory (single-batch check, not full optimizer training memory). Auxiliary shared gradients are nonzero, gradients finite, and removing the head changes actions by exactly zero. Replay produced 315 actions, 316 observations, 14746 cloth vertices and 948 lossless RGB files; all 951 artifacts match full SHA-256 between Mac and Baidu.

Three small-Transformer/full-ResNet18 runs use the same tick-180 window, 500 steps, seed 1000, batch 1, lr 3e-4 and identical initialization. Final prior-zero normalized action L1: RGB-H 0.02198, Tracks 0.02011, Tracks+Completion 0.01863. Training errors do not establish policy superiority.

**Completion quality gate failed:** all-point EPE 28.35 mm versus static 19.50 mm. For the 12 moving points, EPE is 64.07 mm versus static 75.71 mm. The earlier 100-step runs are preserved. The auxiliary head is not yet an effective trained completion model, and no flow-policy success improvement is claimed.

[Anonymous model/training/track viewer](https://peiqil.com/dynamic-robot-bench-viewer/lehome/flow-model/) · [machine receipt](flow-validation.json). Source/records are synchronized through GitHub to Mac/Baidu; gpu17 again timed out during SSH banner exchange and remains unsynchronized.
