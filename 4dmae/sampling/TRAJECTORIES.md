# Playable point trajectories

Added `public/trajectories.html`, linked from the sampling page. The viewer replays actual saved simulation states with fixed material-point identities, while separating condition input from query reference. It does not run a model or change training code.

Public URL: https://peiqil.com/dynamic-robot-bench-viewer/4dmae/sampling/trajectories.html

## Display contract

- Four clips: anchor frames 255, 510, 765 and 988 of demonstration 416. Frame 988 was added deliberately because the cube moves visibly; this is a visualization selection, not a performance evaluation.
- Each raw clip contains 160 consecutive states at 20 Hz: 128 states through the anchor (`t0`, index127) plus32 future states. Select16/32/64/128 historical states, corresponding to0.75/1.55/3.15/6.35 seconds between first and last states. Future reference extends1.60 seconds beyond t0.
- Playback controls: play/pause, restart, frame-level slider,0.25×/0.5×/1× speed, loop, history length, future-reference toggle, four clips, five sampling settings and ten seeds.
- Default: frame988, cube holdout, seed0,64 historical states, future reference enabled,0.5× playback.
- Left: blue condition trajectories replay through t0. Query anchors appear at t0. The entire input panel then freezes, including its RGB, tracks and markers.
- Right: withheld query trajectories, including historical and optional future ground truth. These are never labeled as model predictions or inputs.
- Historical RGB is visualization context. The proposed model input remains current RGB, C history and Q anchors, not a historical RGB sequence.
- Points are selected only once at t0, then reconstructed from their fixed body-local coordinates. No per-frame resampling. Changing the seed explicitly chooses another point set.
- Hollow markers indicate approximate occlusion using physical body ID and a depth tolerance of4mm +0.3% depth. Off-screen points remain in the data. Trajectories are simulation ground truth, including through occlusion; this is not visual-tracker accuracy.
- History length controls this preview only; no training config is changed.

## Source and reproduction

`scripts/export_animation.py` restores stored states and renders RGB, camera-space depth, segmentation and body poses. It performs zero physics steps. `scripts/build_animation.py` reuses the existing random/DINO/object samplers, reconstructs UV trajectories, checks current anchor positions, and exports one compact JSON plus an MP4/poster per clip. DINO for frame988 uses the same frozen official checkpoint as the static preview.

Raw geometry is in `raw/animation/` on the rendering host; only the compact derived assets need to be downloaded for the viewer. Some raw geometry is also retained locally. Public assets live in `public/animation/`. The browser uses decoded video frame timestamps to select matching trajectory samples; seeking is quantized to a source frame. Input rendering always uses `min(frame,127)`.

```sh
python scripts/export_animation.py --source <benchmark-data-dir> --output raw/animation
# Make frame-988.npz and frame-988.png available in raw/ for Scene.
python scripts/extract_dino.py --root . --frames 988
python scripts/build_animation.py --root .
python scripts/build_trajectory_video.py --root .
```

The downloadable `animation/trajectory-demo.mp4` is a1280×720 white-background two-panel example of the default setting, containing96 frames at10fps (0.5× source speed). It uses the same material points and freezes the input after t0. Numerical evidence is in `animation/verification.json`; the renderer receipt is `raw/animation/render-verification.json`. Browser and anonymous-publication evidence are in `qa/trajectory-browser-verification.json` and `qa/trajectory-publication.json`.

Rendering used one idle developer GPU; CPU processing and the local video encode do not allocate training nodes. No rollout policy, model inference, training or source-policy change was introduced.
