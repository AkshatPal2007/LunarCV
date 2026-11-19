LunarCV backend improvement plan

Prepared: 19 November 2026. Scope: Python registration library, CLI, FastAPI, data ingestion, evaluation, backend packaging and deployment. Frontend work is excluded. This document proposes implementation; it does not represent completed changes.

The objective is one reproducible backend that registers real Chandrayaan-2 imagery to real LRO NAC or SELENE imagery, produces distributed correspondences and a registered product, and reports defensible accuracy and resource use. Preserve the architecture and minimal preprocessing required by AGENTS.md.

The current engineering assessment is 30/100. The projected target is 85/100, conditional on the acceptance evidence below. This is an engineering rubric using the user's operational-deployment standard, not an ISRO assessment, certification, measured accuracy percentage, or probability of acceptance. Performance scoring remains provisional because full-scene profiling and load tests have not been completed.

| Dimension | Weight | Current | Target | Evidence needed for target |
| --- | ---: | ---: | ---: | --- |
| Registration correctness and architecture fidelity | 25 | 8 | 22 | Shared engine, correct coordinates, valid fusion, distribution, refinement and transforms |
| Geospatial and sensor/data handling | 15 | 5 | 13 | Metadata-led overlap, real product adapters, masks, reliable output grid |
| Scientific validation and quality decisions | 20 | 3 | 16 | Independent controls, untouched test scenes, failure-inclusive reporting |
| Compute, memory and throughput | 15 | 6 | 12 | Cold/warm stage profiles, bounded RAM/VRAM, representative workload measurements |
| Job reliability and recovery | 10 | 3 | 9 | Persistent state, bounded workers, cancellation, atomic outputs, recovery tests |
| Reproducibility, packaging and automated verification | 10 | 4 | 9 | Locked artifacts, valid cache, installed-package/container tests, real-data regressions |
| Access controls and integration contract | 5 | 1 | 4 | Strict inputs, configured access, auditable artifacts and API contracts |
| Total | 100 | 30 | 85 | All required acceptance checks passed |

A target score is not earned merely by completing code. Missing independent validation, unsupported sensor claims, or uncontrolled resource use prevents the 85/100 assessment. A 100/100 rating would require operational requirements, external review and sustained evidence on the intended deployment workload; this repository cannot establish that today.

The current score reflects confirmed defects: local NumPy shadowing crashes the CLI; cache writing overwrites NPZ with pickle; LightGlue scores are discarded; the geographic crop is hardcoded; the API and CLI run different algorithms; spatial selection is absent from the CLI; sub-pixel refinement loses the fractional reference template center; holdout scoring is disconnected from the final product; and job state is process-local. The saved submission has five final matches, 18.8% grid occupancy, 1.1% hull coverage and zero successful refinements despite an ACCEPT decision. Saved metrics are historical diagnostics, not fresh validation of the present code.

Existing verification: six backend evaluation-helper tests passed; two legacy geography test modules failed collection. Memory-only probes reproduced NumPy scope failure, incompatible cache loading, discarded model confidence, fractional-coordinate refinement bias, a NaN quality-gate acceptance, invalid Compose CORS parsing and incorrect original-shape metadata on the known-size raw-image fallback. Docker execution and full registration were not performed during this review.

The architecture to implement is:

Real files and labels -> metadata and valid-data masks -> geographic overlap and GSD prior -> minimal normalization and multiscale tiles -> concurrent LightGlue and RIFT2 under resource limits -> agreement-aware fusion -> MAGSAC++ -> grid selection -> paired sub-pixel refinement -> final transform fitting -> source warped to reference grid -> independent checks and immutable products.

Use one RegistrationEngine for this sequence. CLI and API are adapters around that engine. Keep the current modules and introduce only the contracts needed to connect them; do not rewrite working algorithms without a demonstrated defect.

Define a RegistrationRequest containing source/reference product references, labels/geometry, validated processing settings and an optional evaluation pair ID. Define RasterProduct with original path, sensor, product ID, native shape/dtype, GSD, available georeferencing/geolocation, nodata and provenance. Define explicit mappings between native, cropped and matcher pixel frames, including pixel-center conventions. Define MatchCandidates with paired coordinates, matcher identity, native confidence and agreement flags; preserve stable match IDs through every stage. Define a result with the transform direction, output grid, selected/refined points, metrics, artifact manifest, warnings and stage timings.

Scientific decisions and execution state must be separate. A job can finish successfully while registration quality is rejected or accuracy remains unvalidated. Do not let COMPLETED imply scientifically acceptable.

1. Stabilize the executable baseline. Estimate: 2-3 engineering days.

Fix the local NumPy import in backend/scripts/register_pair.py. Replace the current cache with an explicit numeric-array schema and JSON metadata; preserve coordinates, confidence and matcher identity. Use atomic writes, schema versions and cache keys incorporating content hashes, labels/geometry hashes, crops, scales, matcher/weight versions and settings. An incompatible cache is a miss, not silently trusted input. Hash immutable products once at ingestion and verify identity before reuse.

Read the actual LightGlue per-match scores and validate score/point lengths. Make extractor resizing explicit so its internal default resize does not undo the configured resolution. Validate matcher choices with an enum and reject unsupported values. Reject non-finite points, transforms and metrics before estimation and before quality acceptance.

Fix CORS parsing, explicit storage-root configuration, production data mounts and package discovery of lunarcv subpackages and app. Install from backend/uv.lock in reproducibility checks. Remove import-time directory creation where practical. Keep synthetic code examples restricted to explicitly labeled unit-test fixtures; no example may produce demonstration/evaluation numbers from random data.

Acceptance: the real baseline CLI completes without relying on an old cache; fresh/cache executions preserve the same candidates and provenance within documented numerical tolerance; malformed inputs and NaNs fail closed; the packaged backend imports from outside the source tree; a clean container starts and finds the configured data and manifest. Include a real CLI smoke test and cache round-trip tests.

2. Create the shared engine and coordinate contract. Estimate: 3-4 engineering days. Depends on step 1.

Move stage orchestration out of the 1,229-line script and registration_service.py into a common engine. Consolidate algorithm defaults from app/config.py, lunarcv/config.py, processing_config.py and inline constants. Keep deployment settings separate from algorithm configuration and dataset manifests. Report resolved settings actually used by each run.

Choose source-native to reference-native mapping as the external contract. Store crop and scaling composition explicitly, rather than relying on names or implicit division. Export the final refined coordinates actually fitted, with point status, confidence, matcher support and residual. Distinguish candidate, MAGSAC inlier, spatially selected and refinement-accepted counts. Represent forward/backward RMSE with their pixel frames and GSD where available.

Define model-specific minimum support and degeneracy checks. Honor requested similarity, affine and homography models consistently. Remove repeated conflicting fits. Reference output dimensions and masks determine the product grid; do not silently truncate an unstable transform into a plausible image. Preserve native radiometry for the registered science product; use normalized copies for matching and quicklooks.

Acceptance: CLI and API invoke the same stage functions with the same resolved settings; identical inputs produce equivalent transforms and metrics. Native/crop/matcher coordinate round trips pass tests, including fractional coordinates. CSV points reproduce the recorded residuals and transform. Dark valid pixels remain valid, and all outputs declare their coordinate frame.

3. Replace manual overlap with real metadata-driven intake. Estimate: 4-6 engineering days for baseline OHRC/NAC support. Other sensor adapters depend on real product access.

Support product bundles containing imagery, XML/PDS labels and geometry, or references to a server-side dataset registry. Configure file limits for actual products and read metadata without full-image decoding. Reject corrupt files at intake. Remove file-size guessing as an implicit claim of sensor compatibility; retain any necessary fallback only with explicit assumptions and warnings.

Fix original-shape tracking before cropping. Preserve raster bit depth through valid-pixel percentile normalization. Correct PDS signedness, endianness and array selection against declared labels. Treat IIRS cubes and SELENE products as explicit adapters with band/array selection, not generic 2D IMG assumptions. Declare unsupported products clearly until verified on real data.

For OHRC, retain the joint scan/pixel geolocation information rather than reducing it to independent longitude/latitude ranges. Use appropriate reference georeferencing/geolocation when available. Bounding-box intersection is a coarse search bound, not an exact raw-camera reprojection. Record prior uncertainty and search margins. Handle longitude conventions, wraparound and polar cases deliberately. Never label an ungeoreferenced raster with an invented CRS.

Replace proportional strip pairing with overlap-derived tile candidates and a coarse-to-fine search. Track tile origins and scales exactly. Freeze dataset splits before tuning; treat the repeatedly tuned baseline as development data and reserve new complete scenes for testing.

Acceptance: a second real overlapping OHRC/NAC scene runs through path/manifest configuration without editing source-code crop constants. Non-overlap and incomplete metadata produce explicit outcomes. Every declared additional sensor pairing passes its own real-product ingestion and overlap checks before being advertised as supported.

4. Complete fusion, coverage and refinement. Estimate: 4-6 engineering days. Depends on steps 2-3.

Run LightGlue and RIFT2 on the same candidate regions, concurrently when the CPU/GPU budget allows. Limit RIFT2 joblib/FFT workers to avoid oversubscription. Record matcher failures and the actual fallback in provenance. Fuse by proximity in both source and reference coordinates, retaining one-to-one support and stable IDs. Preserve raw confidence by matcher; do not treat RIFT2's constant score as calibrated LightGlue confidence.

Apply global MAGSAC++ before spatial selection, as required. Use top-K selection across valid overlap cells, with occupancy, CV and hull coverage reported on a declared domain. Report full-scene coverage separately. Add bounded targeted matching in empty overlap cells instead of lowering acceptance thresholds to accept a cluster. Give this search a fixed attempt/time budget.

Correct paired refinement to preserve fractional template centers. Account for local orientation and scale with the provisional geometry when extracting corresponding neighborhoods. Use correlation/texture reliability, peak ambiguity and bidirectional consistency; retain failed refinements unchanged and record them. Final transform fitting follows refinement. Any post-fit residual validation must be logged, bounded and included in final coverage metrics; it must not become repeated threshold tuning to make the RMSE look good.

Use the simplest adequately supported transform. Validate model complexity on development controls and check local residual structure. TPS remains a conditional, regularized fallback for real high-relief failure cases with enough distributed support and independent evidence; do not use it to interpolate a sparse cluster perfectly.

Acceptance: fusion provenance is inspectable; matcher failure exercises the documented fallback; clustered points cannot pass broad-coverage criteria; fractional identity and transform unit tests catch refinement bias; at least one real pair demonstrates useful refinement or honestly records no gain. Numerical precision alone never triggers a sub-pixel accuracy claim.

5. Make evaluation defensible. Estimate: 4-6 engineering days after suitable real controls are available; data/control acquisition time is additional.

Separate fit residual, held-out matcher consistency and independent registration accuracy. The current raw-candidate affine holdout must not be described as final-product accuracy. Evaluate the actual selected model and pipeline without leakage from scoring controls into fitting, threshold tuning, model selection or refinement settings. Deduplicate/group nearby observations so repeated tile detections do not cross validation partitions.

Use independent metadata reprojection, cross-sensor consistency or crater centroids selected under a predefined protocol; record uncertainty and never choose controls after seeing errors. Keep complete scenes split, with disjoint development and test scenes. Include failed/no-match scenes in success-rate reporting. Aim for 12-20 independent real scene pairs for an initial pilot, spanning the declared sensor scope, illumination, scale, viewpoint and polar/equatorial conditions. This is a planning target, not a claim that this sample establishes universal robustness.

Report candidate count, MAGSAC inliers/ratio, selected count, successful refinement count, fit RMSE, independent RMSE/median/p95, control count/uncertainty, coverage CV/occupancy/hull, stage timings and peak RAM/VRAM. Record a precise unavailability reason instead of inventing unavailable metrics. Compare with the paper only when metric definition, pixel frame and protocol permit comparison; otherwise label its figures as context.

Freeze acceptance thresholds using development evidence before opening the test results. Distinguish geometrically usable, accuracy unvalidated, validated sub-pixel and rejected outcomes. A sub-pixel claim requires independent error below one reference pixel on the declared domain, with control uncertainty and error distribution reported; uncertainty may make that claim inconclusive.

Acceptance: independently recomputing a report from the run manifest and final transform reproduces its measurements; controls remain untouched; rejected and failed cases are included; no unsupported benchmark or accuracy claims remain.

6. Bound resources and harden execution. Estimate: 4-6 engineering days. Instrumentation starts in step 1; optimization follows a correct baseline.

Measure cold-start and warm-run latency by stage using a monotonic timer, GPU synchronization where needed, hardware IDs, RAM and VRAM. Warm models once per worker. Use windowed/memory-mapped input and tiled output; avoid full-scene float copies. Cache validated product metadata and feature extraction for unchanged tiles/settings. Profile before removing per-tile CUDA empty_cache calls, changing precision or raising feature limits; retain numerical regressions when applying such changes.

Use a persistent job store and bounded worker queue. SQLite and one controlled GPU worker are sufficient for the initial single-host deployment; introduce additional infrastructure only when demonstrated throughput requires it. Keep API validation/progress responsive while compute runs out of process. Set CPU/GPU concurrency, native library thread counts, timeouts, cancellation behavior, disk quotas and cleanup policy. Persist terminal failures on restart; resume only verified stages. Write artifacts atomically and publish their manifest last.

Validate product IDs against the registry instead of unconstrained glob patterns. Enforce configured authentication for exposed deployments, per-job ownership where relevant, path containment and byte/dimension limits. Add structured stage logs, liveness/readiness checks and model/storage readiness. Pin model revisions and weight checksums, prefetch artifacts for offline inference and verify code/weight redistribution terms.

Acceptance: declared maximum-size products run within documented memory limits; a second queued job cannot exhaust the GPU; OOM, cancellation, restart and full-disk tests leave honest recoverable state; warmed runs avoid repeated weight loading. Publish p50/p95, throughput, peak resources and failure rates on fixed hardware. Set absolute latency budgets after baseline profiling; do not promise unmeasured speedups.

The registered deliverable for each run is a reference-grid raster with valid-data mask and georeferencing when available; a transform JSON with direction and coordinate composition; CSV/NPZ final correspondences; an evaluation JSON separating fit and independent errors; an immutable provenance manifest with input/model/config hashes; stage timings; and optional real-image quicklooks. The science product must not be only a normalized PNG.

The test strategy has three layers: memory-only unit tests for numerical/contracts logic; real-product integration tests for CLI/API/I/O and artifacts; and frozen real-scene evaluation for scientific claims. Synthetic arrays are allowed only in the first layer. Add CI for these contracts and clean installation/container smoke checks; gate expensive real-data regressions separately without treating their absence as passing validation. Reconcile the legacy test imports and replace documentation of nonexistent test suites with actual test locations.

Delivery should use small reviewable changes: baseline repairs; shared contracts/engine; real-data intake/prior; fusion/distribution/refinement; evaluation; worker/deployment/performance. Fixes that restore correctness should precede changes intended to increase match counts. Preserve old artifacts as historical runs and version new output schemas.

Planning estimate: approximately 6-8 engineering weeks for one experienced backend/CV engineer with periodic geospatial review, assuming real imagery, controls and compute are available. This excludes external acquisition delays and may expand for unsupported sensor formats or camera geometry. A first 8-12 working-day milestone should target a reproducible OHRC/NAC baseline and shared engine, with independent accuracy and full sensor coverage still pending. Do not assign a higher operational score simply because that milestone ships.

The exit decision is evidence based. Re-score using the same rubric after each milestone. The 85/100 target requires validated declared scope, reproducible products, defensible independent checks and measured bounded operation. Institutional integration, larger independent campaigns, operator procedures and sustained operational trials remain the route toward the user's 100/100 standard. New matcher families, domain training, distributed deployment and broad nonrigid warping remain conditional follow-up work after this baseline is measured.


Implementation checkpoint — development demo

Implemented the shared native-coordinate engine and CLI/API adapters, safe content-addressed cache, permissive release extractors, confidence handling, fractional refinement, spatial gates, independent-control scoring without fitting, bounded image loading, same-CRS raster overlap, native-raster/mapping/manifest outputs, SQLite jobs and isolated bounded worker, cancellation at stage/tile boundaries, explicit configuration, model prefetch and mapping audit tools, tests and CI. Real preset comparisons retain rejected results. RIFT2's empty coarse result now disables repeated secondary tile attempts only for that run.

Not completed or claimed: independent accuracy, a second untouched scene, full IIRS/SELENE camera/cube adapters, raw LRO camera reprojection, TPS validation, institutional operational acceptance, and publication rights review. Docker engine execution depends on an available Docker environment. Public deployment/release has not been performed. The user explicitly accepted an honestly labeled development demo while independent controls are unavailable.
