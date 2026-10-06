# Frozen round-2 protocol

Question: with current RGB, all current point positions, current robot state and
precommitted future commands held fixed, does target history help, and does tool
history add further value?

Base code commit: 3b30fe9dd3b1d585ec512323ceb84d14390fc0d5. Implementation commit,
source-file SHA256 and artifact hashes are frozen in the run's protocol_lock.json
before formal training. config.json fixes the budget and preselected cases.
No new data, model backbone, scene or auxiliary-weight search.

Pre-training repairs: seed7-v1 completed the inherited data audit, then failed
the GPU eval-mode GRU backward loss test (cuDNN requires training mode for its
RNN backward). No smoke or formal training ran. For eval gradient tests/diagnostics
only, cuDNN is disabled while retaining eval mode; formal training stays unchanged.
A pure repeated binary3x3 segmentation maximum filter is also memoized in the
inherited audit; every original assertion still runs over all episodes/windows
and the full result must exactly match the original saved audit. No original
source/data/output is edited. Completed protocol/run: seed7-v2; v1 is retained.

Reuse original 300 episodes / 100 families / 6300 windows, 70/15/15 families;
4410/945/945 windows. Hashes of manifest, samples, metadata and frozen current-RGB
ResNet-18 cache are required to match config.json. The original audit is retained
and rerun before the comparison. Original coordinates in metres, relative
displacements, fixed 0.1m scaling, current 224px RGB anchors, 1s negative history,
0.5s future, 20Hz commands and 10Hz observations remain unchanged.

Forward whitelist: p0, current visual, current global_visual, current proprio
(9 qpos + 9 qvel), history_time, future_time, actions, current entity association,
current uv, history, availability. Entity association gates access and selects
target supervision; uv is the projection underlying the same cached anchors.
Neither adds a new embedding or changes the original network architecture.
Raw histories are replaced by zero displacement before any encoding when
forbidden, accompanied by availability=0. Current point geometry is always
preserved. H0 has no negative history, H_self only cube history, H_all both.
No random trajectory dropout, old completed histories, label statistics, absolute
episode time, past visual features, contact/stage/family metadata or future truth
is an input. Relative time grids and current joint velocity remain inputs.
Thus H0 lacks object past trajectories but retains the original robot velocities.

Same original four-layer width-256 body and future head, same slots/tokens,
dropout=0. The original history head stays in the state dict, frozen and skipped.
Only target future SmoothL1(beta=0.01m): XYZ-coordinate mean, then valid target
point/time mean per sample, then sample mean. Future t=0 is absent. Tool future
labels/validity do not contribute to loss. Original AdamW lr=3e-4,
weight_decay=1e-4, clip=1; no LR scheduler (same as round 1).

Seed 7. Create one new random common initialization checkpoint; all three formal
runs reload it, never the first-round trained models or smoke-test weights.
Same numpy seeded permutations, batch32, 10000 updates each, validate every500.
Save 2000/5000/10000 milestones, best validation episode-mean target ADE and final.
Report only validation-selected and final10000 test checkpoints. Lock all six
checkpoint hashes after training and before one unified test evaluation.
Seeds17/27 are configuration only. No continuation based on observed scores.

Pre-training gates: complete raw preprocessing-to-forward access tests, target-only
loss gradients, common conditions/structure, exact initial future equivalence to
the original architecture, inherited data audit, independent eight-sample/500-step
overfit for every variant. Smoke weights are discarded. Preselected train IDs and
all 16 gradient minibatches are recorded. Diagnostics only read train/validation
and existing C checkpoints, eval mode, no optimizer steps. Unavailable early/final
C states are reported as unavailable rather than reconstructed.

History diagnostics use original deterministic_mask(sample,epoch=0,seed=12345),
same as original supplemental test rule, now on train/val only. C vs repeat-current
and oracle true-entity rigid fitting use the same hidden valid queries. Report
target-future moving/stationary groups, entities, covered/uncovered subsets,
query/window/episode/family counts. Compare the rigid fit only on its covered
queries. Gradient future loss retains the original tool+target definition.
Shared parameters: temporal, point, visual, proprio and body; exclude both output
heads, action encoder (future-only) and frozen RGB backbone. Record raw and
lambda=1 weighted ratios, cosine quantiles and negative fraction.

Evaluation: original event/motion rules (contact1e-5 N*s, three100Hz-step debounce,
0.2s event margin, 2mm future-motion threshold); groups overlap. Valid target
Euclidean errors, window means then equal-weight episode means, mm. Report
per-horizon errors/counts, paired Delta_self=H0-H_self and
Delta_cross=H_self-H_all, absolute mm and relative reduction. Family cluster
bootstrap seed20261006, 10000 replicates, retain all episodes/windows from sampled
families. Empty subset families are omitted from that subset's coverage, never
zero-filled. Intervals represent family sampling for fixed single-seed models,
not training-seed stability. CV uses the original last negative0.1s displacement
formula; it needs target history and is not a same-information H0 competitor.

The test set was viewed in round1 and motivated round2; this is an exploratory
reuse, not a fresh confirmation test. No test results guide thresholds,
checkpoint selection, architecture or training. H_all is target-only supervised
and is not equivalent to the old jointly supervised A.

Local visual deliverables only: three preselected family0007/category cases near
the configured times (event coverage takes precedence), plus largest improvement
and degradation windows by H_self-H_all test ADE, clearly labelled after-selection.
No change to the existing public viewer. Stop after results/diagnostics/report.
