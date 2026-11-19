# LunarCV command reference

Commands below run from the **repository root in Linux/WSL** unless another directory is shown. Requirements: Python 3.11+, uv, Node 22.12+, npm. `backend/uv.lock` and `frontend/package-lock.json` are the supported dependency locks. Use locally acquired real mission products for registration; unit fixtures are never demo inputs.

From Windows PowerShell, enter WSL first:

```powershell
wsl.exe -d Ubuntu --cd /home/akshat/Projects/LunarCV
```

## Install and start

```bash
make help                     # List Make targets
make install                  # uv sync --frozen + npm ci
make models                   # Download/verify ALIKED + LightGlue weights
make dev                      # Both servers; Ctrl+C stops their process groups
make dev-backend               # API only, with reload, localhost:8000
make dev-frontend              # Workspace only, localhost:5173
```

Equivalent commands:

```bash
(cd backend && uv sync --frozen)
(cd frontend && npm ci)
backend/.venv/bin/python backend/scripts/prefetch_models.py --features aliked
python3 scripts/dev.py
(cd backend && uv run --frozen uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1)
(cd frontend && npm run dev)
bash backend/run_server.sh
```

`prefetch_models.py --features` accepts `aliked`, `disk`, or `sift`. Model downloads use official pinned assets/checksums. `API_PROXY_TARGET=http://host:8000 npm run dev` (inside frontend/) changes the development proxy. API keys are entered in the workspace header; they stay in memory. Copy `.env.example` to `.env` to configure backend storage and shared-key access. `PUBLIC_MODE=true` requires `API_KEY`.

## Register and inspect

```bash
backend/.venv/bin/lunarcv-register --help
backend/.venv/bin/lunarcv-register --output-dir outputs/runs/development-01
backend/.venv/bin/lunarcv-register --force-rematch --output-dir outputs/runs/development-02
backend/.venv/bin/lunarcv-inspect outputs/runs/development-02
```

Python script equivalents:

```bash
backend/.venv/bin/python backend/scripts/register_pair.py --output-dir outputs/runs/development-03
backend/.venv/bin/python backend/scripts/inspect_mapping.py outputs/runs/development-03
```

Always use **new output directories**. No arguments defaults to the development pair manifest and a timestamped output directory. A completed run can correctly return `quality_decision: REJECT`.

| Registration option | Meaning |
| --- | --- |
| `--pair PATH` | Real product/search-window JSON manifest; default `data/metadata/demo_pair.json` |
| `--source PATH --reference PATH` | Supply both real files explicitly |
| `--source-bounds X0 Y0 X1 Y1` | Exclusive crop in original source pixels |
| `--reference-bounds X0 Y0 X1 Y1` | Exclusive crop in original reference pixels |
| `--scale-x FLOAT --scale-y FLOAT` | Positive source GSD/resampling divisors |
| `--config PATH` | Frozen JSON RegistrationConfig; resolved values recorded in metrics |
| `--matcher ensemble\|lightglue\|rift2` | Matching method |
| `--features aliked\|disk\|sift` | LightGlue feature extractor |
| `--model affine\|similarity\|homography` | Final geometric model |
| `--tile-budget INT` | Bounded guided matching workload; zero disables guided tiles |
| `--no-refine` | Explicit refinement ablation |
| `--force-rematch` | Bypass match-cache reuse |
| `--controls PATH` | Separately acquired native-pixel controls, scored after fitting |
| `--output-dir PATH` | New directory for science/diagnostic products |
| `--help` | Full parser help |

The hidden compatibility flag `--reuse-match-cache` is obsolete; reuse is already the default. It does not override `--force-rematch`.

Explicit real files (replace paths and integer bounds with your actual products/windows):

```bash
backend/.venv/bin/lunarcv-register --source /data/source.tif --reference /data/reference.tif --source-bounds 0 0 1024 1024 --reference-bounds 0 0 1024 1024 --scale-x 1 --scale-y 1 --model affine --output-dir outputs/runs/custom-01
```

The example coordinates illustrate syntax, not a demonstrated overlapping scene. Compatible projected rasters can derive overlap/GSD when windows are omitted. Arbitrary raw camera products need explicit localization; they are not silently mapped from bounding boxes.

## Verify and benchmark

```bash
make lint                     # Backend Ruff + strict frontend lint
make test                     # Backend and top-level geography unit/API tests
make frontend-check           # TypeScript + lint + formatting + production build
make browser-test             # Running real backend/frontend required
make real-browser-test        # Also requires real mission files and model weights
make build                    # Local Python package + frontend build; not publication
make inspect RUN=outputs/runs/development-01
```

Expanded verification:

```bash
(cd backend && uv run --frozen ruff check .)
(cd backend && uv run --frozen pytest tests ../tests -q)
(cd frontend && npm run typecheck && npm run lint && npm run format:check && npm run build)
(cd frontend && npm audit --audit-level=high)
(cd frontend && npx playwright install --with-deps chromium)
(cd frontend && npm test)
(cd frontend && LUNARCV_REAL_DATA=1 npm test)
(cd backend && LUNARCV_REAL_DATA=1 uv run --frozen pytest tests/test_real_scene.py -q)
backend/.venv/bin/python backend/scripts/verify_api_worker.py
```

`--with-deps` installs system browser dependencies and may need administrator privileges. On the verified host, missing Ubuntu libraries were instead extracted into ignored `outputs/browser-runtime/root`; when present, prefix browser commands with `LD_LIBRARY_PATH=$PWD/outputs/browser-runtime/root/usr/lib/x86_64-linux-gnu` from the repository root (use the absolute path from frontend/). This is a host test workaround, not an application dependency.

Repeatable real-data benchmarks use separate interpreter processes and retain logs/products:

```bash
backend/.venv/bin/python backend/scripts/benchmark_pair.py --help
backend/.venv/bin/python backend/scripts/benchmark_pair.py --mode fresh --runs 3 --output-dir outputs/benchmarks/fresh-01
backend/.venv/bin/python backend/scripts/benchmark_pair.py --mode cached --runs 3 --output-dir outputs/benchmarks/cached-01
```

Options: `--pair PATH`, `--output-dir PATH` (new parent directory, required), `--runs 1..10`, `--mode fresh|cached`. Cached mode still reports actual cache hits; an empty cache requires a fresh first run. Summary JSON includes both engine and process wall time. It does not create an accuracy benchmark or hide failed quality gates.

Isolated development ablation (no production-cache writes, unchanged quality thresholds):

```bash
backend/.venv/bin/python backend/scripts/diagnose_guidance.py --guidance-model affine --output-dir outputs/experiments/affine-guidance-01
backend/.venv/bin/python backend/scripts/diagnose_guidance.py --guidance-model homography --output-dir outputs/experiments/homography-guidance-01
```

Options: `--pair PATH`, `--guidance-model affine|homography` (required), `--output-dir PATH` (required). This tests coarse guidance only, using the learned primary; it is not independent validation and does not change the release default.

## Frontend scripts (inside frontend/)

| Command | Purpose |
| --- | --- |
| `npm ci` | Reproduce the committed dependency lock |
| `npm run dev` | Live workspace and backend proxy |
| `npm run typecheck` | Strict TypeScript verification |
| `npm run lint` | Lint, failing on warnings |
| `npm run format` | Format maintained workspace source |
| `npm run format:check` | Check formatting |
| `npm run build` | Type-check and build static assets |
| `npm run preview` | Static preview only; no API proxy |
| `npm test` | Browser tests; backend must run |
| `LUNARCV_REAL_DATA=1 npm test` | Include actual mission registration |
| `npx playwright show-report` | View local test report |
| `npx playwright show-trace PATH` | Inspect a retained local failure trace |
| `npm audit --audit-level=high` | Dependency security advisory check |

## API from the terminal

The workspace normally handles these calls. Default local API:

```bash
curl -s http://localhost:8000/api/v1/health
curl -s http://localhost:8000/api/v1/ready
curl -s http://localhost:8000/api/v1/pairs
curl -s http://localhost:8000/api/v1/images
curl -s http://localhost:8000/api/v1/config/processing
curl -s http://localhost:8000/api/v1/jobs
```

When configured, add `-H "X-API-Key: $LUNARCV_API_KEY"` to API calls; do not put keys in URLs. Replace placeholders below with real returned IDs/files:

```bash
curl -f -F file=@/data/source.img http://localhost:8000/api/v1/upload
curl -f -F file=@/data/source.xml http://localhost:8000/api/v1/upload/FILE_ID/label
curl -f http://localhost:8000/api/v1/images/FILE_ID/metadata
curl -f -H 'Content-Type: application/json' --data-binary @registration-request.json http://localhost:8000/api/v1/register
curl -f http://localhost:8000/api/v1/jobs/JOB_ID
curl -f http://localhost:8000/api/v1/jobs/JOB_ID/results
curl -f http://localhost:8000/api/v1/jobs/JOB_ID/visualization
curl -f -o metrics.json http://localhost:8000/api/v1/files/JOB_ID/metrics.json
curl -f -X DELETE http://localhost:8000/api/v1/jobs/JOB_ID
```

See [API contracts](Docs/api/endpoints.md) for request syntax, all routes, state meanings and error codes. `/config/correspondence-points` and `/config/transform-matrix` are deprecated historical processing-coordinate endpoints, not current native mapping evidence.

## Docker

Docker Desktop WSL integration must be enabled. Container execution was **not verified** on the current host.

```bash
docker compose config --quiet
make docker-build
make docker-up
make docker-logs
make docker-down
docker compose -f docker-compose.dev.yml config --quiet
docker compose -f docker-compose.dev.yml up --build
```

Production compose serves frontend on localhost:5173 and API on loopback:8000, with model cache in a named volume and local data/output mounts. Do not add multiple API workers. An Internet deployment needs configured HTTPS/operator access and cleared asset rights. `docker compose down` preserves data/model volumes; there is deliberately no convenience target that deletes data volumes.

## Release review and cleanup

```bash
make release-check
backend/.venv/bin/python backend/scripts/release_check.py
backend/.venv/bin/python backend/scripts/build_wheel.py --out-dir outputs/artifacts/local-unpublished
make clean
python3 scripts/clean.py
```

The release audit exits **1** while rights/license blockers remain; that is a real failing release gate. A local wheel/build is not approval to publish. `make clean` now removes only named rebuildable build/test/lint caches. It preserves mission data, uploads, results, model cache, match caches, run evidence, node_modules and the Python environment. It is not a retention policy.

The `build_wheel.py` helper accepts `--out-dir PATH` and `--help`. It stages only maintained package source/metadata in a fresh temporary directory, builds without reusing the checkout's old setuptools build tree, and verifies every packaged Python file plus the model manifest. Direct `uv build` remains a tool command; clean staging avoids dependence on the checkout build tree and provides an explicit source-inventory audit. This does not grant publication rights.
