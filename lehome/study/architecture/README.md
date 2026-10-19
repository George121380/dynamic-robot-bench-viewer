# Architecture figures for slides

Two English figures describe the implemented models, rather than the proposed action-residual fusion discussed after the pilot. Both use a16:9 canvas, vector modules, schematic garment inputs, editable text and a consistent visual vocabulary: blue for RGB/policy, teal for point histories and amber for training-only computation.

- `architecture-overview.svg/.pdf/.png`: causal observations, shared visual encoding, trajectory tokens, native ACT and the pre-Transformer auxiliary tap.
- `architecture-details.svg/.pdf/.png`: point features and MLP, observed/hidden selection, five controlled observation conditions and the3NN residual auxiliary control.
- `architecture-figures.pdf`: both figures as separate pages.
- `architecture-figures.zip`: all delivery files and captions.

Use SVG for editable vector graphics in your slide editor, PDF for vector import, and the4800×2700 PNG for direct insertion. Diagrams and curves are schematic; they are not additional simulation observations or numerical experiment results. The SVG sources retain editable text. PDF lettering uses vector outlines for portable font rendering.

## Figure1 caption

**Trajectory-conditioned ACT with masked track completion.** At time t, the actor receives current RGB from three cameras, current12-D measured joints and, for history-enabled variants, a16-frame RGB window spanning0.5s. A shared ResNet-18 preserves the current image grid(900 visual tokens) and pools the15 older frames to4×4 per camera(up to720 tokens). A shared point-wise MLP encodes each of16 observed3D trajectories into one512-D token. The observation tokens and the native32-D CVAE latent feed the original ACT encoder/decoder, which predicts100×12 absolute joint targets. Training uses the native posterior from current joints and ground-truth future actions; evaluation fixes the latent to zero. A training-only completion decoder attends to positioned observation tokens captured **before** the main ACT Transformer and **excluding** the posterior latent. Hidden-point current positions and past-time queries predict48×15×3 past displacements. Hidden points and targets do not enter the actor. Auxiliary gradients reach shared observation encoders and projections, not the main ACT Transformer directly. Validation MSE uses the denormalized output joint targets in rad², with padding excluded.

## Figure2 caption

**Trajectory representation and controls.** Each point-time feature concatenates current XYZ divided by0.5m, past-minus-current XYZ divided by0.05m, relative time and a validity bit(3+3+1+1 channels). The16 time slots flatten to128 features, followed by shared Linear128→128, ReLU, Linear128→128, ReLU and Linear128→512 layers(99,072 parameters). Invalid slots are zeroed. Selection uses farthest-point sampling of64 current-visible cloth vertices and a seeded random16/48 observed/hidden split. Vertex identities persist within a window and can change across windows. ACT, RGB-H, Geometry, Tracks and Tracks+Completion retain the native actor while adding the indicated observation or auxiliary condition. The separate residual-completion experiment adds a learned correction at scale0.1 to a fixed inverse-squared-distance3NN history estimate. Connected/detached variants differ in whether auxiliary memory gradients reach shared observation encoders; detachment does not disable normal actor training. This residual is a **track-completion residual**, not an action residual.

## Provenance

Diagram source: `../../draw_architecture.py`. Implementation checked against `act_history_policy.py`, `act_residual_policy.py`, `act_pilot_data.py`, `flow_data.py` and the completed pilot manifests at source commit4ab423ce636705f19676b25883cfa7ae234e8ed4. Ground-truth3D tracks, including past positions, are privileged simulation observations; no RGB-based tracker is claimed. Cold-start invalid history tokens are omitted from ACT attention, so displayed token counts are maxima. Strong-completion weight/initialization sweeps retain the same topology and are not separate architectures in these diagrams.

Rebuild SVGs with `python3 integrations/LeHome/draw_architecture.py --output integrations/LeHome/figures/architecture-v1`. Use Inkscape for PNG export and add `--export-text-to-path` when exporting PDF. No model code, results, training hold or cluster job is changed by this drawing task.
