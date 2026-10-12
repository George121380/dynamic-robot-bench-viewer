# OCBench, with Bowling as the priority addition

**Recommendation: add Bowling immediately after the controlled CollisionChain task.** Retain FreeMotion, Tool Contact/Release and CollisionChain for the initial diagnostic loop. Bowling adds ball–pin and pin–pin collisions, tipping, rotation and free motion, testing predictions of objects never directly touched by the robot.

On 2026-10-12 we audited the pinned source/release manifest, read and rendered the first official validation trajectory, and collected three CPU rollouts with seeds 0/1/2. This delivers **task selection and a depth/physics smoke entry point**. No model training, shared evaluation-runner integration, strict hidden-state pairs or MJWarp execution occurred. Branch task/benchmark-subset-v1; no PR; private main unchanged.

[中文](README.zh.md) · [RGB-D / 3D / contact GIF gallery](https://peiqil.com/dynamic-robot-bench-viewer/ocbench/) · [28-task inventory and evidence](ocbench.json) · [Numerical validation](ocbench_validation.json)

## Research fit
The robot launches a ball that travels away from the gripper, strikes pins and can propagate motion through pin–pin impacts. Eleven dynamic rigid bodies create a richer contact topology than a controlled 2–3-cube chain. Forecast the **ten pins**, particularly downstream pins still stationary at the query time, rather than only extrapolating the ball.

Proposed experiments use windows before/after rack entry at 0.2/0.5/1.0 s horizons: H-self versus H-all and masking of ball/upstream-pin histories. Hold current geometry, point queries, precommitted actions, capacity and budget constant. Report per-object persistent-point ADE/FDE, moving-object ADE, rotation, identities/count of knocked pins, propagation order and phase errors. Do not let stationary points dominate averages. Without a contact prediction head, use contact truth to partition errors rather than inferring unreliable event times from predicted points.

These are **proposals**, not model results or demonstrated necessity of physical history. A non-Markovian demonstration policy does not establish hidden-physics ambiguity. The default state observation explicitly includes ball linear/angular velocity: exclude these for Hidden Velocity tests and retain them only as privileged labels.

## Environment and original scoring
- IDs: `bowling-task1-v0` (MJWarp), `bowling-cpu-task1-v0`, and `visual-bowling-cpu-task1-v0`. **No Bowling lite variant exists.** No duplicate environment was registered.
- UR5e + Robotiq 2F-85. Actions are seven normalized joint deltas: six arm joints plus the gripper. Arm scales are 0.18/0.18/0.18/0.36/0.36/0.36 rad; gripper scale 0.12 in normalized opening, not radians. This is not the Panda 7D Cartesian command interface.
- Default control 50 Hz, physics 500 Hz, 500 controls / 10 seconds, ball radius 0.0425 m, ten pins. State observations are 102D; complete qpos/qvel are 91D/80D. Official visual observations contain front/side/wrist 224² RGB; the smoke renders front 160² RGB-D.
- A pin is cumulatively knocked when its local vertical axis has world-Z component below 0.75. Reward increases by 0.1 per newly knocked pin, maximum return 1.0. **Upstream success stays false**, so it is not a Bowling success-rate metric. Report pins_knocked/return; label any added all-ten-knocked success separately.
- Resets randomize ball XY, rack XY as a group and robot initialization. The CPU primitive randomizes launch direction/speed, approach, height, gripper and tilt. This smoke does not randomize mass/friction/geometry or implement held-out OOD splits.
- Invisible boundary walls and a gripper-limiting plane affect dynamics. Record these constraints; do not interpret boundary interactions as an unbounded ordinary tabletop.

## Released data and depth
At release revision `fd771640f7a47879d8b06657fe05389641b5bff9`, Bowling has **10,000 train / 1,000 validation episodes**, each with 500 controls. The train/validation NPZs are 3,470,914,682 / 346,792,143 bytes. These are manifest counts, not full local downloads.

Validated HTTP ranges into the official validation archive confirm float32 observations [501000,102], actions [500000,7], **qpos [500000,91], qvel [500000,80]**. Complete simulation states are saved before actions. There are no RGB, depth or calibration arrays, and no released Bowling visual dataset.

We read the first 500 states and re-rendered 30 frames with matching assets in CPU MuJoCo. About 1.80 MB of ranges were transferred; no 3.47 GB train download or pickle execution. This is a partial numeric read, not a full-archive SHA256/CRC audit. Observations include the terminal endpoint, while qpos/qvel have only 500 pre-action states per episode: frame 500 was not fabricated. Align sparse image indices and dense actions explicitly.

The convenience `load_dataset` drops qpos/qvel, returning only standard BC fields; use the raw NPZ for rendering. Re-rendered depth pairs with the newly rendered RGB. CPU and MJWarp are not numerically identical, and restoring original states does not validate action-based GPU trajectory replay. No original Bowling RGB exists for pixel matching.

Saved poses support persistent material points, but a CPU mj_forward cannot recover the original MJWarp contact events or forces. **No contact truth is exported for the official re-render.** Live CPU collection supplies solver contacts separately.

![Official Bowling validation trajectory: RGB / Z depth](https://peiqil.com/dynamic-robot-bench-viewer/ocbench/media/official-val-episode0-rgb-depth.gif)

**Depth: original-state rendering verified; new simulated RGB-D collection also works, without a depth-estimation model.** Depth is metric camera-axis Z. The 7 m far-plane background is excluded by valid masks. macOS warned that ARB_clip_control is unavailable; initial-frame floor-ray checks on all four samples have maximum error about 0.037 mm. This checks floor geometry/calibration, not all meshes, occlusions or pixels. The 30 uniformly selected frames play at 100 ms/frame, about 3.33× speed.

## Actual physics and persistent identity checks
Seeds 0/1/2 each run 500 controls with healthy states and knock **8/0/0** pins. Seed 0 records ball contacts with pin_0/2/5 plus eleven pin–pin pair types. Seeds 1/2 have no ball–pin or pin–pin contacts and score zero. They are retained natural negatives, not guaranteed controlled Near Miss protocols.

Each episode contains 501 rigid-state frames, 101 RGB-D frames at 10 Hz and solver contacts every 2 ms at 500 Hz. Eleven objects each bind 24 fixed BODY-local points: fixed sphere samples for the ball and compiled mesh vertices for pins. Point IDs persist and poses transport the same material points; local-coordinate roundtrip error is below 4e-16 m. Points include occluded surfaces and are not independently resampled depth clouds. Robot link points are not included.

The original control logic is retained; nstep=10 is split into ten mj_step calls for logging. For seed 0, qpos/qvel/actions match standard upstream stepping exactly and a repeated seed reproduces them exactly. No teleportation, imposed target-motion interpolation or downstream freezing occurs. Contacts use active MuJoCo constraints and normal mj_contactForce >1e-6 N, timestamped at the pre-integration solver state with 2 ms resolution. Continuous event intervals mark left/right censoring. Only normal force is exported; force×dt is not called a true impulse.

![New seed 0: RGB / persistent XYZ / solver contacts](https://peiqil.com/dynamic-robot-bench-viewer/ocbench/media/seed0-dynamics.gif)

**Depth: this new rollout natively stores metric RGB-D; this GIF displays RGB, fixed XYZ and contacts.**

![New seed 1: zero-score episode](https://peiqil.com/dynamic-robot-bench-viewer/ocbench/media/seed1-dynamics.gif)

**Depth: the negative rollout also stores simulated RGB-D.** All three RGB–depth GIFs are in the gallery.

## Files and reproducible commands
`tools/fetch_ocbench_bowling_prefix.py` reads pinned numeric release prefixes. `tools/ocbench_bowling_smoke.py` provides the Bowling CPU sampler/state renderer, avoiding the missing Bowling route in the upstream generic CPU generator. `tools/visualize_ocbench_bowling.py` renders actual RGB, persistent XYZ, 500 Hz contact timelines and event intervals. Dependencies are pinned in `tasks/ocbench_bowling/requirements-cpu.txt`. Full numeric outputs stay in ignored local results, not Git or the public site.

From this branch checkout:

```bash
uv venv --python 3.12 .runtime/ocbench-cpu
uv pip install --python .runtime/ocbench-cpu/bin/python -r tasks/ocbench_bowling/requirements-cpu.txt
.runtime/ocbench-cpu/bin/python tools/fetch_ocbench_bowling_prefix.py --output results/ocbench-bowling/release-prefix
.runtime/ocbench-cpu/bin/python tools/ocbench_bowling_smoke.py --output results/ocbench-bowling/run --release-prefix results/ocbench-bowling/release-prefix --seeds 0 1 2
.runtime/ocbench-cpu/bin/python tools/visualize_ocbench_bowling.py --root results/ocbench-bowling/run
```

For headless Linux, set `MUJOCO_GL=egl`; that backend was not accepted in this review. These commands generate/audit samples, not model online/offline evaluations.

Collected HDF5 `model_visible/` contains RGB/depth/valid/K/OpenCV world_to_camera, frame IDs, timestamps, 14D robot proprio (six joint positions + six joint velocities + raw gripper joint position/velocity), and actually submitted 7D actions. `privileged/` contains complete states, body poses, fixed points/IDs, knocked flags, rewards and solver contacts. The official sensor `sample.npz` and labels `privileged.npz` are separate. Raw gripper joint position is not the official normalized gripper opening.

Expert commands are generated from state and submitted before each individual step. Offline conditioning slices can use these logged commands, but this smoke **does not establish that a whole future chunk was fixed at query time**. Strict action counterfactuals must precommit a chunk before branching. Never substitute future actual robot trajectories or future privileged expert decisions for planned commands.

## Other OCBench families
The inventory lists all 28 full task IDs and official video sources. **The other 27 tasks have no depth/physics acceptance here** and do not contribute to the 44 accepted depth entries.

- block: eight tasks—single task1; double/triple task1–2; quadruple task1–3. Carrying, stacking and arrangements may support later Grasp/Release tests; ordinary successful demonstrations do not ensure dynamic failure modes.
- chamber: seven—easy task1–3, medium/hard task1–2. Drawer/window joints, locks and blocks offer articulated/compositional interactions.
- hanoi: six—single/double/triple, task1–2 each. Geometry constraints and precision insertion; defer until stable tracking/link identities.
- switch: six—3x3/4x4/5x5, task1–2 each. Neighboring colors toggle by discrete rules rather than physical inter-object collision propagation.
- bowling: one, prioritized here. No lite or released visual Bowling data; the generic project-page statement about all eight variant combinations does not apply fully.

## Maturity and remaining work
Initial software release: 2026-10-04; paper submission: 2026-10-05, roughly one week before this review. Widespread independent validation and absence of hidden bugs are not established. Issue #2 reports switch 4x4/5x5 contact-buffer overflow with newer mujoco-warp; Bowling stayed within the reporter's buffer, **not our GPU validation**. Future MJWarp runs must pin versions, check overflow and verify contacts/scores per world.

Pending: training adapter, complete scene-family splits, held-out physics/geometry/composition, strict hidden-velocity/action pairs, shared online/offline metrics, full release hashes, terminal-state and CPU–GPU replay acceptance. Existing core tasks and evaluators are unchanged. Small-sample acceptance does not prove complete benchmark integration or learned generalization.

Keep the three controlled core tasks initially, then use Bowling pin-target windows as the priority external interaction test before expanding other OCBench families.

## Primary evidence
[Project](https://seohong.me/projects/ocbench/), [paper](https://arxiv.org/abs/2610.07056), [pinned source / MIT license](https://github.com/seohongpark/ocbench/tree/6939a1e84f7ce9dbdd20c9f80d4cf335e8f83b49), [Bowling implementation](https://github.com/seohongpark/ocbench/blob/6939a1e84f7ce9dbdd20c9f80d4cf335e8f83b49/ocbench/envs/bowling_env.py), [released data](https://huggingface.co/datasets/seohongpark/ocbench/tree/fd771640f7a47879d8b06657fe05389641b5bff9/full/bowling-task1-v0), [MJWarp collector](https://github.com/seohongpark/ocbench/blob/6939a1e84f7ce9dbdd20c9f80d4cf335e8f83b49/impls/envs/streaming_data.py), [reported overflow](https://github.com/seohongpark/ocbench/issues/2). Robot assets retain upstream licenses; no third-party meshes or training results are redistributed.

