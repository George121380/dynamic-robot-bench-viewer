# HPT explanation figure

This addition explains the HPT trunk in the frozen PullCube B5 architecture (`cf880fa7882665aad0d66c86adb1b45d6f14327c`). It does not change the model or describe every EgoWAM variant. In particular, the shown B5 adapter reads only the action/future slices, while the original project page also discusses observation-token conditioning.

Rebuild the new SVG, 3200 × 1800 PNG and vector PDF:

```sh
python3 4dmae/architecture/source/build_hpt.py
pdfunite 4dmae/architecture/architecture.pdf 4dmae/architecture/hpt-internals.pdf 4dmae/architecture/shared-tokenizer.pdf 4dmae/architecture/b5-figures-with-hpt.pdf
```

Requires Inkscape and Poppler. The three-page bundle places HPT between the overview and tokenizer figures. The later query-entry revision below updates the overview and both bundles.

Evidence:

- [EgoWAM §4.1](https://arxiv.org/html/2607.08436v1#S4.SS1) and [Appendix B.1](https://arxiv.org/html/2607.08436v1#A2.SS1): learned action/future tokens, 64/16 counts, shared 256-dimensional 16-block trunk.
- [Original HPTModel](https://github.com/GaTech-RL2/EgoWAM/blob/c87617fe37a6ed6a951e6b176ad552200c425c93/egowam/algo/hpt_wm.py#L419): query parameters. The original file's SHA-256 is `80eed74f19eeec81f92c30c46f400b7566eacb0599acba9a1afe89d0ae4adb0d`; the HPTModel class AST matches the vendored class.
- [B5 adapter](https://github.com/George121380/4dmae/blob/cf880fa7882665aad0d66c86adb1b45d6f14327c/four_d_mae/models/egowam/model.py#L107): 16 history tokens, context computation, action-only inference.
- [Token assembly/readout](https://github.com/George121380/4dmae/blob/cf880fa7882665aad0d66c86adb1b45d6f14327c/four_d_mae/models/egowam/vendor/hpt.py#L487): `[action, future, observations]` order and output slices.
- [Transformer block](https://github.com/George121380/4dmae/blob/cf880fa7882665aad0d66c86adb1b45d6f14327c/four_d_mae/models/egowam/vendor/hpt_nets.py#L231): pre-norm self-attention and MLP, each with a residual connection. No causal mask is supplied by this adapter.
- [Trajectory path](https://github.com/George121380/4dmae/blob/cf880fa7882665aad0d66c86adb1b45d6f14327c/four_d_mae/models/egowam/trajectory.py#L33): tokenize the noisy trajectory, add flow time, cross-attend to HPT context, predict velocity. Sampling keeps C history fixed.

The schematic omits dropout, normalization of input coordinates, and invalid-point handling. It distinguishes the learned query parameters, the scene-conditioned output features, the physical anchors, and the random generation state. The name HPT alone does not imply pretrained trunk weights in this run.

## Query entry in the overview

The user asked to locate query inside the pipeline, not add explanatory paragraphs. The previous `#completion` text/table section has been removed; its fragment now points into the overview for link continuity. The main diagram separates the formerly combined tokenizer/decoder box:

`Point query Q (current XYZ) + noisy tracks/status → Tθ → point token q → trajectory decoder → Q completion`.

The HPT path is labeled `16 future-context tokens (K, V)`. Inside decoder cross-attention, point features form the query and HPT context supplies keys and values. Flow time enters the decoder; completion uses 50 flow steps. The lower C/Q panel notes that C uses the same decoder with observed past clamped. This is a schematic of the Q call, not a new network architecture.

Rebuild the updated overview SVG/PNG/PDF and both PDF bundles:

```sh
python3 4dmae/architecture/source/build_overview.py
```

`pullcube-rgb.png` is the same recorded thumbnail embedded in the original overview. The generator does not rewrite the HTML, HPT inset, or tokenizer figure.

Evidence remains frozen to `cf880fa7882665aad0d66c86adb1b45d6f14327c`: `TrajectoryTokenizer.forward`, `TrajectoryDecoder.forward`, and `HistoryExtension.sample` in [trajectory.py](https://github.com/George121380/4dmae/blob/cf880fa7882665aad0d66c86adb1b45d6f14327c/four_d_mae/models/egowam/trajectory.py); [CrossBlock.forward_cross](https://github.com/George121380/4dmae/blob/cf880fa7882665aad0d66c86adb1b45d6f14327c/four_d_mae/models/egowam/vendor/denoising_nets.py) calls cross-attention as `cmha(x, cond, cond)`. The point token is updated by time embedding and self-attention before the cross-attention operation; those internal operations remain expanded in the tokenizer figure.

Scope is unchanged: privileged 64 C / 64 Q persistent surface points on cube/tool, not the newer 12 C / 12 Q scene-motion sampler or an object-holdout result. Point-selection evidence: [oracle.py](https://github.com/George121380/4dmae/blob/cf880fa7882665aad0d66c86adb1b45d6f14327c/benchmarks/pull_cube_tool/oracle.py).
