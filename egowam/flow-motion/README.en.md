# Moving-camera 3D flow: interactive geometry illustration

Completed three synthetic scenarios comparing uncompensated, ideal-compensated and erroneous-compensated flow. The visualization does not run human videos, Track4World extraction or the deployed prediction head, and establishes no empirical model or label accuracy.

`moving-camera-flow.html` is the editable fragment. `index.html` is the self-contained page with styles and local state persistence. Public URL: https://peiqil.com/dynamic-robot-bench-viewer/egowam/flow-motion/ . Scenario selection, scrubbing and finite three-second playback use local geometry only.

An object moving 8 cm right while the camera moves 10 cm right has an uncompensated lateral displacement of −20 mm and an ideally compensated displacement of +80 mm. Assuming a shared 20% point-coordinate scale error while applying metric camera translation gives a 20 mm static-background residual and +76 mm estimated object displacement. For a stationary point initially 0.7 m away and a 15-degree camera rotation, the uncompensated displacement is about 182.7 mm. Ideal compensation removes it. A hypothetical extra 1-degree relative rotation error leaves about 12.2 mm. These assumptions are not measured Aria or Track4World errors.

Plots show the x–z slice of 3D geometry with zero y motion. All panels use the same source points and equal coordinate scales. Flow arrows are magnified threefold; numeric values are not magnified. The erroneous-scale panel anchors estimated displacement vectors at the common reference points rather than treating normalized point coordinates as metric absolute positions.

Chrome verification covered the default state, rotation, 0% and 50% scrubbing, playback start and natural completion. A 320 px layout has no horizontal overflow and labels remain above 11 px. Wide layouts compare panels side by side; narrow layouts stack them. Motion respects reduced-motion and never loops automatically. JavaScript syntax checks passed. Empirical validation still requires unfiltered static residual distributions and independent dynamic 3D ground truth.
