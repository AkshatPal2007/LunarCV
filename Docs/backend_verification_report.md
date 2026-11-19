Historical baseline report. The subsequent integrated implementation and measurements are documented in [production_readiness_report.md](production_readiness_report.md). The statement below that the frontend was unchanged applies only to that earlier verification.

Backend development verification — 20 November 2026

The user accepted an honestly labeled development demo without independent controls. This is a working-tree verification, not a release tag or scientific accuracy benchmark. Frontend code was not changed.

Verified: 37 automated backend/geography tests passed; backend Ruff lint passed; the wheel builds with both console commands and model-asset metadata; wheel Python files match reviewed source; imports work outside the checkout; configuration/API imports avoid Torch; the real spawned API worker completes and serves TIFF/mapping/metrics/manifest artifacts; both fresh and cached native mappings pass the independent artifact audit tool. Dependency deprecation warnings remain. Docker execution was not verified because WSL Docker integration is unavailable.

The actual pair is OHRC ch2_ohr_ncp_20210401T2357376656_d_img_d18 and LRO NAC M1350459544RE. It is development data, with explicit legacy pixel search windows and nominal GSD divisors. The raw LRO label has no geolocation model. No whole-scene geographic accuracy or sub-pixel accuracy is claimed.

| Development experiment | Candidates | Geometric inliers | Fit RMSE in reference pixels | Outcome |
| --- | ---: | ---: | ---: | --- |
| Historical SuperPoint + LightGlue, global | 48 | 6 | 1.030 | REJECT |
| DISK + LightGlue, global | 2 | 0 | unavailable | REJECT |
| ALIKED + LightGlue, global | 111 | 9 | 1.303 | REJECT |
| SIFT-feature LightGlue, global | 20 | 4 | unavailable | REJECT |
| ALIKED ensemble, repeated RIFT2 tiles | 173 | 12 | 1.572 | REJECT |
| Final ALIKED ensemble, bounded fallback | 173 | 12 | 1.572 | REJECT |

All failures remain in ignored local outputs/verification directories. Extractor choices were compared on development imagery; these comparisons are not a held-out generalization benchmark. The historical SuperPoint preset is excluded from the release defaults because of its restrictive license. Increased support does not establish improved independent accuracy: the final fit remains spatially concentrated.

Final selected points: 12. Inlier ratio: 0.0694. Source grid occupancy: 12.50%; source hull coverage: 2.529%. Reference grid occupancy: 18.75%. Successful refinements: 0. Independent accuracy: unavailable. Quality decision: REJECT. All thresholds remained fixed for the comparisons.

Performance measurements on NVIDIA GeForce RTX 4070 Laptop GPU:

| Measurement | Seconds |
| --- | ---: |
| Repeated-secondary experiment | 152.148 |
| Final fresh invocation | 38.992 |
| Final cached invocation | 2.665 |

These are single-run engine timings, excluding interpreter/import startup, on this pair; no p50/p95 throughput claim is made. Empty coarse RIFT2 results disable further secondary tile calls only for that run. Learned matching continues on six geometry-guided tiles. Model weights are reused by the API worker. Final peak process RSS: 3119.07 MiB (process-lifetime scope); peak GPU allocation: 1848.18 MiB; peak GPU reservation: 2534.00 MiB. Timing includes input hashing and artifact writes.

Fresh/cached transform matrices and correspondence CSVs match exactly. API/CLI native transform parity on the real smoke-test pair: True (API uses LightGlue-only; the ensemble secondary produced no matches, so both yielded the same mapping). All fit residuals are recomputed from exported original-image coordinates by lunarcv-inspect, without fitting another transform.

Final algorithm/code/model identity is recorded in each metrics.json; core code SHA-256: d4aea035942377470f266099182a92465d0094cfebbfc4a144447cda9f92b15d. Published artifacts are protected by per-run manifest hashes. The input labels, source geometry and pair manifest are hashed; the current pair's split is development. Unit-test fixtures never enter these results.

The provisional engineering assessment is approximately 60/100 using the original rubric: correctness 18/25, geospatial handling 7/15, scientific validation 5/20, efficiency 12/15, runtime reliability 7/10, reproducibility/testing 8/10, access/integration 3/5. This is an engineering judgment, not an ISRO assessment or an accuracy percentage. The 85/100 target is not achieved.

Remaining work: independent controls and untouched scenes; a genuinely well-distributed real registration; payload-specific IIRS/SELENE/camera adapters; validated TPS if required by real relief cases; stronger operational trials and disk-retention controls; actual Docker execution; project-code license selection; RIFT2 descriptor provenance/license; and mission-image/paper redistribution review. See public_release.md. No public deployment, repository push, GitHub release or model training was performed.

Reproduce from the repository root:

```bash
backend/.venv/bin/python backend/scripts/register_pair.py --force-rematch --output-dir outputs/runs/new-fresh
backend/.venv/bin/python backend/scripts/register_pair.py --output-dir outputs/runs/new-cached
backend/.venv/bin/python backend/scripts/inspect_mapping.py outputs/runs/new-fresh
```

Use unique directories. The installed package also provides lunarcv-register and lunarcv-inspect. A rejected run is evidence about a failure case and must remain labeled as such in a portfolio demonstration.
