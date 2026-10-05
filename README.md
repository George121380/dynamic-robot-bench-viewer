# Dynamic Robot Bench trajectory viewer

Public, anonymous visualization: https://peiqil.com/dynamic-robot-bench-viewer/

This repository contains the static viewer and public trajectory previews.
The dynamic benchmark implementation is maintained in a separate private repository.

Official source: [RoboDojo-Benchmark/RoboDojo](https://huggingface.co/datasets/RoboDojo-Benchmark/RoboDojo), revision `35efbc7dedfdbeeb6e95fb749bd885d73d483e41`.
All 100 original conveyor demos are included, preserving official video bytes and episode numbers.
Each official preview is checked against its source SHA-256, and all three cameras have the same frame count and 25 Hz clock as the HDF5 numeric record.
The dataset card declares Apache-2.0. Original attribution and checksums are in `official/source.json`.

Official HDF5 does not record conveyor speed. The original task selects conveyor asset 00000 with a constant speed magnitude of approximately 0.10 m/s; this is configuration evidence, not a measured per-episode speed curve.
Scripted previews are real simulator recordings at randomized speeds. They include failures and are a snapshot of ongoing pilot collection.
The new collector samples approach and lift curves from 74 usable official teleoperation segments (17 left-arm, 57 right-arm), retargets them to live object geometry, and varies arm preference, grasp orientation, approach timing, closing timing, and lift motion. The v5 collector selects continuous IK branches and bounds velocity, acceleration and jerk. It executes one grasp plan per episode and rejects measured motion outliers or grasp-region cropping. The head-camera overlay uses native simulator intrinsics/extrinsics and an estimated contact region; it does not test occlusion. Historic versions remain available through the version filter. The old vertical collector remains selectable for comparison.
These are reference-conditioned synthetic simulator recordings, not human teleoperation. Training eligibility additionally requires a closed gripper and an active lift near the target; passive object flips that trigger the original task reward are excluded. Arm-activity and measured tool-angle metrics are in `comparison.json`, including failed attempts; the two sources are not a paired policy-success comparison.

No model checkpoint scores are reported here. Full training HDF5 files and credentials are not published in this repository.

Quality validation snapshot (2026-10-05): five completed v5 attempts, three qualified successes, one per speed level, with 161/161 critical recorded frames inside the tested head-camera margin. Two tall-object attempts were rejected and retained. This small validation batch does not replace the complete historical v4 pilot.
