# Physical acceptance record
All **60/60** episodes passed: four P0 protocols, 20 modes, seeds 0/1/2. Each uses actual Panda control and PhysX integration with native RGB-D, fixed points and solver contacts. **69/69 CPU regression tests passed**, including existing coverage and 13 new interface tests. No neural model was trained.

[中文](VALIDATION.zh.md) · [complete machine-readable evidence](validation.json) · [implementation/commands](README.en.md) · [23 GIFs](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/)

## Mode verification
- ToolContactRelease: engage_pull, near_miss, contact_release, failed_engagement, each 3/3.
- HookPullDynamics: successful_engagement, hook_miss, ineffective_contact, detachment, each 3/3. Ineffective contacts move the target off-direction with less than 1 mm negative-X progress; refined engagement is false.
- CollisionChain: direct_push, two_body, three_body, near_miss, failed_propagation, collision_free_motion, each 3/3. Three-body propagation has real A–B/B–C contact and ordered A<B<C motion; no direct robot/tool contact with B/C. Independent post-collision B motion is additionally verified.
- FreeMotionInterception: interception, missed, early, late, redirection, no_intervention, each 3/3. Successful/early contacts change velocity; miss/late/no intervention have no target contact; redirection exceeds 45°.

Additional independent-physics profile: independently sampled A/B/C mass, friction and restitution, requested tool speed 0.30–0.34 m/s and impact angle ±0.025 rad. Six chain modes × three seeds **18/18 pass**; independent OOD Physics three-body **1/1 passes**. These are extra small samples; failed propagation retains the explicit B override.

Every episode has 111 frames, 110 controls and 550 physics contact steps. Maximum exported point-transform discrepancy: **5.96e−8 m**. Persistent IDs/local points/poses and RGB-D/calibration shapes/finite values passed auditing.

## Reproducibility and evaluation
- Repeat all 20 seed0 modes: poses, velocities, points, local points, point IDs, contact states and commands are **20/20 exactly equal**, within the same Linux CPU runtime.
- Corrected float32 online inputs: one episode per protocol plus an actual WebSocket collision-chain episode, **5/5 exactly equal to offline inputs/predictions**, called before future integration. Earlier float64 online predictions and their small recording-precision differences remain retained.
- The offline CLI evaluated the native WebSocket three-body sample: stationary smoke Object ADE 0.088245 m, Target ADE 0.083155 m, propagation accuracy 0. Contact timing is null without a head. This validates interfaces/metrics, not a learned model.
- Oracle self-comparison gives zero ADE/FDE. Pair response and OOD-gap interfaces are tested and exercised on actual data. Small-sample stationary/CV gaps are recorded without claims of learned generalization.
- Current-code annotation replay of all 60 recorded episodes matches discrete modes/events/phases. Different NumPy versions produce only a maximum 1.49e−8 m/s velocity-change statistic difference.

## Diagnostic pairs
Three seeds × three types: **9/9 accepted**, with strict and approximate matching distinguished.
- Action counterfactual: identical complete native initial-state IDs and current RGB-D, changed precommitted controls only. Mean future target difference: 4.13–4.56 cm.
- Hidden velocity: three identical current RGB-D/proprio/calibration and future-control pairs. Omitting current oracle points makes all nonhistory model inputs exactly equal. Default current oracle points differ by 0.39–1.04 micrometres, so default strict ambiguity is false. Mean future difference: 28.45–33.30 cm.
- Contact history: actual past target contact in A and none in B, equal future controls. Seed0/2 current RGB-D match exactly; seed1 RGB MAE is 0.000102/255. Robot/oracle-point differences make all three approximate rather than strict all-input ambiguity. Mean future difference: 5.04–7.06 cm.

Metadata retains held/changed variables, initial-state/action IDs, observable matching and response differences. A/B visualizations share world projection/scale and provide a separate anchor image.

## OOD and retained failures
OOD Geometry 4/4, OOD Physics 4/4, three-body OOD Composition 1/1; two ID geometry-family three-body samples pass 2/2. The cylinder component sample is in train; the full box→cylinder→box order remains held out. This covers selected positive modes, not the complete OOD mode grid.

Original attempts remain, without changing success thresholds:
- acceptance-001 failed_propagation seed2 displaced B by 1.39 cm. Rejected; explicit 5 kg/high-friction B passes the repeated 60-mode suite.
- diagnostics-001 tool contact-history had observable mismatch and was rejected; native ball interception histories replace it.
- Early composition two_body exported three targets with a seen prefix. Excluded; configurations now reject that scope.
- Brief velocity correlation alone does not define hooking; engagement now requires more than 5 mm negative-X progress and remains explicitly approximate.

## Artifacts and limits
Git stores code/configuration/documentation and compact evidence. Raw HDF5 is in this worktree's `data/interaction_dynamics/`: acceptance-006, repro-001, diagnostics-final-seed0/1/2, OOD profiles, online-final-001 and ws-online-001. Local and gpu17 data are available; Baidu receives code/documents but did not execute these simulations.

Native RGB-D integration source: `d68def4bc00e1bbe26a1b64d1cc51ab6226d301c`. acceptance-006 derives annotations while preserving all physics/cameras/commands, rather than rerunning simulation. Original-file hashes and simulation/annotation fingerprints are separate. Current annotation replay verifies every episode.

Limits: approximate hand bounding-box points and heuristic phase/engagement; solver-contact flicker; export covers tracked-object and robot–object contacts, not table reaction forces. CPU single-environment small-sample validation, without production-scale statistics or full Isaac Sim GPU integration regression. P1 new door/drawer links and carry/slip extensions remain deferred; existing paths are retained. No neural-model performance results.


The v3 annotation refresh preserves recorded poses, velocities, points, contacts, commands and RGB-D exactly in 60/60 episodes; labels and phases replay exactly. `task_success` records physical goal achievement separately from negative-mode verification; `privileged/progress_displacement_m` stores per-frame progress. The incomplete acceptance-005 refresh was rejected for a 1.42e−14 m recomputation difference; acceptance-006 preserves existing audited oracle arrays.
