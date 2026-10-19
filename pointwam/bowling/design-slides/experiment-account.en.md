# Bowling dynamics: chronological experiment account

As of 2026-10-19. Fourteen editorial rounds reconstructed from execution records, protocols and Git history; these are not original run identifiers. No new training, inference or physics.

The original goal was unseen robot-release, multi-pin dynamics from 21-point history and robot conditions. It remains unestablished. The later 100 ms rolling-ball task is a different, narrower task.

## Round 1

Trajectory reconstruction failed twice before the planned main dynamics run. This was reconstruction using true future trajectories, not forecasting.

Sources: `experiments/pointwam_bowling/README.zh-CN.md`, `reports/pointwam_bowling/tokenizer-v1/gate.json`, `reports/pointwam_bowling/tokenizer-lr-probe/gate.json`

## Round 2

Time encoding improved reconstruction, but lossless trajectory representation did not make the 2000-step generative dynamics fit accurately. These were train-only diagnostics.

Sources: `experiments/pointwam_bowling/DIAGNOSIS.zh-CN.md`, `reports/pointwam_bowling/diagnosis-round2/experiment-scope.json`

## Round 3

Direct coordinate regression fitted eight training trajectories accurately, but all 110 validation stationary pins drifted more than 20 mm by four seconds.

Sources: `experiments/pointwam_bowling/DIRECT.zh-CN.md`

## Round 4

Frozen-model checks found early false motion and rollout amplification. True second-two scene inputs reduced, but did not remove, stationary-pin error.

Sources: `experiments/pointwam_bowling/STATIC_DRIFT_DIAGNOSIS.zh-CN.md`

## Round 5

Temporal-prefix training enforced exact early-output invariance to later plans, but did not eliminate false motion or improve overall validation accuracy.

Sources: `experiments/pointwam_bowling/TEMPORAL_PREFIX.zh-CN.md`

## Round 6

Contact-timing analysis exposed inadequate post-contact support in the original two-second validation queries, while confirming that training did contain collisions.

Sources: `experiments/pointwam_bowling/CONTACT_DIAGNOSIS.zh-CN.md`

## Round 7

The object-relation model improved pre-contact accuracy but worsened post-contact displacement error on a fresh holdout. The planned continuation criterion failed.

Sources: `experiments/pointwam_bowling/INTERACTION_EXPERIMENT.zh-CN.md`

## Round 8

Physics interventions showed axial spin matters, but did not prove that the original full history is insufficient or that hidden state is the cause of model failure.

Sources: `experiments/pointwam_bowling/VISIBLE_STATE.zh-CN.md`

## Round 9

Adding true object pose and velocity improved training fit but worsened validation collision error in all three seeds.

Sources: `experiments/pointwam_bowling/state_probe/README.zh-CN.md`

## Round 10

Short-horizon supervision greatly reduced quiet-pin false motion on the same 100 ms target, but did not establish a reliable collision-prediction advantage.

Sources: `experiments/pointwam_bowling/local_collision/README.zh-CN.md`, `experiments/pointwam_bowling/local_collision/protocol.json`

## Round 11

Nearby training coverage strongly improved local response fit, but this intentionally exposed evaluation neighborhoods and did not establish unseen-scene generalization.

Sources: `experiments/pointwam_bowling/neighborhood/README.zh-CN.md`

## Round 12

On a new controlled rolling-ball task, full point history improved first-pin 100 ms response prediction across three seeds and fresh families. This supports history use within that scope.

Sources: `experiments/pointwam_bowling/paired_response/README.zh-CN.md`

## Round 13

Partial-history reconstruction failed the primary full-input test. The masked-input mean gain was not seed-stable, and the train/test availability mismatch limits causal attribution.

Sources: `experiments/pointwam_bowling/history_completion/README.zh-CN.md`

## Round 14

A read-only scope review found a fixed relative rack and first-pin-only target. The current completion line was closed; the bounded history benefit remains valid.

Sources: `reports/pointwam_bowling/research-closeout-v1/scope-audit.json`, `experiments/pointwam_bowling/research_status.json`
