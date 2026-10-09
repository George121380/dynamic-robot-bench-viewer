# Benchmark task GIF gallery

**All 26 catalog entries and 16 native PhysMani tasks have GIFs, 42 total.** The [anonymous online page](https://peiqil.com/dynamic-robot-bench-viewer/benchmark-tasks/) supports Chinese/English, task search, priority/source/depth filters and pause. [中文说明](README.zh.md). This subtree adds visualizations and preserves existing site pages.

Sources include existing project conveyor/puck experts, finger diagnostics and PhysMani experts, plus official/author media from ManiSkill, RoboCasa, robomimic, PerAct, Kubric, Physion, CLEVRER, CoPhy and Farama. Cards retain original links; [sources.json](sources.json) records provenance, revisions, attribution, source hashes, camera crops, playback factors and frame checks for all 42 GIFs. PhysMani retains upstream-code CC BY-NC-SA 4.0 attribution.

**TurnFaucet-v1 alone uses a legacy official TurnFaucet-v0 motion reference, explicitly labeled v0; it does not establish acceptance of the v1 environment or data.** PerAct images are external author policy examples; PhysMani images are accepted scripted-expert demonstrations. None establishes project learned-model scores.

GIFs are lossy previews with width at most 384, 8 fps and 128 colors, totaling approximately 36.9 MiB. Sources longer than 20 seconds are sped up with labeled factors. RoboCasa uses the left external camera from three-view concatenated videos. PhysMani uses front views with an original 0.05-second interval; preview transfer used JPEG quality 85. These assets support task selection, not training or physical metrics. Lazy loading and JPEG posters support pause and reduced-motion preferences.

All 42 files passed multi-frame, distinct-pixel, duration, looping and SHA-256 checks. Browser checks verified language switching, the five P0 entries, search, pause and a 390-pixel narrow viewport. Tools and complete bilingual task/data documentation are on the private implementation repository's `task/benchmark-task-docs` branch, unmerged into main; task implementation status is unchanged.

All 42 GIFs are followed by depth labels: stored original/project depth, state rendering, new RGB-D collection, estimation/reconstruction for existing RGB, or unresolved availability. They describe the selected data version; GIFs still show RGB only. Rendering requires version, camera and frame-alignment checks. [depth_labels.json](depth_labels.json) contains bilingual summaries without internal data paths.

Depth filters apply to the 26 catalog entries; all 16 native PhysMani tasks remain below. Counts are 11 stored, 14 renderable, four new-collection, two estimation/reconstruction, two partial and one version-unconfirmed; conditions overlap. Notes distinguish public ManiSkill states from project diagnostics, and retain selected PerAct archive, CoPhy subdataset, Adroit full-state and TurnFaucet-v1 limitations beside the respective GIFs. The original 42 GIFs/posters are unchanged.
