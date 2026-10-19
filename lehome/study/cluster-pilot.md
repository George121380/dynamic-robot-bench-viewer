# Three-hour B20z paired pilot

The user explicitly authorized up to32 B200 GPUs from2026-10-19 19:56:28 to22:56:28 UTC. Exact-ID cleanup starts at22:53:28. Formal30,000-step training remains paused. Jobs use`ei-liupeiqi-wam-training-actpilot-s<seed>` and one full eight-GPU node per seed, with independent single-GPU runs rather than a larger global batch.

Seeds1000–1003 each run the five principal ACT/RGB-H/Geometry/Tracks/Completion conditions plus three exploratory completion-gradient controls: output initialization gain100 (std0.01), auxiliary weights0.1/1/10. Three fixed training-window zero-update probes measured the original weighted shared-gradient ratio at2.1e-6–6.8e-6, versus0.14–0.16 for gain100/weight10. These are mechanism controls; any validation-selected winner remains exploratory.

All32 runs cap at2000 optimizer updates, effective batch16, identical16train/4validation episodes, frozen lossless data, paired per-seed ACT initialization/sample order, sixteen-frame history, native ACT backbone, AdamW lr1e-5, clip10 and BF16. Full427-window FP32 prior-zero validation runs every250 updates. Primary offline comparisons use fixed2000-step results; all matched intermediate budgets are retained and validation-best weights are labeled separately. Developer H800 results remain engineering checks rather than mixed-hardware principal results.

Root:`results/lehome_garment_folding/act-b20z-validation-01`. Exact IDs are in`jobs.json`, platform state in`lease-status.json`, node and per-run receipts retain actual outcomes. An isolated personal Git clone freezes execution source. Each node copies and verifies the lossless cache to private/tmp and performs a real full-resolution BF16 backward gate. A developer-host watchdog cancels only exact registered IDs with verified names; workers additionally enforce the absolute deadline on their own child process groups.

Privileged simulation GT tracks and a single garment limit conclusions. This is not a final-test or multi-scene success-rate study. The existing500-step developer pilot and single-pose ten-rollout protocol remain unchanged.
