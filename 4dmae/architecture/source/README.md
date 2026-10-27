# HPT explanation figure

This addition explains the HPT trunk in the frozen PullCube B5 architecture (`cf880fa7882665aad0d66c86adb1b45d6f14327c`). It does not change the model or describe every EgoWAM variant. In particular, the shown B5 adapter reads only the action/future slices, while the original project page also discusses observation-token conditioning.

Rebuild the new SVG, 3200 × 1800 PNG and vector PDF:

```sh
python3 4dmae/architecture/source/build_hpt.py
pdfunite 4dmae/architecture/architecture.pdf 4dmae/architecture/hpt-internals.pdf 4dmae/architecture/shared-tokenizer.pdf 4dmae/architecture/b5-figures-with-hpt.pdf
```

Requires Inkscape and Poppler. The original overview, tokenizer figure and two-page PDF are unchanged. The three-page bundle inserts HPT between them.

Evidence:

- [EgoWAM §4.1](https://arxiv.org/html/2607.08436v1#S4.SS1) and [Appendix B.1](https://arxiv.org/html/2607.08436v1#A2.SS1): learned action/future tokens, 64/16 counts, shared 256-dimensional 16-block trunk.
- [Original HPTModel](https://github.com/GaTech-RL2/EgoWAM/blob/c87617fe37a6ed6a951e6b176ad552200c425c93/egowam/algo/hpt_wm.py#L419): query parameters. The original file's SHA-256 is `80eed74f19eeec81f92c30c46f400b7566eacb0599acba9a1afe89d0ae4adb0d`; the HPTModel class AST matches the vendored class.
- [B5 adapter](https://github.com/George121380/4dmae/blob/cf880fa7882665aad0d66c86adb1b45d6f14327c/four_d_mae/models/egowam/model.py#L107): 16 history tokens, context computation, action-only inference.
- [Token assembly/readout](https://github.com/George121380/4dmae/blob/cf880fa7882665aad0d66c86adb1b45d6f14327c/four_d_mae/models/egowam/vendor/hpt.py#L487): `[action, future, observations]` order and output slices.
- [Transformer block](https://github.com/George121380/4dmae/blob/cf880fa7882665aad0d66c86adb1b45d6f14327c/four_d_mae/models/egowam/vendor/hpt_nets.py#L231): pre-norm self-attention and MLP, each with a residual connection. No causal mask is supplied by this adapter.
- [Trajectory path](https://github.com/George121380/4dmae/blob/cf880fa7882665aad0d66c86adb1b45d6f14327c/four_d_mae/models/egowam/trajectory.py#L33): tokenize the noisy trajectory, add flow time, cross-attend to HPT context, predict velocity. Sampling keeps C history fixed.

The schematic omits dropout, normalization of input coordinates, and invalid-point handling. It distinguishes the learned query parameters, the scene-conditioned output features, the physical anchors, and the random generation state. The name HPT alone does not imply pretrained trunk weights in this run.
