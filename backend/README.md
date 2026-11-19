LunarCV backend

The maintained registration entry point is lunarcv.engine.RegistrationEngine. Both the CLI and API use it. The default development preset is ALIKED + LightGlue with a concurrent RIFT2 cross-check, minimal percentile normalization, MAGSAC++ affine filtering, grid selection, conservative paired refinement, and one final affine fit. DISK and SIFT-feature LightGlue are explicit comparison options. No model training is required.

Install and verify:

```bash
cd backend
uv sync --frozen
uv run ruff check .
uv run pytest tests ../tests -q
uv run python scripts/prefetch_models.py
```

Acquire the real OHRC and LRO products listed in ../data/metadata/demo_pair.json from ISSDC/LROC. Preserve the OHRC XML sidecar. Raw imagery and derived mission imagery are not automatically redistributed. The default pair uses explicitly declared legacy search windows and nominal GSD values. Its LRO EDR label has no geolocation grid; no precise geographic reprojection is claimed.

```bash
uv run python scripts/register_pair.py --output-dir ../outputs/runs/development-01
uv run python scripts/inspect_mapping.py ../outputs/runs/development-01
```

Use a new output directory per run. Matches are cached by input content, labels, code, weights and resolved settings. --force-rematch bypasses the safe numeric cache. A failed quality gate is retained. Lower fit residual alone does not establish better accuracy.

For other real image windows:

```bash
uv run python scripts/register_pair.py --source /data/source.tif --reference /data/reference.tif --source-bounds X0 Y0 X1 Y1 --reference-bounds X0 Y0 X1 Y1 --scale-x 1 --scale-y 1 --output-dir /data/run-01
```

Bounds are exclusive x0,y0,x1,y1 in original pixels. For supported north-up rasters with the same declared projected CRS, overlap and GSD are derived automatically when explicit windows are omitted. Raw PDS camera imagery requires explicit windows/geolocation; arbitrary center crops and footprint-to-camera shortcuts are not used. Each window is limited to 32 million pixels by default. Multiband cubes require an explicit verified band adapter; IIRS/SELENE robustness has not been demonstrated by this repository.

Output files include registered.tif with native source radiometry and a validity mask, normalized PNG quicklooks, matches.png, correspondence_points.csv, candidates.npz including rejected candidates, transform.json, metrics.json and manifest.json. transform.json maps original source pixels to original reference pixels and declares how output pixels relate to the reference. A TIFF without reference CRS remains explicitly ungeoreferenced.

Start the single-host API:

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

The API uses SQLite job state and one spawned compute worker. MAX_PENDING_JOBS bounds outstanding work. Cancellation and JOB_TIMEOUT_SECONDS are checked at stage/tile boundaries; they do not preempt an active native-library call. Interrupted jobs become failed on restart and can be rerun using verified caches. Do not increase API workers for this deployment profile.

POST /api/v1/upload returns an immutable file ID. Upload PDS4 XML with POST /api/v1/upload/{file_id}/label. POST /api/v1/register accepts source_image_id, reference_image_id, matcher, features, model, source_bounds, reference_bounds and source_scale_xy. Poll GET /api/v1/jobs/{job_id}; results include science raster, transform, metrics and manifest URLs. DELETE /api/v1/jobs/{job_id} requests cancellation. Execution completion and scientific quality are separate.

GET /api/v1/config/processing reports actual engine defaults. GET /api/v1/health is liveness; GET /api/v1/ready checks job storage and default model assets. Set API_KEY and PUBLIC_MODE=true before exposure; requests then require X-API-Key. The service is a single-operator deployment, not a multi-tenant service. Keep storage behind the API and a configured reverse proxy. CORS settings are a JSON list. Storage directories can be set explicitly by environment variables. Installed-package API storage defaults to ~/.local/share/lunarcv (override LUNARCV_HOME); a source checkout uses its own data/outputs directories. The wheel exposes lunarcv-register and lunarcv-inspect.

Optional real worker verification (uses the local mission products and writes only ignored verification outputs):

```bash
uv run python scripts/verify_api_worker.py
```

See ../Docs/evaluation_protocol.md and ../Docs/public_release.md. Independent control-point accuracy is unavailable. Run scripts/release_check.py before preparing a public source release.
