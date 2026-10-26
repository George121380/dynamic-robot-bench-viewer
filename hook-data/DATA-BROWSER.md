# Hook formal-data browser

The home page now opens the actual dataset player; the prior acceptance page is preserved as `acceptance.html`. All250 admitted episodes are available:200train/50validation. Development clips, rejected failures and test data are outside this browser.

Filter by split, tool and direction; watch the original recording with a synchronized top-down geometry view, scrub frames, and jump to grasp/contact/end. Playback initially starts1.5s before first contact; the start button shows the complete episode. Tool thumbnails use the first matching case, preferring distinct directions rather than scoring outcomes.

Videos are the original128×128/20Hz files, individually SHA-verified against the formal manifest. Enlargement adds no detail. The top-down view reconstructs rigid poses from the128 saved persistent surface points and known geometry. It is visualization only, uses world XY in metres, omits the robot, and neither resimulates nor modifies training data.

The training-window inspector calls the frozen production observation_window/targets functions at the first contact state, clipped to the final pre-action frame if needed. It shows current RGB,18-dimensional state,8observed points×16history frames,40×7actions,16query anchors and15past/15future label steps. Future labels are hidden by default and never actor inputs. Points are simulator oracle tool/cube surfaces, not the later4D-MAE full-scene sidecar.

`data-browser-v1/manifest.json` binds source/export SHA values, timing and rigid-fit error. Each series.f32 frame has49little-endian float32 columns: toolR9+t3,cubeR9+t3,state18,action7. The terminal action row is only padding: videos/state haveT+1frames, training RGB/action haveT. Window PNGs are lossless; gallery/three-frame strips are JPEG previews.

`export_data_browser.py` reads the frozen Baidu release with four CPU threads. No GPU allocation, training or source/data mutation. Open https://peiqil.com/dynamic-robot-bench-viewer/hook-data/ .
