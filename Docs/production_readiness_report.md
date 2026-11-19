# Integrated engineering verification — 20 November 2026

**Outcome: a verified working development application; not production-qualified or independently accurate. Current engineering score: 68/100. The requested 90+ target has not been earned.** No thresholds were weakened, synthetic evaluation products created, model training performed, or restricted assets published.

## Audit scope and baseline

Reviewed the repository structure, maintained CV engine and adapters, API schemas/routes/services, durable jobs, raster/PDS handling, coordinate composition, numeric caching, scientific metrics/control scoring, existing backend/geography tests, React runtime/components/assets, frontend dependency/build configuration, Docker/Compose, Make/dev scripts, documentation, licensing audit and `backend_verification_report.md`. Existing working-tree backend functionality was retained. The earlier report remains the historical baseline.

Before this iteration: 37 tests passed; one real development scene produced 173 candidates, 12 inliers, fit RMSE 1.572110 reference pixels, 12.5% source grid occupancy and REJECT. The previous fresh/cached engine invocations were 38.992/2.665 seconds. The previous engineering assessment was 60/100. These are software/development diagnostics, not independent registration accuracy.

## Root causes and remaining scientific limits

The primary's full-window 111 candidates yield only nine affine inliers. Accepted evidence clusters in a small part of the processing windows. RIFT2 contributes zero cross-sensor candidates on this scene, so it cannot provide independent agreement. Guided tiles add support but do not distribute it across the image. A small fit residual cannot rescue that failure.

The declared prior is a legacy manually localized search window with nominal scale divisors; it is not ground truth. The raw LRO EDR has no geographic model. General orbit/camera reprojection is not implemented. The acquisition metadata also identifies NAC companding, which is a radiometric calibration investigation rather than permission to tune arbitrary image preprocessing. No unvalidated decompanding/calibration was inserted into the default path. The official [LROC data specification, Appendix B](https://pds.lroc.im-ldi.com/data/LRO-L-LROC-5-RDR-V1.0/LROLRC_2001/DOCUMENT/LROCSIS.PDF) documents those transfer functions.

Coarse homography guidance from concentrated matches can extrapolate unreliably. An isolated, reproducible affine-guidance experiment produced 111 candidates, nine inliers, fit RMSE 1.303247, source occupancy 18.75% and hull 2.547%: still REJECT. Its smaller residual is not better accuracy, so it was not promoted. `scripts/diagnose_guidance.py` records the experimental script hash, changes only coarse guidance, and never writes the production cache.

Additional exploratory real-window checks also failed to justify promotion: matching every source tile against the full reference yielded only five affine inliers; quarter-turn hypothesis union yielded seven; optional cached outdoor LoFTR yielded 12 inliers with 25% source occupancy and 18.75% reference occupancy. These exploratory observations are not a new benchmark, default algorithm, independently validated result, or generalization claim. RIFT2 real-image identity returned 265 exact identity matches on a 320-pixel crop, indicating the implementation can self-match; self-match is not cross-sensor validation.

There are no independent controls or untouched scenes. This was explicitly accepted as a development-demo limitation. The existing external-control scorer requires provenance, uncertainty, native coordinates and at least six unused points; it scores after fitting. Its software behavior is tested, but real independent accuracy remains unavailable. No common-crater controls were hand-picked to improve the numbers. No Table 3 superiority claim is justified on this different, unvalidated scene.

## Implemented improvements

- Replaced the active simulated React interface with a strict TypeScript scientific workspace in the existing React/Vite stack. Removed unused mock visualization components and the hardcoded legacy client. No framework migration or new scientific model dependency.
- Integrated actual image availability/uploads/XML labels, bounded crop inputs, registration requests, stage progress, durable job history, cancellation requests, error diagnostics and authenticated products.
- Added native-coordinate visualization, mouse/keyboard correspondence selection, confidence/residual/refinement/agreement inspection, source/reference grids, overlay opacity, checkerboard, registered view, zoom, support hull, transformation matrix, stage timings and evidence exports.
- Replaced unused legacy file-size guessing/implicit center-crop loaders with compatibility adapters to the shared bounded reader; explicit crop origins are regression tested.
- Added formal workspace response schemas and metadata/history/visualization endpoints. Header/window validation rejects bad or oversized requests before queueing. Failed/cancelled jobs can retain available diagnostic metrics. Artifact paths require containment and actual files.
- Removed repeated full-image float conversion in RIFT2 descriptors and replaced 36 per-cell histograms per keypoint with one indexed accumulation. Rounded boundaries, all bin counts and inclusive last edge are preserved exactly. Added equivalence tests.
- Connected cancellation/progress heartbeat to guided tile calls. Kept one compute owner, bounded queue, numeric cache identity, pretrained reuse, deterministic seeds and native mappings.
- Added a geometric support mask with an explicit non-accuracy definition. Fixed frontend object-URL cleanup/credential transitions and mobile history access found during integration testing.
- Applied compatible npm advisory fixes and removed unused animation/Tailwind dependencies. Updated Docker frontend to Node 22 and npm ci; added same-origin routing, security/no-store headers, upload/time limits, loopback API exposure and persistent model cache.
- Added ignore protection for new API results, uploaded products and mission sample pairs; historical tracked files still need rights review.
- Disabled Vite public-directory copying and excluded legacy imagery from the frontend Docker context. Expanded the release checker to include tracked public assets and outputs; existing Git history still requires review.
- Added clean temporary wheel staging plus exact module/source/model-manifest auditing; `make build` uses it. A suspected stale module was confirmed to be current source; no original-wheel mismatch was found. The staged final wheel verifies all 64 Python modules and its model manifest.
- Added reproducible benchmarks, opt-in real-scene regression, frontend CI, safe process cleanup and a non-destructive `make clean`. Created the complete `COMMANDS.md`; replaced stale API/CV/deployment documentation and retained historical reports as such.

## Measured before / after

Hardware: NVIDIA GeForce RTX 4070 Laptop GPU; Linux/WSL2; Python 3.11; Node 22.14. Engine timings exclude interpreter/import startup but include input hashing and artifact export. No concurrent workload/throughput or p95 claim is made from three samples.

| Measurement | Before | After |
| --- | ---: | ---: |
| Fresh engine time | 38.992 s, one previous run | median 21.697 s, three runs |
| Fresh engine samples | — | 22.254 / 21.697 / 21.134 s |
| Process wall samples, including imports | — | 26.778 / 26.147 / 25.705 s |
| Cached engine time | 2.665 s, one run | 2.630 s, one run |
| Initial RIFT2 matcher wall time | 35.619 s, prior diagnostic | 18.250 s, optimized diagnostic |
| Candidates / geometric inliers | 173 / 12 | 173 / 12 |
| Fit RMSE, native reference px | 1.5721102387 | 1.5721102387 |
| Source occupancy / hull | 12.50% / 2.529% | 12.50% / 2.529% |
| Reference occupancy | 18.75% | 18.75% |
| Refinements accepted | 0 | 0 |
| Independent accuracy | unavailable | unavailable |
| Quality decision | REJECT | REJECT |

The new median is approximately 44% below the previous single fresh measurement; this is a local performance observation, not a deployment SLA. A copy-only intermediate run took 40.989 seconds and did not establish a speedup; the histogram optimization produced the substantial measured change. Peak process RSS across the final three fresh runs was 3119–3147 MiB; GPU allocation remained about 1848 MiB. No material memory reduction is claimed.

Pre-/post-optimization native matrices and correspondence CSVs match exactly. Fresh/cache CSVs and matrices also match exactly. The artifact audit recomputes residuals from exported original pixels without refitting. This is independent recomputation of software artifacts, **not independent geometric accuracy validation**.

Local evidence: `outputs/verification/workspace_histogram_fresh`, `workspace_histogram_cached`, `workspace_benchmark_fresh/benchmark.json`, `affine_guidance`, real API job outputs under `data/results`, and ignored browser screenshots/reports. These mission-derived files are not approved public assets. Every run has input/code/config/model identities and artifact hashes.

## Verification executed

- Backend/geography suite: **42 passed, one optional real-data test skipped** in the ordinary run. Ruff passed. Nonfatal upstream deprecation warnings remain.
- Explicit real-data test: **one passed**, executing fresh/cache registration, exact native matrix/CSV agreement and artifact audit on acquired OHRC/LRO products.
- Browser integration: **two passed** against running real backend/frontend. Desktop 1440 px and mobile 390 px, no horizontal overflow or browser page errors; actual real job rejection, keyboard match selection, overlay opacity/support hull, checkerboard and persistent history reopening verified.
- Frontend strict TypeScript, lint with warnings forbidden, formatting and production build passed. npm audit reported **zero known vulnerabilities** at verification time.
- Frontend build approximately 216 kB JavaScript / 68 kB gzip, 16 kB CSS / 4 kB gzip; no copied mission images or remote font dependency. No old-build size comparison is claimed.
- Fresh/cached product hash audits passed. Three isolated fresh benchmark processes all reproduced the same counts, fit residual and quality decision.
- Release checker correctly fails on licensing/rights blockers. Docker execution could not be run because WSL Docker integration is unavailable. YAML parsing/static review is not treated as container verification.

## Engineering score and path to 90+

This is a judgment of engineering readiness, not an ISRO certification or an accuracy percentage. The same category weights as the earlier backend report are retained; the integration category now covers the real scientific workspace.

| Category | Previous | Current | Conditional target |
| --- | ---: | ---: | ---: |
| Correctness / 25 | 18 | 20 | 23 |
| Geospatial handling / 15 | 7 | 7 | 13 |
| Scientific validation / 20 | 5 | 5 | 17 |
| Efficiency / 15 | 12 | 14 | 15 |
| Runtime reliability / 10 | 7 | 8 | 9 |
| Reproducibility/testing / 10 | 8 | 9 | 10 |
| Access/integration / 5 | 3 | 5 | 5 |
| **Total / 100** | **60** | **68** | **92, conditional** |

The conditional target is not an achieved or promised score. Required next milestones:

1. Acquire independently established geographic/camera priors and separately measured controls, with uncertainty and frozen evaluation protocol. Obtain additional untouched overlapping real scenes spanning illumination, scale/viewpoint, polar/equatorial and supported payload differences. Keep development scenes out of reported generalization results.
2. Resolve radiometric/camera normalization using documented mission calibration; compare fixed model-preserving matching improvements on development data. Require genuinely broad correspondence support without shrinking the reported domain or changing gates. Validate on untouched scenes before promotion. Add relief-aware transforms only if independently supported by data.
3. Execute target Docker/GPU and CPU trials, concurrency/resource exhaustion/cancellation/restart/storage tests and reproducible operational benchmarks. Add operator retention and hard watchdog/isolation if the deployment requires them. Expand payload adapters with real IIRS/SELENE data before claiming generic support.
4. Obtain the rights holder's original-code license decision, resolve RIFT2 upstream provenance/license, and review imagery/derived products/paper/legacy assets and Git history. Run the failing release gate again. Build exclusion is not redistribution permission.

No public deployment, repository push, release publication or data-rights decision was performed. The application is suitable for a transparent local portfolio development demonstration; it must not be presented as a validated lunar mapping product.
