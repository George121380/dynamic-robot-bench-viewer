# Interaction-Aware 4D Dynamics: implementation and acceptance
Four interaction protocols extend the existing benchmark, reusing ManiSkill's Panda, table, tools, ball and controller. Original registrations, conveyor runner and depth paths remain available. Branch: `task/interaction-dynamics-v1`; unmerged into private main, no PR. Final counts and retained failures are in [validation.json](validation.json). Interface acceptance, physical mode verification and model performance are separate.

[中文](README.zh.md) · [complete task inventory](task_inventory.json) · [anonymous GIF gallery](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/) · [existing depth report](../benchmark_tasks/DEPTH_RUN.en.md)

## Step 0: inspected implementation
Audit preceded implementation at `c39a8799`. The earlier 42 visual entries include dataset and aggregate entries, rather than 42 unified runnable environments.
- Existing implementation: Isaac Sim dual-X5 conveyor manipulation; separate MuJoCo UR5e puck collision (`9985d495`), with robot→A→B propagation.
- Existing ManiSkill diagnostics: PullCubeTool-v1, PokeCube-v1, RollBall-v1, PushT-v1, PickCube-v1 and Panda finger articulation. These cover L-tool pulling, peg pushing, rolling, off-centre pushing and grasp/release. A diagnostic recording is not necessarily a successful task policy.
- PhysMani: 16 native moving-target/support/insertion/grasp tasks, plus an aggregate catalog entry.
- RoboCasa: original-state RGB-D replay for OpenDrawer, PanTransfer, CloseFridge, SlideDishwasherRack, StackBowlsCabinet, CoffeeSetupMug, SlideToasterOvenRack and StirVegetables; no new unified policy adapter.
- ToolHang / AdroitHandHammer original-state replay; two native RLBench expert RGB-D paths; MOVi-C, CoPhy, Physion and CLEVRER offline data/generation. Matching TurnFaucet-v1 assets remain blocked; its previous GIF is v0.
- Existing ADE/FDE/history evaluators and WebSocket transport have specific model and robot assumptions. New Panda recording uses an explicit versioned schema, without reusing the dual-X5 recorder.

Gaps: three-body propagation, interception controls, fixed physical point identities, substep contact truth, matched hidden-state pairs and explicit parameter/composition holdouts. Inventory JSON lists all 42 previous entries without rewriting their historical implementation status.

## Protocols and success definitions
New IDs preserve upstream IDs and native task criteria. `mode_verified` verifies the intended positive or negative interaction; legacy `success` remains its compatibility alias. `task_success` separately records physical goal achievement: a negative control can have mode_verified=true and task_success=false. It is not the upstream task-policy score. After environment creation, `simulation.prepare` establishes physical grasps, layouts and the precommitted plan; bare Gym reset only constructs the upstream base scene.

### Tool contact/release
`tool_contact_release` / `ToolContactRelease-v1` extends PullCubeTool using the original L-tool and cube.
- engage_pull: real force contact and more than 4 cm negative-X pull.
- near_miss: no force contact, target displacement below 5 mm.
- contact_release: momentum transfer, final contact at least 0.5 s before the end and more than 3 mm subsequent target motion.
- failed_engagement: real contact without the 4 cm intended pull; weak or off-direction motion is allowed.

### Hook/pull
`hook_pull` / `HookPullDynamics-v1` reuses the same L-tool geometry and implementation.
- successful_engagement: geometric hooking and a pull beyond 4 cm.
- hook_miss: no force contact and a stationary target.
- ineffective_contact: actual contact without the intended pull.
- detachment: initial contact/motion followed by geometric disengagement through lift/side motion, at least 0.5 s before the end.

No weld, fake attachment or target pose-following is used. Effective engagement is an explicitly approximate velocity-following annotation conditioned on actual solver contacts and more than 5 mm negative-X progress.

### Collision chain
`collision_chain` / `CollisionChain-v1` extends PokeCube with independent B/C bodies and its physically grasped peg.
- direct_push: robot-controlled peg→A, B outside the propagation path.
- two_body: tool→A→B, B displacement greater than 1.5 cm.
- three_body: tool→A→B→C, real A–B and B–C contact and ordered motion onset A<B<C.
- near_miss: offset B, no A–B force contact and B displacement below 5 mm.
- failed_propagation: real A–B contact but B displacement below 1 cm; explicit 5 kg / friction 0.8 B override, never frozen state.
- collision_free_motion: contact release followed by independent B motion.

Verification excludes direct robot/tool contact with B/C. A is the native box; B/C support box/cylinder geometries. Held-out mixed composition is explicit.

### Free-motion interception
`free_motion_interception` / `FreeMotionInterception-v1` extends RollBall. Initial linear and consistent rolling angular velocity are set before recording; subsequent states are physically integrated.
- interception / early: actual hand–ball collision modifies pre-existing motion.
- missed / late: spatial/timing miss with moving ball and no robot–ball force contact.
- redirection: moving post-contact velocity changes direction by more than 45°.
- no_intervention: the same free-motion setup with no intervention.

Ball points lie on an analytic sphere. Hand points are a documented link-bound bounding-box reference, not an exact robot mesh surface or a merged finger articulation.

## Recording and model boundary
HDF5 schema `interaction-dynamics-v1`: 5.5 s, 110 controls at 20 Hz, 111 observations and 550 contact samples at 100 Hz. Default: 12 fixed points per object.
- `observation/`: uint8 RGB, float32 depth_m in metres, intrinsic, OpenCV world_to_camera, time, Panda robot_state (9 qpos + 9 qvel).
- `action/command[N,7]`: actually submitted normalized pd_ee_delta_pose controls ordered dx,dy,dz,rx,ry,rz,gripper. Deltas use robot-root coordinates and native controller scaling; −1 closes and +1 opens. Rotation commands are zero here. Requested commands are not measured TCP velocity.
- `privileged/`: poses[T,O,7] (XYZ+WXYZ), linear/angular velocities[T,O,6], local_points[O,P,3], points[T,O,P,3], persistent point/object/link IDs, complete native initial-state snapshot, physics_time, contact_state, impulse_Ns, force_N, contact_locations, phase and progress_displacement_m[T,O] (position displacement from the first frame).
- Sample local points once; transform by actual body/link poses at every frame. Native hand link index is retained; independent actors use link ID −1.
- Every native SAPIEN CPU PhysX substep is queried. Any solver-point impulse above 1e−7 Ns establishes force-bearing contact. Raw points/separations remain available; positive solver separation does not invalidate force contact. Initial ongoing contacts are left-censored.
- Pair-summed impulses have normalized pair orientation; raw point impulses retain engine orientation. Force is impulse divided by physical dt.
- Motion onset uses a 5 mm displacement threshold on the 20 Hz grid. Engagement/coupled-motion/phase are explicitly approximate velocity/contact annotations, not engine attachment states.

`model_window` allowlists current RGB-D/calibration/proprioception, current points, permitted past points and precommitted future controls. H0 has no history; H-self keeps the designated target (default ID 1); H-all keeps all entities. Point masking drops a selected point's entire past; object masking groups all links by physical object_id; H-self uses the same grouping. Current oracle points are optional (`include_current_points=False` removes them); results with oracle input should not be labeled pure-RGB perception performance. Target velocities, mass, contact truth, future poses and success labels never enter model requests.

## Physical diagnostic pairs
Each pair stores IDs, held/changed variables, native initial-state/action hashes, future response difference, current RGB/depth/proprio/pose matching, and acceptance. Reset-time writes precede the complete physical integration of histories/futures.
- Hidden velocity: moving/resting ball matched at frame 20, identical future controls, differing hidden velocity. Strict flags compare all nonhistory model fields exactly. Micrometre differences in current oracle points make the default strict flag false; omitting those points yields a strict pair. Pixel matching is reported separately, never equated with all-input identity.
- Action counterfactual: engage-pull versus near-miss, identical complete native initial state and changed precommitted controls, anchor 0.
- Contact history: real early interception versus a resting branch at the matched later ball pose, matched robot/current observation and equal future actions, anchor 80. Require real past target contact in A and none in B.
- The first tool-based contact-history attempt was rejected for observable mismatch and retained as diagnostics-001.

These episodes diagnose history/action responsiveness. Learning these capabilities still requires subsequent training and ablation; this implementation provides data and evaluation interfaces.

Use the complete pre-anchor history for diagnostics: e.g. `model_window(path,80,history=80,future=30)` for contact_history, retaining the early real contact. Ordinary random windows default to history=10. For strict Hidden Velocity current input, use `include_current_points=False`; the online equivalent is `--no-oracle-current-points`, requiring a compatible predictor. Stationary/CV smoke controls require current points.

## Randomization and partitioning
Record seed/family/config, sampled values, mode overrides, runtime versions and source hashes. ID scale 0.94–1.06, target mass 0.055–0.075 kg, friction 0.018–0.028, restitution 0.08–0.18; tool mass 0.10–0.13 kg with grasp friction 0.8. Layout, spacing, angle, contact offset, speed, onset and release timing also vary.
- ID: new scene/trajectory families under seen ranges. Stable family hashes assign train/validation/test before windowing. Modes from the same scene share a family.
- OOD Geometry: scale 1.25–1.40, explicitly disjoint size holdout, not arbitrary novel shapes.
- OOD Physics: mass 0.13–0.17 kg, friction 0.045–0.055, restitution 0.45–0.60, outside ID ranges.
- OOD Composition: three_body collision_chain only, box→cylinder→box versus ID all-box (family0) or box→cylinder→cylinder (family1). Components are seen but the full order is held out. Seen two-body prefixes are rejected as composition OOD.

OOD is test-only; pairs use a separate diagnostic split. Generate at least two ID families for composition component coverage. Small acceptance runs are not a production training dataset.

Optional `--independent-object-physics` applies to collision_chain: independently sampled A/B/C mass, friction and restitution preserve identical A/B parameters across two-/three-body siblings. Requested tool speed varies over 0.30–0.34 m/s and impact angle over ±0.025 rad. ID/OOD Physics ranges are retained; failed propagation has an explicit B override. This profile has its own family identity, preserving the original profile reproducibility. Additional 18 ID plus one OOD Physics episodes passed.

## Reproducible generation
Verified Linux CPU runtime: ManiSkill 3.0.1, SAPIEN 3.0.3, NumPy 2.0.2 and Gymnasium 1.4.0, with Panda/table assets. Install project extras using `pip install -e '.[interaction,transport]'` and native ManiSkill asset downloads. Use an existing compatible runtime or software Vulkan:
```bash
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=2
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json
python -m dynamic_robot_bench.tasks.interaction_dynamics.runner \
  --seeds 0 1 2 --families 2 --strict --output data/interaction_dynamics/id-run
python -m dynamic_robot_bench.tasks.interaction_dynamics.runner \
  --tasks collision_chain --modes three_body --domain OOD_composition \
  --seeds 0 --strict --output data/interaction_dynamics/ood-composition
python -m dynamic_robot_bench.tasks.interaction_dynamics.runner \
  --tasks collision_chain --independent-object-physics --seeds 0 1 2 \
  --strict --output data/interaction_dynamics/independent-physics
python -m dynamic_robot_bench.interaction.diagnostics \
  --seed 0 --strict --output data/interaction_dynamics/diagnostics-run
python -m dynamic_robot_bench.interaction.visualize \
  --input data/interaction_dynamics/id-run --output results/interaction-gallery
```
Select individual `--tasks`/`--modes`; OOD_geometry/OOD_physics use the same domain flag. Always use a new output directory. `tasks/interaction_dynamics/default.json` documents the reproducible configuration; actual execution uses CLI arguments.

## Online/offline evaluation
Reuse the existing XPolicyLab WebSocket observation/action RPC envelope. The prediction endpoint returns `{"points":...}` from `get_action`; these points are never executed as robot controls. Prediction is called before future simulation, with the complete control plan already committed.
```bash
python -m dynamic_robot_bench.tasks.interaction_dynamics.runner \
  --tasks collision_chain --modes three_body --seeds 0 \
  --online-predictor dynamic_robot_bench.interaction.baselines:stationary \
  --prediction-anchor 20 --prediction-future 70 --strict \
  --output data/interaction_dynamics/online-run
python -m dynamic_robot_bench.interaction.evaluate \
  --episode data/interaction_dynamics/online-run/ID_collision_chain_family000000_seed0_three_body.h5 \
  --prediction data/interaction_dynamics/online-run/ID_collision_chain_family000000_seed0_three_body.prediction.npz \
  --anchor 20 --future 70 --output results/interaction-metrics.json
python tools/validate_interaction_dynamics.py \
  --input data/interaction_dynamics/id-run --output results/interaction-validation.json
```
Set `INTERACTION_XPOLICY_ROOT` to the existing transport runtime and `INTERACTION_MODEL_URL` to your service, then use predictor `dynamic_robot_bench.interaction_transport:websocket`. Local smoke server: `python -m dynamic_robot_bench.interaction_transport --port 19875`.

Metrics: Object/Target/Moving-object ADE/FDE, per-object errors, propagation accuracy, phase-wise ADE, paired difference-of-differences response error and ID/OOD gaps. Contact timing is null without an explicit contact head. An optional contact_probability head is evaluated on the observation grid with unmatched event counts; exact native labels remain recorded. Stationary/constant-velocity are interface smoke controls, not trained world-model results.

## Files and limits
`config.py/environments.py/simulation.py` implement holdouts, registration, physical preparation and precommitted rollouts. `geometry.py/data.py` implement fixed points, atomic recording, auditing and safe input windows. `diagnostics.py/evaluate.py/baselines.py/visualize.py` provide pairs, metrics, smoke predictors and genuine GIFs. Explicit entry point: `tasks/interaction_dynamics/runner.py`; transport: `interaction_transport.py`. Tests cover transformed identities, future/split leakage, metric conventions and real WebSocket exchange. See [VALIDATION.en.md](VALIDATION.en.md).

Limits: CPU single-environment validation and small samples; unsmoothed solver-contact flicker; primitive assets/basic ranges; approximate hand surface. P1 new door/drawer link tasks and carry/slip extensions are deferred, retaining existing PickCube/articulation/RoboCasa paths. No neural model training and no replacement of the old conveyor policy evaluator or robot-specific schemas.

Upstream references: [PullCubeTool](https://github.com/haosulab/ManiSkill/blob/v3.0.1/mani_skill/envs/tasks/tabletop/pull_cube_tool.py), [PokeCube](https://github.com/haosulab/ManiSkill/blob/v3.0.1/mani_skill/envs/tasks/tabletop/poke_cube.py), [RollBall](https://github.com/haosulab/ManiSkill/blob/v3.0.1/mani_skill/envs/tasks/tabletop/roll_ball.py). Actual installed-source hashes are recorded per episode; acceptance uses installed code and execution evidence.

