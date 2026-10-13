# Bowling failure diagnosis

**Bowling v3 mainly suppresses false motion of static pins; it does not reliably predict ball–pin–pin propagation. The strongest evidence concerns conservative checkpoint selection and an inaccurate incoming ball trajectory.** Architecture, data coverage and temporal resolution are plausible contributors, not individually established causes.

This review reads the current PointWorld code, audited full-point reports, all 13 validation records, original arrays and a display subset. It independently recomputes the stationary validation baseline and a paired episode bootstrap. **No new model training/inference, GPU job, or checkpoint reselection.** Fifteen small CPU expert-controller interventions are a separate data-side diagnosis. No new PR; analysis lives on the isolated benchmark branch.

## Observed failure

On the same fresh30, four-second forecast:

- All-pin ADE: v2 **4.13 cm**, v3 **2.00 cm**, stationary **1.54 cm**.
- Moving-pin ADE: **5.34 → 5.23 cm**, stationary **5.46 cm**. Improvement over stationary is only **2.32 mm / 4.25%**.
- Moving-pin FDE worsens: **11.83 → 14.08 cm**.
- Derived tipping: v2 **53 TP / 116 FP / 23 FN**; v3 **0 / 0 / 76**. Tipping is derived from rigid fitting of predicted points; GT uses simulator tipping states.
- There are 95 moving and 205 static pins among 300. Static false-motion rate 25.6% is macro-averaged over episodes, whereas 44/205 is micro-averaged over pins.

A paired bootstrap over the 18 moving episodes gives **0.27–4.59 mm** 95% interval for ADE improvement over stationary (10,000 samples, fixed seed). This is exploratory analysis of an inspected test set. A small ADE gain does not establish event prediction.

![Actual RGB / GT / v2 / v3, seed3004](https://peiqil.com/dynamic-robot-bench-viewer/pointworld/bowling-v3/seed3004.gif)

The example has seven moving pins and six tips. Its 45-point-per-pin display subset has only **0.58–0.72 cm** maximum predicted mean displacement, versus **3.11–24.83 cm** for moving GT pins. Illustrative subset measurements are not substitutes for audited full-point scores.

## Checkpoint selection favors conservatism

The implemented score is `0.5*(moving-pin ADE + all-pin ADE) + 2 cm*static false-motion rate`.

- Selected **step1500**: validation moving ADE **5.44 cm**, FDE **13.71 cm**, tips **0 TP / 0 FP / 48 FN**, score **4.37 cm**.
- **step2750**: moving ADE **5.14 cm**, FDE **10.79 cm**, tips **24 TP / 19 FP / 24 FN**, score **5.10 cm**. Later training exhibits a dynamic response but more false motion; the formula rejects this tradeoff.
- Independently recomputed **stationary validation score is 3.82 cm, better than every logged network checkpoint**. Stationary was not actually selected as a checkpoint; it exposes the scoring incentive.

Freeze a revised validation protocol before another test: report moving ADE/FDE, tipping precision/recall and static false motion jointly, with a declared tradeoff or dynamic-quality gate. Optimizing recall alone risks v2's false positives. Removing the false-motion term alone does not guarantee selecting step2750, since all-pin ADE still favors conservative predictions. Do not select weights using the inspected fresh30.

## The incoming ball is already wrong

Before first real ball–pin contact in 18 episodes, ball-point ADE worsens **7.01 → 7.89 cm**. Last precontact visible-point centroid error worsens **11.99 → 14.11 cm**. This centroid is not a fitted ball center or direct contact-normal error. Ball radius is **4.25 cm**; incoming errors of this scale can change the hit/miss, impacted pin and collision timing. We do not derive contact truth from forecast proximity.

The separately trained realized-future-robot-path diagnostic also misses **76/76** tips. Feeding that path to the selected main weights does not recover them either. Robot-plan error is not the sole bottleneck; these experiments do not prove it irrelevant.

## Other contributors: facts versus hypotheses

**Data/optimization:** 94 of 206 training episodes have moving pins; only **12.8%** of pin–future-frame slots exceed 1 cm displacement. Early precontact and permanently static slots account for 87.2%. Episodes are sampled uniformly. Average loss-weight mass is ball 42.2%, moving pins 18.9%, static pins 23.9%, background 15.0%; this is not gradient contribution. A 2 cm Huber loss bounds large-residual gradients and may favor common small-motion forecasts under unresolved branching. This is a hypothesis, not proof that Huber necessarily causes failure. v2 already demonstrates that movement weighting alone does not prevent false positives.

**Architecture:** small-DROID jointly processes current scene points and robot plan points with PointTransformer attention; one head emits ten future displacement vectors. It can model cross-point relations. However, there is no explicit passive-body velocity state, sequential collision integration or contact/phase objective in this run. Recorded contacts are not used in its training loss. Rigid rotation and indirect propagation must be learned implicitly from point regression. One seed and 206 episodes for approximately 51M trainable parameters do not determine the architecture's limit; training-subset overfitting has not been tested.

**Time:** contacts are logged at 500 Hz, forecasts at **0.4 s** intervals over **4 s**. Direct long-horizon regression without phase supervision weakly constrains contact onset/order. Shorter and denser windows should isolate this effect; sparse outputs alone do not prove endpoint prediction impossible.

**History:** `context_frames=1`, and the encoder reads only scene frame0. Repeating the current points eleven times is not history. Every query is before pushing with near-zero ball speed. This does not evaluate the project's **4D MAE / H-all / masking** idea. Adding earlier stationary frames is insufficient. Add post-launch and pre/post-contact queries, matched velocity/contact-history pairs, and an actual history input path.

Existing input, identity, time, restoration and 416 full-prediction checks reduce concern about known display/label misalignment; they do not eliminate every implementation bug. GT depth, fixed physics and a single training seed limit conclusions.

## Next diagnostic sequence — proposed, not executed

1. Overfit 8–16 training trajectories, measuring ball error, moving-pin FDE, tipping recall and false motion separately. Failure here prioritizes encoding/loss/normalization/optimization checks; successful memorization shifts attention to coverage/generalization.
2. Separate robot→ball, ball→one pin and pin→another pin with shorter controlled CollisionChain windows. Report per-object/per-phase errors; retain negative examples.
3. Freeze validation tradeoffs and stratify hit/miss, direct/glancing and single/multiple propagation. Increase postcontact dynamic coverage while retaining static-point supervision.
4. Implement H0/H-self/H-all on post-launch queries, then upstream-object masking. Hold current geometry, RGB-D, future commands and splits fixed. Oracle velocities/contacts remain labels or explicitly separate diagnostic inputs.
5. An Oracle future-ball-path diagnostic can isolate downstream propagation, but is unavailable to deployed forecasts and must be reported separately. If accurate ball inputs still fail, investigate contact/phase supervision, rigid constraints or recurrent state representations.

## Separate issue: earliest expert GIFs

The original smoke seeds0/1/2 knock **8/0/0** pins; they are not learned-model results. All three original qpos/qvel/actions replay bit-exactly against earlier HDF5.

- Seed1's planned line misses every initial pin center by at least **12.0 cm**. Actual release heading is 38.7°, with **18.1 cm** lateral offset at the head row. Center-aim-only changes this same reset from **0 to 8 pins**.
- Seed2 plans **−9.2°** but releases at **+36.8°**, about **46.0°** off, with **42.6 cm** lateral offset. None of four small aim/side/orientation interventions recovers a hit.
- Removing all tested perturbations gives **0/6/0**; seed0 falls from eight to zero. Three seeds do not establish a stable controller improvement or population success rate.

Expert negatives warrant stratified data. They cannot explain the model missing every tip when fresh30 actually contains 18 moving episodes and 76 GT tips.

## Evidence and reproduction

[bowling_failure.json](bowling_failure.json) includes source hashes, validation curves, the new baseline and bootstrap. [Expert diagnosis](bowling_expert_diagnosis.json) is separate. Both tools use the isolated benchmark CPU runtime:

```bash
.runtime/ocbench-cpu/bin/python tools/analyze_bowling_model_failure.py --pointworld-root /path/to/PointWorld --output docs/benchmark_subset/bowling_failure.json
.runtime/ocbench-cpu/bin/python tools/analyze_ocbench_bowling.py --source results/ocbench-bowling/acceptance-004 --output results/ocbench-bowling/new-diagnosis --render
```

Primary local evidence: PointWorld `reports/bowling-v3-{results,diagnostic-results,contact-diagnosis,data-audit}.json`, `bowling-v2-data-audit.json`, `benchmark_adapters/{run_bowling_v3,collect_bowling,prepare_bowling_v3}.py`, `pointworld/base.py`, `scene_featurizer.py`. Training commit `ef870090`; read-only checkout `2d45b414`. Official [PointWorld source](https://github.com/NVlabs/PointWorld) and [Bowling expert](https://github.com/seohongpark/ocbench/blob/6939a1e84f7ce9dbdd20c9f80d4cf335e8f83b49/ocbench/oracles/primitives/bowling.py).

[Model GIFs and fresh30](https://peiqil.com/dynamic-robot-bench-viewer/pointworld/bowling-v3/) · [中文](README.zh.md).
