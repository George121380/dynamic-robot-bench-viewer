# UnifiedACT v2: minimal ACT changes

The standard condition directly calls upstream LeRobot0.4.3 `ACT.forward()`. Current image encoding, CVAE, encoder/decoder, action head and native L1+10KL semantics remain native. The entire reviewed difference is [act-forward.patch](act-forward.patch); an executable regression compares installed upstream source, the saved original and this patch. No runtime AST manipulation, monkey patches, forward hooks or changes to the installed package are used. The wrapper no longer reimplements ACT's posterior or action forward path.

There are two explicit extension sites: causal RGB-history tokens before the encoder, and point conditioning after the encoder. Observation-only point heads use an explicit zero-prior memory readout. Constructor/parameter shapes of native ACT are unchanged. Upgrade upstream only after reviewing the source diff and passing parity checks.

V2 removes trajectory-aligned image gathering, visual point projections, calibration dependencies and a hidden auxiliary RNG counter. Keep shared history MLP, one normalized cross-attention and the original action decoder/head. Stationary versus tracks now changes only numerical displacement at matched anchors, time, masks, RGB and capacity. Past/future point decoders remain separate, query-chunkable and free of3NN/rigid output corrections. The optional bounded-gradient experiment is isolated; normal OFF/detached training uses standard backward and AdamW.

Dynamics accepts only declared piecewise-constant controls without controller preview. A state query atτ masks commands beginning at or afterτ. Suffix edits cannot affect earlier predictions under the same applied prefix. Preview controllers need a different verified control export/protocol.

LeHome now has an independent loader: actor observation selection is separate from auxiliary labels; no legacy imports/sys.path edits; actual consumed cache SHA256s are checked on startup and receipts identify those bytes. Concurrent edits are detected. RGB-only auxOFF does not read point files. Raw trajectories/calibration are no longer consumed. Existing point histories are explicitly ORACLE persistent vertices, including past occluded coordinates; the masks do not establish sensor visibility or tracker availability.

The v2 data contract requires actual keys, dimensions/dtypes/times/masks, source/exporter hashes, causal tracking/occlusion declarations, control semantics, commitment batch/time and plan coverage. A validator checks metadata consistency, not the real-world truth of provenance. Dynamics intervention commands are not automatically policy expert labels.

Validation reports final denormalized prior-zero action chunk/first-action MSE, per-dimension errors/units, and completion all/moving/static EPE against repeat-current and, when available, a global observed-track mean LS velocity reference. The reference consumes no hidden labels and is not hidden-point GT velocity. Only full validation with moving targets is eligible to pass the quality gate; training/partial windows remain diagnostic.

Resume identity includes all own modules (including data), native ACT, dependency versions, recipe and verified data bytes. Replayed log suffixes are archived, valid main logs have unique steps, attempts/wall time are accumulated. CPU synthetic regression compares interrupted versus uninterrupted model, Adam state and RNG bitwise. Such unit updates are not real-task training.

`ObservationHistory` and `ChunkExecutor` provide explicit synchronous history, reset, short execution prefix and action queue. Point windows come from an external causal tracker. Prediction horizon does not determine execution prefix. CPU queue tests pass; A thin bridge connects the existing LeHome rollout while preserving its legacy branch. Actual Isaac execution/quality, real tracker and asynchronous latency handling remain unvalidated.

Read [Chinese specification](README.zh-CN.md), [review response](review-response.zh-CN.md), [data contract](data-contract.json), [validation](validation.json) and [real-data check](real-data-check.json). V1 is retained in `v1/` and Git commitfe3ec86; v1 checkpoints are not silently converted. The architecture is a shared model family, not a goal-conditioned multitask checkpoint or an established world-action planning system.

```bash
python -m unittest discover -s tests -p 'test_unified_act*.py' -v
python -m dynamic_robot_bench.models.unified_act.runner preflight --config configs/unified-act/lehome-preflight.json
```

The example uses run schema v2 and0 updates. Evaluation requires a checkpoint. Real-task training and node allocation remain on hold. CUDA/BF16, full cross-task exports and closed-loop performance are not established by CPU checks.

For an isolated checkout, explicitly reuse the deployed runtime with LEHOME_RUNTIME, LEHOME_PY, LEHOME_LAB and LEHOME_ASSETS_ROOT, then invoke this checkout's integrations/LeHome/act_pilot_run.sh with a v2 checkpoint and explicit execution prefix. The launcher adds the current code root to PYTHONPATH. This documents a future acceptance entry point; it was not executed this turn.
