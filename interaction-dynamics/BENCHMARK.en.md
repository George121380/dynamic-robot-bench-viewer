# Interaction dynamics benchmark specification

Four P0 protocols and 20 modes are implemented. The basic 60/60 rollouts and 19/19 additional independent-physics chain episodes passed small-sample acceptance. Native Panda/PhysX environments are reused; no model was trained. See the [inventory](task_inventory.json), [implementation and commands](README.en.md), and [actual GIF gallery](https://peiqil.com/dynamic-robot-bench-viewer/interaction-dynamics/). [中文](BENCHMARK.zh.md).

## Tasks and samples

- **ToolContactRelease-v1**: L-tool contact, momentum transfer and release. Positive controls pull or induce post-release sliding; negatives miss or contact ineffectively. Physical goal: real contact and more than 4 cm negative-X pull.
- **HookPullDynamics-v1**: reuse the same L-tool for engagement, misses, ineffective contact and lift/side detachment. Same physical goal; effective engagement is a contact/velocity-following/progress heuristic.
- **CollisionChain-v1**: grasped peg pushes A; real A→B or A→B→C collisions propagate motion, including independent post-collision motion. Negatives offset B or use an explicit 5 kg/high-friction B for weak propagation. Three-body goal requires actual contacts, ordered motion onset, C displacement above 1.5 cm and no direct robot/tool contact with B/C.
- **FreeMotionInterception-v1**: ball already moves before intervention. Compare successful/early interception, spatial/timing misses, redirection and no intervention. Physical goal: real interception and velocity change above 0.02 m/s; redirection additionally exceeds 45°.

`mode_verified` verifies intended behavior, including negatives; `task_success` independently records physical goal achievement. Legacy `success` aliases mode verification. Full thresholds and retained failures appear in [acceptance](VALIDATION.en.md).

## Randomization, splits and ground truth

Task-specific scale, mass, friction, restitution, arrangement/initial velocity, tool speed/direction, contact offset and release time are randomized and saved. Chain A/B/C physics can be independently sampled; failure overrides are explicit. ID, OOD Geometry (size), OOD Physics (parameter ranges) and OOD Composition (full three-body combination) use explicit holdouts. Partition scene/trajectory families before creating windows.

Save native RGB-D/calibration, robot state and actually submitted controls. Privileged groups contain fixed local points and persistent IDs, world XYZ tracks from real poses, velocities, physics-substep contact/impulse/location/events, phases, displacement progress and success labels. Object velocity, mass and future poses never enter model requests. Hand reference points approximate its link bounding box; objects/tools use analytic geometry surfaces.

Three diagnostic types each have three seeds: hidden velocity, identical complete state with changed actions, and different contact histories. Strict Hidden Velocity omits current oracle points; Contact History is explicitly approximate with measured matching errors and full pre-anchor history. Every branch is physically integrated; held/changed variables and matching metrics are retained.

## Evaluation

Object/Target/Moving-object ADE/FDE, per-object errors, propagation accuracy, phase-wise ADE, paired action-response error and ID/OOD gaps. Contact timing is null without an explicit prediction head. Safe windows support H0/H-self/H-all, persistent-point masking and object_id masking of all links. Future conditioning uses precommitted controls, never realized future robot trajectories.

Acceptance: 69/69 CPU regressions, 20/20 exact same-seed repeats, 5/5 online/offline matches and 9/9 accepted physical diagnostic pairs. OOD probes cover selected positive modes only. Production-scale statistics, full legacy Isaac Sim GPU integration and neural-model experiments were not run. P1 new door/drawer and carry/slip extensions are deferred; existing paths remain available.
