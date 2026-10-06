# Point-history masking inspection

Read-only explanation of the first oracle trajectory pilot. Published at the user's request.

- Reuses the existing three public case windows: samples 1965, 843 and 3321.
- Shows original current RGB, exact original mask rules, model-input availability, and the saved C checkpoint's reconstructed past trajectories.
- Default uses the original fixed supplemental-test mask: epoch 0, seed 12345.
- The seed 7 / epoch 0–3 options demonstrate the training rule on these test windows; they are not historical training occurrences.
- The C model is the original seed 7 checkpoint selected at update 1800. CPU inference only; no optimizer updates or new training.
- Hidden-input neutralization, current-input preservation and original camera projection were checked.
- CPU hidden-history ADE for these fixed-mask windows matches original GPU records within 0.001 mm.
- Publishes three small example windows, their current frames and model predictions inside one self-contained HTML document. Does not publish model weights, full caches or complete raw data.
- Does not modify the first or second round's pages, training, evaluation or the third round's protocol.

Original mask: 12 independent point-level draws with probability 0.5; each chosen point loses all ten negative-time history displacements. The all-hidden case restores one point across the scene. No per-object coverage requirement. Current point geometry and RGB remain available. The C future branch does not consume reconstructed-history outputs.
