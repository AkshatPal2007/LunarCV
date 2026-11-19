LunarCV evaluation protocol — development-v2

The available OHRC/LRO scene is development data because it has been used repeatedly to implement and compare presets. Historical priority-0-v1 outputs remain historical; reclassification does not create a new test set.

The shared engine fits only matcher-derived candidates. It applies geometric rejection, spatial selection, paired refinement and one final selected model. It exports the exact refined native coordinates used for that fit. No repeated residual-threshold sweep is used to select a flattering final subset.

Fit RMSE, median and p95 are diagnostics in native reference pixels. The legacy evaluate_homography_holdout helper measures held-out raw candidate consistency; production quality does not treat it as independent accuracy. Independent accuracy remains unavailable until external controls are supplied. The engine never automatically claims sub-pixel accuracy.

External controls are supplied through --controls controls.json. The JSON must declare coordinate_frame=native_pixels, independent_of_matching=true, method, provenance, uncertainty_reference_px, and at least six points with source:[x,y] and reference:[x,y]. Controls are scored only after fitting; near-duplicates of fit locations are refused. Declaring independence is a provenance assertion that requires review, not a guarantee provided by the JSON format.

Freeze complete-scene development/test splits and thresholds before evaluating new scenes. Group nearby duplicate observations before splitting. Select controls using a predefined method independent of final errors, and report uncertainty. Include failed/no-match scenes. Do not compare fit residuals or raw-candidate holdout with the paper's accuracy numbers as equivalent measurements.

The current geometric thresholds are provisional engineering guards: at least 12 selected matches, at least 50% grid occupancy and 20% convex hull coverage in both entire processing windows, CV no greater than 1.5, and fit RMSE no greater than 2 native reference pixels. These thresholds are versioned in RegistrationConfig. They are not validated scientific acceptance criteria. Empty and non-overlap cells are not silently excluded to improve coverage.

Every completed run records native transform direction, crop and scale matrices including pixel-center offsets, complete original shapes, input/label/model/code/config identities, all candidates and their geometric status, selected/refined points, independent-check availability, stage timings and resource measurements. manifest.json publishes hashes of completed artifacts. Use backend/scripts/inspect_mapping.py to verify hashes and recompute residuals without fitting.

A REJECT outcome is preserved as a valid experiment result. GEOMETRICALLY_USABLE_ACCURACY_UNVALIDATED indicates only that provisional geometry checks passed; it is not a registration-accuracy certificate.
