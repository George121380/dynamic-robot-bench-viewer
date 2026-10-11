# Initial model iteration: recommended benchmark subset
Start with **FreeMotionInterception-v1, ToolContactRelease-v1, and CollisionChain-v1**, progressing from self history to action/contact reasoning to cross-object propagation. With room for two, choose **FreeMotion + CollisionChain**; for one pipeline-debugging task, choose FreeMotion. Keep the existing 300-episode PullCubeTool pilot as a regression set. This is a selection recommendation: **no model was trained on the new tasks, and a forecasting benefit from MAE has not been established**.

Status: inventory, data, acceptance and previous experiments reviewed on 2026-10-11. Branch `task/benchmark-subset-v1`; no PR; private main unchanged. Environment code remains at `16c9aef`. This review adds bilingual documents, review JSON and a static-page builder, without changing tasks or evaluators. PhysMani evidence uses `ab23d05` and the published 2026-10-10 03:31 UTC snapshot; snapshot job status is not a live observation.

[中文](README.zh.md) · [Public selection page with GIFs](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-subset/) · [45-entry structured review](review.json) · [Existing interaction acceptance](../interaction-dynamics/VALIDATION.en.md) · [Existing depth acceptance](../benchmark-tasks/depth/)

## Why these three
The experiment should isolate benefits from history, actions and other objects, rather than only improve historical reconstruction. These tasks share Panda, ManiSkill, seven-dimensional precommitted pd_ee_delta_pose controls, 20 Hz observations/control and 100 Hz contacts. Small-sample acceptance covers full RGB-D, persistent points and contact fields. Holding robot, coordinates, control semantics and schema constant helps interpret model changes.

The previous experiment is a useful warning. Project-root `dev/experiments/history-supervision-round3/REPORT.md` reports seeds 7/17/27: validation-selected target test ADE was B3 0.397±0.024 mm and C3 0.405±0.036 mm. C/B benefit was −0.0085 mm, family-bootstrap 95% CI [−0.0221,+0.0046], with opposite effects across seeds. Historical completion learned, but forecasting gains were inconsistent. These are exploratory results on the old PullCubeTool pilot, **not performance on the new tasks**. Its repeatedly viewed test set should not substitute for a fresh frozen test-family pool.

### 1. FreeMotionInterception: establish history value
The target moves before robot contact. Retain interception, missed, early, late, redirection and no_intervention. Compare H0/H-self before contact; include constant velocity to identify mere extrapolation. Then evaluate timing and post-impact direction/velocity, so easy free motion does not conceal collision failures.

Accepted ball hidden-velocity pairs are useful for development, with a query-definition caveat. RGB-D, proprioception and future controls can match strictly; current oracle points differ by about 0.39–1.04 µm. Main point ablations should give every branch the same type of current P0 input and disclose approximate pair matching. If strict RGB-only pairs omit P0, H0 must still know the spatial definition of randomly sampled point IDs; otherwise the ablation also tests point-identity initialization. Centroid/pose metrics or shared fixed queries can address this. That training adapter is not implemented or validated yet.

[RGB + persistent XYZ + contact GIF](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/media/ID_free_motion_interception_family000000_seed0_interception.gif) — **Native simulator depth GT, metres**.

### 2. ToolContactRelease: actions, contact and release
Retain engage_pull, near_miss, contact_release and failed_engagement, forecasting the target cube. Identical-initial-state action counterfactuals have been accepted. Contrast effective contact, near misses, ineffective contacts and post-release motion. Action conditioning uses precommitted controls, never future realized TCP trajectories.

HookPullDynamics uses the same L-tool environment; success/miss/ineffective modes substantially overlap, so do not count it as a separate initial family. Add its detachment mode later if useful. Keep the old 300-episode PullCubeTool pilot for regression. Public PullCubeTool/PokeCube/RollBall demonstrations offer coverage, but successful demonstrations alone do not establish history dependence or balanced negative examples.

[RGB + persistent XYZ + contact GIF](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/media/ID_tool_contact_release_family000000_seed0_contact_release.gif) — **Native simulator depth GT, metres**.

### 3. CollisionChain: primary cross-object task
Use the accepted `--independent-object-physics` profile, independently sampling A/B/C mass, friction and restitution. Retain direct_push, two_body, three_body, near_miss, failed_propagation and collision_free_motion. Physical A–B/B–C contacts cause B/C motion; acceptance excludes direct tool/robot contact with B/C.

Forecast **B (object_id=2) and C (object_id=3)**, rather than default target A at ID 1. Compare H-self/H-all in windows where B/C are still stationary but upstream objects have moved, then mask past A/tool tracks. Hold current geometry and queries constant across branches; otherwise H-all gains may reflect different current information. Report B/C per-object ADE, propagation order and phase errors separately from tool/A and static-point averages.

The existing generator has no accepted chain pair with different upstream velocity but matched current visible geometry and future controls. This is a valuable next diagnostic; ball diagnostics are not evidence for chain history dependence. Shuffled history is an input ablation, not a physically valid counterfactual.

[RGB + persistent XYZ + contact GIF](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/media/ID_collision_chain_family000000_seed0_three_body.gif) — **Native simulator depth GT, metres**.

This GIF illustrates an accepted basic-profile three_body episode. Independent-physics numerical acceptance is separate; this is not footage from that batch.

## Is the data ready?
- Basic acceptance-006 core subset: **48 episodes / 9 scene families, train/validation/test=42/0/6**. FreeMotion is 18/0/0; Tool 12/0/0; Chain 12/0/6. All four protocols total 60 episodes / 12 families.
- Independent-physics-002 chain adds **18 ID episodes (12/6/0)** and one OOD Physics episode. It supplies chain validation without completing tool/free-motion three-way coverage.
- Physics profiles have different family strings and independently hashed partitions, while base seed/family layouts and controls can share ancestry. Freeze one profile initially, or introduce parent-scene grouping before combining profiles across splits. That parent field is not implemented.
- Forty depth-capable entries passed through 39 distinct samples / 468 frames. These are generally twelve-frame read/re-render smokes, **not complete training rollouts**, and do not validate persistent-point/contact adapters.
- Eight RoboCasa entries have original-state RGB-D replay, without accepted action-reexecution consistency, link-bound points or contact GT. PhysMani has more mature RGB-D and official Dataset readers: across all 16 tasks, 12/12 assets, 32 expert/WM packages and 3,200 released-3DFA evaluation episodes have evidence, but persistent-point GT is unverified. Depth accessibility is not equivalent to immediate point-world-model training compatibility.

## First iteration plan (proposed, not executed)
1. Start with ID and one fixed physics profile. Enumerate 100 `(family,seed)` scene families per task; 4/6/6 modes produce **1,600 candidate rollouts**. Existing hashes give an expected 70/20/10 split, not exact quotas; inspect coverage before generation. Group modes, pairs and related variants before slicing windows. Preserve failures, acceptance criteria and rejection reasons.
2. Use the existing nine diagnostic pairs for development. Add about 30 fresh pairs for each hidden-velocity, action-counterfactual and contact-history type. Upstream-hidden-velocity chain pairs require separate implementation and fieldwise matching acceptance. This is a starting budget, not a statistical-power guarantee.
3. Balance tasks, positive/negative modes, movement and contact events; report 0.2/0.5/1.0 s forecasts. Include pre-impact, onset, release and free-motion windows, avoiding static-point-dominated averages. Mixed two/three-target batches require explicit entity-valid masks.
4. Freeze current inputs, future controls, capacity, budget and validation checkpoint selection: H0 → H-self → H-all → H-all + MAE, then point/object history masking. Establish FreeMotion self-history value, B/C cross-history value, then MAE forecasting value. Report reconstruction separately.
5. Use three training seeds and paired family-level differences/intervals. Include stationary/CV, moving B/C, phase errors, action responses and later ID/OOD gaps. Do not infer contact timing from points without a contact head. Three seeds remain limited replication.
6. Expand afterward with PushT torque/rotation and OOD Physics, Geometry and Composition. Freeze held-out parameter ranges/combinations; a new seed alone is not OOD.

Existing generation interfaces can collect the subset. These are **small-sample commands**, not executed in this review or equivalent to the 1,600-rollout plan. Linux runtime requirements are in the [implementation document](../interaction-dynamics/README.en.md):
```bash
python -m dynamic_robot_bench.tasks.interaction_dynamics.runner \
  --tasks free_motion_interception tool_contact_release --seeds 0 1 2 \
  --families 2 --strict --output data/interaction_dynamics/subset-dev-free-tool
python -m dynamic_robot_bench.tasks.interaction_dynamics.runner \
  --tasks collision_chain --independent-object-physics --seeds 0 1 2 \
  --families 2 --strict --output data/interaction_dynamics/subset-dev-chain
```
The runner has no B/C target-selector CLI. The training/input adapter must call `model_window(...,target_id=2)` or `target_id=3` and explicitly select the corresponding per-object metrics. Default H-self online smoke is not the B/C ablation.

## Which public tasks come next?
- **PushT-v1** first: asymmetric geometry and off-centre pushing add rotation/torque under the same simulator.
- **PhysMani**: start with `pick_moving_target_on_the_table` and `push_moving_button`, normal/high-speed pairs. They isolate dynamic perception and timing more readily than insertion or container placement. High speed is OOD only when fully excluded from training. Official 16-task policy success remains separate from point-forecast error; add point/control adapters first. See [official tasks/data](https://github.com/vLAR-group/PhysMani) and the [published local-progress snapshot](https://peiqil.com/dynamic-robot-bench-viewer/physmani/progress.json).
- **RoboCasa**: OpenDrawer first, CloseFridge second, covering prismatic/revolute constraints and per-link points. Dishwasher/toaster racks are drawer alternatives. Official states/scene files support replay without proving our new contact annotations. Preserve official pretrain/target splits, original success rules and exact versions. See [official atomic tasks](https://robocasa.ai/docs/build/html/tasks/atomic_tasks.html) and [dataset format/splits](https://robocasa.ai/docs/build/html/datasets/using_datasets.html).
- **Conveyor**: retain L1 constant-speed external online evaluation. L2/L3 mix semantic memory, two arms and exogenous speed schedules. An unobserved future schedule precludes uniquely identifiable deterministic futures; condition on it or evaluate uncertainty.
- MOVi-C is optional action-free representation pretraining; CoPhy/Physion are passive external diagnostics. They cannot replace robot action conditioning. CLEVRER lacks project-verified pixel depth/persistent-3D GT; estimated depth is not geometric ground truth.

P0 reuses familiar upstream assets/environments, but its new modes and acceptance rules are custom protocols. Three-seed/60-episode acceptance supports small-sample functionality, not absence of hidden bugs or community validation of the whole protocol. Freeze manifests, audit point transforms independently and replicate on fresh families. [Upstream ManiSkill tasks](https://maniskill.readthedocs.io/en/latest/tasks/table_top_gripper/index.html) and [public demonstrations](https://huggingface.co/datasets/haosulab/ManiSkill_Demonstrations/tree/main/demos) provide external anchors.

## Complete item-by-item decisions
Scope: 42 historical catalog entries, including the PhysMani overview, plus four new protocols; excluding the redundant overview gives **45 individual entries**. Speed variants, datasets and reused environments are not independent task families. Dataset counts come from selected versions/registered metadata and do not mean every corpus was downloaded locally.

1. **[match_and_pick_from_conveyor](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#match_and_pick_from_conveyor) — External validation**. Moving support / grasp / semantic memory. Retain for external online tests, starting with L1 constant speed; unobserved future L2/L3 schedules preclude deterministic exact forecasts.
   - Data: Official 100; project accepted v4 20 / v5 3.
   - [Depth: New RGB-D collected · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#match_and_pick_from_conveyor). New RGB-D in the actual Isaac Sim task; hold robot state to verify conveyor motion and sensors, without evaluating grasp success.

2. **[push_puck_collision](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#push_puck_collision) — Existing regression**. Two-body collision / free sliding. 27 pilot episodes with restricted y control; the depth smoke had no A-B collision. Use calibrated successful runs for regression; use the new chain for the core.
   - Data: 27 project recordings; no matching standard release.
   - [Depth: New RGB-D collected · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#push_puck_collision). New depth in existing CollisionEnv. This sample failed with second_strike before A–B collision; it is not a successful demo.

3. **[PandaFingerArticulationDiagnostic-v0](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#PandaFingerArticulationDiagnostic-v0) — Pipeline sanity**. Link identity / joint motion. Check link-bound transport; this is not a full articulated manipulation benchmark or task-policy success.
   - Data: Custom task; 2 project source episodes.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#PandaFingerArticulationDiagnostic-v0). Project diagnostic HDF5 stores RGB, millimeter depth and calibration; the official expert corpus was not downloaded.

4. **[RollBall-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#RollBall-v1) — Merge / reuse**. Ball pushing / rolling. Covered by the interception family; the original starts at rest, so its name alone does not establish a hidden-velocity diagnostic.
   - Data: 855 episodes in selected RL metadata.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#RollBall-v1). Project diagnostic HDF5 stores RGB, millimeter depth and calibration; the official expert corpus was not downloaded.

5. **[PullCubeTool-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#PullCubeTool-v1) — Existing regression**. Standard tool pulling. Retain the 300-episode oracle pilot for regression and a public-source anchor; repeated old test sets are not fresh final evaluations.
   - Data: 1,000 motion-planning episodes.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#PullCubeTool-v1). Project diagnostic HDF5 stores RGB, millimeter depth and calibration; the official expert corpus was not downloaded.

6. **[PokeCube-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#PokeCube-v1) — Merge / reuse**. Grasped-peg pushing. Covered by CollisionChain direct_push; audit public demonstrations for bypassing the peg.
   - Data: 579 episodes in selected RL metadata.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#PokeCube-v1). Project diagnostic HDF5 stores RGB, millimeter depth and calibration; the official expert corpus was not downloaded.

7. **[PickCube-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#PickCube-v1) — Pipeline sanity**. Grasp / lift / release. Use for camera/action/grasp pipeline sanity; successful demonstrations alone rarely establish a history requirement.
   - Data: 1,000 motion-planning episodes.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#PickCube-v1). Project diagnostic HDF5 stores RGB, millimeter depth and calibration; the official expert corpus was not downloaded.

8. **[PushT-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#PushT-v1) — Next addition**. Off-centre contact / planar rotation. First expansion candidate: add rotation, contact-location dependence and asymmetric geometry beyond simple balls/boxes.
   - Data: 719 episodes in selected RL metadata.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#PushT-v1). Project diagnostic HDF5 stores RGB, millimeter depth and calibration; the official expert corpus was not downloaded.

9. **[OpenDrawer](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#OpenDrawer) — External validation**. Prismatic joint / handle contact. First RoboCasa choice: one joint and clear phases, with state-based depth verified; add link points, real contacts and action replay.
   - Data: Human pretrain 100 / target 500; MG 10k; one original-state RGB-D replay, not a complete training adapter.
   - [Depth: Original-state depth rendered · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#OpenDrawer). Replay original XML/states/cameras; original-video RGB MAE 8.25/255. Displayed RGB/depth are rendered together.

10. **[PanTransfer](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#PanTransfer) — Later expansion**. Grasp / carry / placement. Useful later for carry/release; composite planning confounds early dynamics, and target data must not define pretraining splits.
   - Data: Human target 500; no registered pretrain/MG; one original-state RGB-D replay, not a complete training adapter.
   - [Depth: Original-state depth rendered · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#PanTransfer). Replay original XML/states/cameras; original-video RGB MAE 6.47/255. Displayed RGB/depth are rendered together.

11. **[CloseFridge](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#CloseFridge) — External validation**. Hinged door / release. Second RoboCasa choice: contrast rotational versus drawer translation; verify persistent link identities first.
   - Data: Human pretrain 100 / target 500; MG 10k; one original-state RGB-D replay, not a complete training adapter.
   - [Depth: Original-state depth rendered · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#CloseFridge). Replay original XML/states/cameras; original-video RGB MAE 11.60/255. Displayed RGB/depth are rendered together.

12. **[SlideDishwasherRack](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#SlideDishwasherRack) — Alternative**. Sliding rack. Redundant with drawer translation; use as an alternative or fixture generalization, not simultaneous first-round additions.
   - Data: Human pretrain 100 / target 500; MG 10k; one original-state RGB-D replay, not a complete training adapter.
   - [Depth: Original-state depth rendered · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#SlideDishwasherRack). Replay original XML/states/cameras; original-video RGB MAE 2.96/255. Displayed RGB/depth are rendered together.

13. **[StackBowlsCabinet](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#StackBowlsCabinet) — Later expansion**. Stacking / support contacts. Rich support constraints with multiple stages and occlusion; add after basic contact learning is stable.
   - Data: Human pretrain 100 / target 500; no MG; one original-state RGB-D replay, not a complete training adapter.
   - [Depth: Original-state depth rendered · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#StackBowlsCabinet). Replay original XML/states/cameras; original-video RGB MAE 2.65/255. Displayed RGB/depth are rendered together.

14. **[CoffeeSetupMug](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#CoffeeSetupMug) — Later expansion**. Grasp / containment / relative pose. Better for composite manipulation and visual generalization; limited incremental dynamics for the initial subset.
   - Data: Human pretrain 100 / target 500; MG 10k; one original-state RGB-D replay, not a complete training adapter.
   - [Depth: Original-state depth rendered · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#CoffeeSetupMug). Replay original XML/states/cameras; original-video RGB MAE 6.29/255. Displayed RGB/depth are rendered together.

15. **[SlideToasterOvenRack](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#SlideToasterOvenRack) — Alternative**. Sliding rack. Redundant with drawer translation; use as an alternative or fixture generalization, not simultaneous first-round additions.
   - Data: Human pretrain 100 + MG 10k; no target; one original-state RGB-D replay, not a complete training adapter.
   - [Depth: Original-state depth rendered · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#SlideToasterOvenRack). Replay original XML/states/cameras; original-video RGB MAE 2.99/255. Displayed RGB/depth are rendered together.

16. **[StirVegetables](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#StirVegetables) — Later expansion**. Tool contact with many small objects. Rich interactions, but occlusion, assets and success/contact adaptation are more complex; avoid as an initial primary metric.
   - Data: Human pretrain 100 / target 500; no MG; one original-state RGB-D replay, not a complete training adapter.
   - [Depth: Original-state depth rendered · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#StirVegetables). Replay original XML/states/cameras; original-video RGB MAE 7.12/255. Displayed RGB/depth are rendered together.

17. **[ToolHang](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#ToolHang) — Later expansion**. Assembly / geometric support. Valuable geometric relations; isolate engagement with simple L-tools before full assembly and multiple assets.
   - Data: robomimic PH: 200 successful human demos.
   - [Depth: Original-state depth rendered · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#ToolHang). Full MuJoCo states from original demo_0 rendered as paired RGB-D; no original RGB pixel comparison.

18. **[reach_and_drag](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#reach_and_drag) — Alternative**. Tool dragging / sweeping. Fresh expert RGB-D exists; suitable for cross-engine tool generalization after persistent points, contact truth and grasp semantics are checked.
   - Data: PerAct: 100/25/25 train/val/test per task.
   - [Depth: New RGB-D collected · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#reach_and_drag). New RLBench expert demo; task Python/TTM match pinned PerAct assets. The author Drive archive was not read.

19. **[MOVi-C](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#MOVi-C) — Optional pretraining**. Passive multi-object motion / occlusion. Preferred optional representation pretraining: rich RGB-D/3D GT, but no robot actions and persistent-point adaptation still needs validation.
   - Data: TFDS 128² v1.0.0: 9,737/250/999.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#MOVi-C). Official TFRecord depth stores ray distance; convert to Z before back-projection.

20. **[CoPhy](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#CoPhy) — Passive diagnostics**. Physical counterfactuals. Fresh Blocktower depth exists; useful for later passive physics diagnostics, not robot action conditioning.
   - Data: Author 224² corpus about 18 GB + split file.
   - [Depth: New RGB-D collected · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#CoPhy). Blocktower only: new RGB-D with author functions/URDFs; no complete AB/CD protocol or other subsets.

21. **[AdroitHandHammer-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#AdroitHandHammer-v1) — Later expansion**. Dexterous grasp / impact. Original D4RL state renders, but 26D dexterous control/contact complicates early debugging.
   - Data: Minari human-v2: 25 episodes / 11,310 steps.
   - [Depth: Original-state depth rendered · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#AdroitHandHammer-v1). Replay original D4RL qpos/qvel/board_pos; the selected Minari file has only success, without full states.

22. **[Physion-v1.5-OCP](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#Physion-v1.5-OCP) — Passive diagnostics**. Object contact prediction. Use Collide for external contact diagnostics; published OCP labels are not dense persistent-point forecasting. Avoid full-corpus downloads initially.
   - Data: 7 categories; readout train/test, 14 ZIPs.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#Physion-v1.5-OCP). Original TDW float32 depth and matrices; aligned RGB-D strided jointly from 1024² to 256².

23. **[sweep_to_dustpan_of_size](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#sweep_to_dustpan_of_size) — Alternative**. Tool dragging / sweeping. Fresh expert RGB-D exists; suitable for cross-engine tool generalization after persistent points, contact truth and grasp semantics are checked.
   - Data: PerAct: 100/25/25 train/val/test per task.
   - [Depth: New RGB-D collected · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#sweep_to_dustpan_of_size). New RLBench expert demo; task Python/TTM match pinned PerAct assets. The author Drive archive was not read.

24. **[CLEVRER](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#CLEVRER) — Passive diagnostics**. Collision-event reasoning. Videos/events exist, but pixel depth and persistent 3D points are unvalidated; reserve for event diagnostics without estimated-depth ground truth.
   - Data: 20,000 videos: 10k/5k/5k.
   - [Depth: Existing videos require estimated depth](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/). The standard release lacks pixel depth; object centers are not surface depth.

25. **[TurnFaucet-v1](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#TurnFaucet-v1) — Deferred / blocked**. Revolute articulation. Matching v1 assets/data remain unaccepted; a v0 GIF is not v1 evidence.
   - Data: v1 absent from checked official demo registry.
   - [Depth: v1 depth availability unconfirmed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/). Matching v1 data/assets are unaccepted; the v0 GIF is a motion reference.

26. **[beat_the_rotating_buzz](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#beat_the_rotating_buzz) — Later expansion**. Rotating-target striking. Keep for later external dynamics validation; multi-stage manipulation/precision and scripted motion complicate initial representation/contact diagnosis. Speed variants are not independent interaction families.
   - Data: Across all 16 tasks: 12/12 assets and 32 expert/WM packages accepted; 3,200 released-3DFA evaluation episodes (2026-10-10 snapshot); persistent-point GT not verified.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#beat_the_rotating_buzz). Project expert observations: decoded RGB24 depth; no WM predictions.

27. **[beat_the_rotating_buzz_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#beat_the_rotating_buzz_high_speed) — Later expansion**. Rotating-target striking. Keep for later external dynamics validation; multi-stage manipulation/precision and scripted motion complicate initial representation/contact diagnosis. Speed variants are not independent interaction families.
   - Data: Across all 16 tasks: 12/12 assets and 32 expert/WM packages accepted; 3,200 released-3DFA evaluation episodes (2026-10-10 snapshot); persistent-point GT not verified.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#beat_the_rotating_buzz_high_speed). Project expert observations: decoded RGB24 depth; no WM predictions.

28. **[insert_onto_rotating_peg](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#insert_onto_rotating_peg) — Later expansion**. Insertion onto a rotating peg. Keep for later external dynamics validation; multi-stage manipulation/precision and scripted motion complicate initial representation/contact diagnosis. Speed variants are not independent interaction families.
   - Data: Across all 16 tasks: 12/12 assets and 32 expert/WM packages accepted; 3,200 released-3DFA evaluation episodes (2026-10-10 snapshot); persistent-point GT not verified.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#insert_onto_rotating_peg). Project expert observations: decoded RGB24 depth; no WM predictions.

29. **[insert_onto_rotating_peg_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#insert_onto_rotating_peg_high_speed) — Later expansion**. Insertion onto a rotating peg. Keep for later external dynamics validation; multi-stage manipulation/precision and scripted motion complicate initial representation/contact diagnosis. Speed variants are not independent interaction families.
   - Data: Across all 16 tasks: 12/12 assets and 32 expert/WM packages accepted; 3,200 released-3DFA evaluation episodes (2026-10-10 snapshot); persistent-point GT not verified.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#insert_onto_rotating_peg_high_speed). Project expert observations: decoded RGB24 depth; no WM predictions.

30. **[pick_moving_target_on_the_table](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#pick_moving_target_on_the_table) — External validation**. Moving-target grasping. First PhysMani choices, normal/high-speed; verify point GT and temporal/action semantics before online timing tests. High speed is a holdout only if explicitly excluded from training.
   - Data: Across all 16 tasks: 12/12 assets and 32 expert/WM packages accepted; 3,200 released-3DFA evaluation episodes (2026-10-10 snapshot); persistent-point GT not verified.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#pick_moving_target_on_the_table). Project expert observations: decoded RGB24 depth; no WM predictions.

31. **[pick_moving_target_on_the_table_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#pick_moving_target_on_the_table_high_speed) — External validation**. Moving-target grasping. First PhysMani choices, normal/high-speed; verify point GT and temporal/action semantics before online timing tests. High speed is a holdout only if explicitly excluded from training.
   - Data: Across all 16 tasks: 12/12 assets and 32 expert/WM packages accepted; 3,200 released-3DFA evaluation episodes (2026-10-10 snapshot); persistent-point GT not verified.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#pick_moving_target_on_the_table_high_speed). Project expert observations: decoded RGB24 depth; no WM predictions.

32. **[place_cups_on_rotating_frame](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#place_cups_on_rotating_frame) — Later expansion**. Place cups on rotating support. Keep for later external dynamics validation; multi-stage manipulation/precision and scripted motion complicate initial representation/contact diagnosis. Speed variants are not independent interaction families.
   - Data: Across all 16 tasks: 12/12 assets and 32 expert/WM packages accepted; 3,200 released-3DFA evaluation episodes (2026-10-10 snapshot); persistent-point GT not verified.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#place_cups_on_rotating_frame). Project expert observations: decoded RGB24 depth; no WM predictions.

33. **[place_cups_on_rotating_frame_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#place_cups_on_rotating_frame_high_speed) — Later expansion**. Place cups on rotating support. Keep for later external dynamics validation; multi-stage manipulation/precision and scripted motion complicate initial representation/contact diagnosis. Speed variants are not independent interaction families.
   - Data: Across all 16 tasks: 12/12 assets and 32 expert/WM packages accepted; 3,200 released-3DFA evaluation episodes (2026-10-10 snapshot); persistent-point GT not verified.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#place_cups_on_rotating_frame_high_speed). Project expert observations: decoded RGB24 depth; no WM predictions.

34. **[remove_cups_from_rotating_frame](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#remove_cups_from_rotating_frame) — Later expansion**. Remove cups from rotating support. Keep for later external dynamics validation; multi-stage manipulation/precision and scripted motion complicate initial representation/contact diagnosis. Speed variants are not independent interaction families.
   - Data: Across all 16 tasks: 12/12 assets and 32 expert/WM packages accepted; 3,200 released-3DFA evaluation episodes (2026-10-10 snapshot); persistent-point GT not verified.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#remove_cups_from_rotating_frame). Project expert observations: decoded RGB24 depth; no WM predictions.

35. **[remove_cups_from_rotating_frame_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#remove_cups_from_rotating_frame_high_speed) — Later expansion**. Remove cups from rotating support. Keep for later external dynamics validation; multi-stage manipulation/precision and scripted motion complicate initial representation/contact diagnosis. Speed variants are not independent interaction families.
   - Data: Across all 16 tasks: 12/12 assets and 32 expert/WM packages accepted; 3,200 released-3DFA evaluation episodes (2026-10-10 snapshot); persistent-point GT not verified.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#remove_cups_from_rotating_frame_high_speed). Project expert observations: decoded RGB24 depth; no WM predictions.

36. **[put_rubbish_in_moving_bin](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#put_rubbish_in_moving_bin) — Later expansion**. Place into moving container. Keep for later external dynamics validation; multi-stage manipulation/precision and scripted motion complicate initial representation/contact diagnosis. Speed variants are not independent interaction families.
   - Data: Across all 16 tasks: 12/12 assets and 32 expert/WM packages accepted; 3,200 released-3DFA evaluation episodes (2026-10-10 snapshot); persistent-point GT not verified.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#put_rubbish_in_moving_bin). Project expert observations: decoded RGB24 depth; no WM predictions.

37. **[put_rubbish_in_moving_bin_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#put_rubbish_in_moving_bin_high_speed) — Later expansion**. Place into moving container. Keep for later external dynamics validation; multi-stage manipulation/precision and scripted motion complicate initial representation/contact diagnosis. Speed variants are not independent interaction families.
   - Data: Across all 16 tasks: 12/12 assets and 32 expert/WM packages accepted; 3,200 released-3DFA evaluation episodes (2026-10-10 snapshot); persistent-point GT not verified.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#put_rubbish_in_moving_bin_high_speed). Project expert observations: decoded RGB24 depth; no WM predictions.

38. **[push_moving_button](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#push_moving_button) — External validation**. Moving-button contact. First PhysMani choices, normal/high-speed; verify point GT and temporal/action semantics before online timing tests. High speed is a holdout only if explicitly excluded from training.
   - Data: Across all 16 tasks: 12/12 assets and 32 expert/WM packages accepted; 3,200 released-3DFA evaluation episodes (2026-10-10 snapshot); persistent-point GT not verified.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#push_moving_button). Project expert observations: decoded RGB24 depth; no WM predictions.

39. **[push_moving_button_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#push_moving_button_high_speed) — External validation**. Moving-button contact. First PhysMani choices, normal/high-speed; verify point GT and temporal/action semantics before online timing tests. High speed is a holdout only if explicitly excluded from training.
   - Data: Across all 16 tasks: 12/12 assets and 32 expert/WM packages accepted; 3,200 released-3DFA evaluation episodes (2026-10-10 snapshot); persistent-point GT not verified.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#push_moving_button_high_speed). Project expert observations: decoded RGB24 depth; no WM predictions.

40. **[moving_basketball_in_hoop](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#moving_basketball_in_hoop) — Later expansion**. Moving basketball / hoop. Keep for later external dynamics validation; multi-stage manipulation/precision and scripted motion complicate initial representation/contact diagnosis. Speed variants are not independent interaction families.
   - Data: Across all 16 tasks: 12/12 assets and 32 expert/WM packages accepted; 3,200 released-3DFA evaluation episodes (2026-10-10 snapshot); persistent-point GT not verified.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#moving_basketball_in_hoop). Project expert observations: decoded RGB24 depth; no WM predictions.

41. **[moving_basketball_in_hoop_high_speed](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/#moving_basketball_in_hoop_high_speed) — Later expansion**. Moving basketball / hoop. Keep for later external dynamics validation; multi-stage manipulation/precision and scripted motion complicate initial representation/contact diagnosis. Speed variants are not independent interaction families.
   - Data: Across all 16 tasks: 12/12 assets and 32 expert/WM packages accepted; 3,200 released-3DFA evaluation episodes (2026-10-10 snapshot); persistent-point GT not verified.
   - [Depth: Depth read · 12-frame sample](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/depth/index.html#moving_basketball_in_hoop_high_speed). Project expert observations: decoded RGB24 depth; no WM predictions.

42. **[ToolContactRelease-v1](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/) — Initial core**. Tool contact, release / action conditioning. Test actual versus missed contact, post-release motion and action response from the same initial state; retain the existing pilot for regression.
   - Data: All modes pass three-seed acceptance; native RGB-D/points/contacts; small samples only.
   - [Depth: Native simulator depth GT (metres)](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/). Synchronized with RGB, persistent XYZ points and 100 Hz contacts.

43. **[HookPullDynamics-v1](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/) — Merge / reuse**. Geometric engagement / detachment. Shares the L-tool and implementation with ToolContactRelease; merge into the tool family and optionally add detachment rather than count independent coverage.
   - Data: All modes pass three-seed acceptance; native RGB-D/points/contacts; small samples only.
   - [Depth: Native simulator depth GT (metres)](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/). Synchronized with RGB, persistent XYZ points and 100 Hz contacts.

44. **[CollisionChain-v1](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/) — Initial core**. Cross-object propagation / upstream history. Primary cross-object task; predict B/C with independent A/B/C physics. Matched upstream-hidden-velocity chain pairs are not yet validated.
   - Data: All modes pass three-seed acceptance; native RGB-D/points/contacts; small samples only.
   - [Depth: Native simulator depth GT (metres)](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/). Synchronized with RGB, persistent XYZ points and 100 Hz contacts.

45. **[FreeMotionInterception-v1](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/) — Initial core**. Moving-object interception / hidden velocity. First establish H-self versus H0, then intervention timing and post-impact velocity; validated hidden-velocity pairs exist.
   - Data: All modes pass three-seed acceptance; native RGB-D/points/contacts; small samples only.
   - [Depth: Native simulator depth GT (metres)](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/). Synchronized with RGB, persistent XYZ points and 100 Hz contacts.

## Artifacts, reproduction and limits
`docs/benchmark_subset/review.json` is the bilingual source for all 45 entries. `tools/build_benchmark_subset.py` renders a public static review page, reusing existing GIFs and showing depth status. It does not simulate, collect data or invoke models:
```bash
python tools/build_benchmark_subset.py --output results/benchmark-subset-site
python -m http.server 8765 --directory results/benchmark-subset-site
```
The page contains three real RGB/XYZ/contact GIFs, searchable/category-filtered decisions, both languages and original task/depth links. Collection and online/offline evaluation use the [existing commands](../interaction-dynamics/README.en.md). The old 69 physical tests were not rerun or altered in this review. Entry/anchor/GIF/page checks are recorded in `checks.json`. Model-training adapters, parent-scene grouping, B/C hidden-state chain pairs and new persistent articulated-link points remain explicit prerequisites for formal experiments.
