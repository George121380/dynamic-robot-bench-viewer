# Long-sleeve folding with auxiliary past-track completion

**Status: design complete; the current implementation runs the public RGB ACT reference, not an enhanced-model training run.** The executable specification for later model work is [track_aux_design.json](track_aux_design.json). The question is whether reconstructing masked **past** cloth motion improves an observation representation used for action learning.

## Architecture and objective

Use 16 observations spaced by three 90 Hz physics ticks: 0.5 seconds of RGB and motion history. Mark missing cold-start samples invalid rather than copying the current observation. Keep the current measured 12-dimensional joint state.

For the first GT upper bound, choose 64 currently visible cloth-surface mesh vertices in the union of the three camera views. Preserve their identities across the window. Provide K=16 trajectories to the actor; retain 48 as training targets. No gripper tracks. Encode fixed-world current XYZ, past-minus-current displacement, negative relative time, and validity masks. Divide spatial quantities by a fixed 0.5 m scale. Save visibility separately from validity: simulator positions behind occlusion are privileged GT, not evidence of a deployable tracker.

Use a two-layer temporal Transformer and a two-layer cross-point Transformer, width 256 and four heads, projected to ACT width 512. Shared ResNet18 RGB features yield 4×4 tokens per camera/frame with camera/time embeddings. The shared observation representation and current joints condition ACT's 100×12 action chunk, initially retaining 100 executed actions per chunk.

The auxiliary decoder receives the observation representation and training-only queries consisting of each hidden point's current XYZ and negative time. Predict 48×15×3 past displacements. **Branch before ACT's CVAE action posterior**: the posterior sees future expert action chunks during training, so neither its latent nor action-decoder features influenced by it may reach completion. Hidden query coordinates and completion predictions never enter the actor. Remove the auxiliary head at inference.

Jointly optimize `L_ACT + 0.1 L_history`, retaining ACT KL weight 10. History loss is masked SmoothL1 on normalized displacement, excluding the current timestamp and invalid entries, normalized by valid element count. Log action and auxiliary gradient norms on shared parameters. Tune only on validation data.

## Four formal controls

1. **RGB-H:** identical 16-frame RGB history and measured joints, with masked/null point context slots.
2. **RGB-H+Geometry:** additionally expose K current XYZ positions; mask past displacement.
3. **RGB-H+Tracks:** expose K past trajectories, with action loss only.
4. **RGB-H+Tracks+Completion:** identical inference inputs to control 3; add the auxiliary training loss.

These comparisons isolate geometry, motion history, and auxiliary supervision. Match model skeleton/context slots, paired initialization, data ordering and optimization budgets. Initial proposal: seeds 1000/1001/1002, 30,000 optimizer steps, effective batch 16, learning rates 1e-5, microbatch 1 and accumulation 16. Profile memory before training and use backbone frame chunking/checkpointing if required. Report parameter counts, compute and latency; equal steps do not imply equal compute.

The downloaded single-frame public ACT checkpoint has incompletely pinned training provenance. It is a pipeline/reference result and cannot serve as a fair control for newly trained enhanced models. Retrain all four formal controls on the same frozen split.

## Data and causality

Replay official expert controls from the **unmerged** source with unambiguous garment/local-episode/initial-pose identity. Save newly rendered RGB synchronized with persistent mesh positions, camera calibration, per-physics-tick time, visibility and controls. Never pair original recorded RGB with GT from a separate replay. New data must use `obs[t] -> action[t] -> physics -> obs[t+1]`; the old collection path reads observations after applying actions, so its alignment must not be assumed equivalent.

Split garments before generating windows: Seen_0–7 train, Seen_8 validation, Seen_9 offline test. Future freshly frozen online cases use Seen_9 and Unseen_0/1. The current twenty episodes are development checks, not an untouched final test. Fingerprint source revisions, poses/scales, RNG state, mesh topology/IDs and camera projection.

A GT upper bound does not establish deployability. A later RGB tracker must use the observed prefix only; whole-episode bidirectional tracking followed by truncation leaks future information. Retrain or fine-tune on estimated tracks with realistic occlusion, drift, missing points and masks. RGB-only deployment additionally requires causal metric 3D world-coordinate estimation; pixel tracks cannot be substituted for XYZ. Do not silently use simulator depth. If observed depth is used, name the condition RGB-D and add a matched RGB-D control.

## Required later acceptance checks

These are requirements for the future implementation, not tests claimed as executed now: replacing hidden targets must not alter actor conditions; replacing future expert actions must not alter completion; replacing auxiliary queries must not alter actor output; persistent identity, timing and camera projection must agree; a tiny batch must overfit and auxiliary gradients must reach the shared encoder; cold-start/invalid masks must work. Compare against the static-current-position completion reference and report errors on points moving more than 5 mm within the window. Judge policy benefit through paired closed-loop success, not completion error alone.

[PointZero](https://pointzero-wm.github.io/) already studies track completion and downstream policy. The proposed distinguishing question concerns **auxiliary representation learning from the same past history**; a generic claim that completion helps policies would be insufficient novelty.
