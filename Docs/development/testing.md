Backend verification

Run from backend/:

```bash
uv run --frozen ruff check .
uv run --frozen pytest tests ../tests -q
uv run --frozen python scripts/build_wheel.py
```

backend/tests/test_evaluation_manifest.py checks the declared development split, provenance and diagnostic candidate holdout. test_registration_contracts.py checks pixel-center mappings, final transforms, numeric caches, confidence, matcher agreement/fallback, fractional refinement, raster validity, PDS typing, non-finite rejection and independent-control separation. test_raster_prior.py checks declared-CRS overlap. test_jobs_api.py checks persistent jobs, bounded queues, restart recovery, upload validation, authentication, cancellation requests and API contracts. The legacy top-level geography tests now import the maintained package.

Synthetic arrays and generated small rasters are used only for unit-testing code logic. Their residuals are not lunar evaluation results. Default tests do not download models or claim registration accuracy.

Real-data checks require locally acquired mission imagery and labels:

```bash
uv run python scripts/register_pair.py --output-dir ../outputs/runs/real-fresh --force-rematch
uv run python scripts/register_pair.py --output-dir ../outputs/runs/real-cached
uv run python scripts/inspect_mapping.py ../outputs/runs/real-fresh
uv run python scripts/inspect_mapping.py ../outputs/runs/real-cached
uv run python scripts/verify_api_worker.py
```

Use unique run directories. Inspect all candidates, selected points, native mappings, coverage, failures and stage timings. Verify fresh/cached CSV and transforms match. The API smoke test executes a real job in the spawned worker and retrieves raster/mapping/metrics/manifest endpoints; scientific REJECT is an expected valid result when coverage is inadequate.

Run scripts/release_check.py separately. A nonzero result identifies publication blockers and must not be hidden as a passing check. Additional independent scene/control validation is distinct from software tests. See Docs/evaluation_protocol.md.

Integrated workspace verification (both servers running):

```bash
make frontend-check
make browser-test
make real-browser-test
(cd backend && LUNARCV_REAL_DATA=1 uv run --frozen pytest tests/test_real_scene.py -q)
```

The opt-in real-data regression checks fresh/cache native mapping and CSV identity and independently recomputes exported fit residuals. This artifact consistency audit is not independent geometric truth. Browser tests inspect real job products, keyboard match selection, overlays, checkerboard, mobile layout and durable history. Missing local products are never replaced by fixtures. Browser screenshots/traces are ignored and may contain restricted mission-derived imagery.
