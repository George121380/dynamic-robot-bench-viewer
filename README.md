# Dynamic Robot Bench trajectory viewer

Public, anonymous visualization: https://george121380.github.io/dynamic-robot-bench-viewer/

This repository contains the static viewer and public trajectory previews.
The dynamic benchmark implementation is maintained in a separate private repository.

Official source: [RoboDojo-Benchmark/RoboDojo](https://huggingface.co/datasets/RoboDojo-Benchmark/RoboDojo), revision `35efbc7dedfdbeeb6e95fb749bd885d73d483e41`.
All 100 original conveyor demos are included, preserving official video bytes and episode numbers.
Each official preview is checked against its source SHA-256, and all three cameras have the same frame count and 25 Hz clock as the HDF5 numeric record.
The dataset card declares Apache-2.0. Original attribution and checksums are in `official/source.json`.

Official HDF5 does not record conveyor speed. The original task selects conveyor asset 00000 with a constant speed magnitude of approximately 0.10 m/s; this is configuration evidence, not a measured per-episode speed curve.
Scripted previews are real simulator recordings at randomized speeds. They include failures and are a snapshot of ongoing pilot collection.
The current scripted expert uses a limited grasping workflow. Arm-activity and tool-angle metrics are in `comparison.json`; the two sources are not a paired policy-success comparison.

No model checkpoint scores are reported here. Full training HDF5 files and credentials are not published in this repository.
