# Executed task evaluation across four methods and four checkpoints

All320 rollouts completed and passed evidence validation. Every cell reports final_success from one independent initialization at each of the same20 nominal poses.

| Method | 5k | 10k | 20k | 30k |
|---|---:|---:|---:|---:|
| ACT | 15% (3/20) | 10% (2/20) | 15% (3/20) | 10% (2/20) |
| Tracks (aux OFF) | 10% (2/20) | 0% (0/20) | 10% (2/20) | 15% (3/20) |
| v3 AUX | 15% (3/20) | 5% (1/20) | 20% (4/20) | 25% (5/20) |
| v4 AUX | 5% (1/20) | 15% (3/20) | 15% (3/20) | 15% (3/20) |

ACT uses current RGB/state. Tracks (aux OFF) adds historical tracks without auxiliary training. v3/v4 train completion and prediction readouts. Auxiliary outputs are unused during policy rollouts.

Pose IDs62001..62020 share commanded pose/asset references across all16 combinations. One unconditional initialization per cell; no deformation-based selection or retry. Cloth microstates/velocities vary stochastically, so these are not exact physical-state pairs. Check commanded translation1e-6m, rotation1e-5deg, scale1e-6, rest-mesh SHA, joint positions/velocities1e-5 and60physics ticks. Preserve600-action/90Hz/prefix10 and50 follow-up actions after first success. Original predicate, primary final_success and secondary ever_success remain unchanged. Engineering failures are separate; completed outcomes are never retried.

ever_success events: 48/320; final_success events: 40/320. These are event totals; each cell has20 trials. Do not pool320 cross-method events into one success-rate estimate.

Executed controls: pose62001 happened to match exactly across independent ACT/v4 processes, while other poses revealed centimeter-scale cloth stochasticity and motivated explicit nominal-pose matching. USD/physics links agreed and images/cloth updated. A323-action expert replay succeeded: zero initial cache difference,2.58mm RMS final cache difference. Separate gates at the previously unmatchable62002/62003 checked nominal acceptance and logged physical variation. Controls are excluded from320 outcomes.

Offline predicate positive control: 4/4 existing expert end states recomputed as successful with the original formulas and matching recorded distances. These existing-data checks are separate from the320 new policy rollouts.

Independent audit recomputed320 initial arrays and320 geometry decisions. Minimum pairwise mesh-coordinate L-infinity separation across20 nominal references: 0.028763 m. Video frame counts checked: 320.

Actual initial mesh maximum-coordinate deviations from nominal references across320 rollouts: median0.00mm, P95 28.12mm, maximum48.19mm; maximum finite-difference velocity deviation0.516m/s. These are recorded, not used to select initializations. Wilson intervals reflect pose/initialization variation, not training-seed variation.

Full427-window reused development validation, distinct from task success:30k chunk MSE by method:

- ACT: chunk MSE 0.059920; first-action MSE 0.023873 rad².
- Tracks (aux OFF): chunk MSE 0.060421; first-action MSE 0.025143 rad².
- v3 AUX: chunk MSE 0.060920; first-action MSE 0.024225 rad².
  Past EPE 9.68 mm (static 14.21); future EPE 7.78 mm (static 13.83).
- v4 AUX: chunk MSE 0.060224; first-action MSE 0.025203 rad².
  Past EPE 10.54 mm (static 14.21); future EPE 8.69 mm (static 13.83).

Motion fitting and policy success are separate measurements. One training seed, one task and20 starts do not support cross-task architecture conclusions. Every checkpoint was predeclared; none was selected by success outcomes.

Visualizations:64 windows and128 English PNGs across v3/v4 and four milestones. The same8 windows are preselected; median/high-error examples are labeled as illustrative.16 observed and48 withheld points,0.5s past/future, known t=0 excluded from EPE. Independent NPZ rescoring passed512 checks. Future RGB/GT are display-only. Expert replay windows and actual policy rollout videos are separate. Projections use the calibrated fixed top camera; cached recorded wrist extrinsics make wrist projections invalid, so they are withheld. World-coordinate trajectories and EPE are unaffected.

[Success matrix PNG](success-matrix.png) · [Verified outcomes JSON](matrix-summary.json) · [Trajectory catalog](trajectory-catalog.json) · [Independent rollout audit](rollout-evidence-audit.json) · [Frozen protocol](protocol.json) · [Runtime controls](runtime-controls-summary.json)

Scope: LeHome simulation with oracle persistent vertices including occluded history. No physical robot, deployable visual tracker or cross-task generalization evaluation.

Training/model source: f3c0744. Corrected runtime and scheduler identities are recorded in protocol.json and the verified summary. All16 exports strictly loaded and hashed before execution. Actual actions, horizons, initial states, success flags, USD/physics pose agreement and videos were checked. The earlier196-run stale-USD batch and stopped strict-microstate cohort are excluded; all320 final outcomes are newly executed under the uniform nominal-pose protocol.
Verified summary: 2026-10-20T14:27:11.005507+00:00.
