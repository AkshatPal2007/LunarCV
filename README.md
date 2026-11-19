# LunarCV

A scientific workspace for registering real Chandrayaan-2 imagery against LRO NAC / SELENE imagery, with inspectable original-pixel correspondences and transparent quality gates.

**Status: working development application; not a validated mapping service.** The current OHRC/LRO development scene fails spatial-coverage gates. Independent geometric accuracy is unavailable. No sub-pixel, ISRO deployment, or general cross-payload accuracy claim is made.

## Run locally

Use Linux/WSL, Python 3.11+, [uv](https://docs.astral.sh/uv/), and Node.js 22.12+ (tested: 22.14). From the repository root:

```bash
make install
make models
make dev
```

Open [the workspace](http://localhost:5173) and [API documentation](http://localhost:8000/docs). The frontend proxies `/api` to the backend; no browser API URL editing is needed. Two terminals also work: `make dev-backend` and `make dev-frontend`.

Acquire the real products and OHRC XML label listed in [demo_pair.json](data/metadata/demo_pair.json) from [ISSDC](https://chmapbrowse.issdc.gov.in/) and [LROC](https://wms.lroc.asu.edu/lroc/search). Files and model weights are not included in the frontend build. Select the available development scene, then **Run registration**. Uploads and explicit search windows are also supported. Large raw products require bounded overlap crops; nothing is silently center-cropped.

**[COMMANDS.md](COMMANDS.md) lists installation, development, every CLI flag, API calls, tests, benchmarks, Docker, and release checks.**

## What the workspace does

- Uses actual backend job progress, persistent SQLite history, cancellation requests, and failure diagnostics.
- Shows real source/reference matches, overlays with opacity control, checkerboard, registered products, and spatial-support hulls.
- Selects correspondences by mouse or keyboard to inspect native source/reference pixels, primary model confidence, refinement, secondary agreement, and fit residuals.
- Displays coverage grids, stage timings, transformation matrices, quality reasons, and independent validation status. Model confidence and the support hull are explicitly **not accuracy estimates**.
- Downloads science TIFF, correspondence CSV, all candidates, transform, metrics, masks, and artifact hashes. A rejected warp remains a diagnostic product.
- Supports shared API-key authentication without putting keys in URLs or persistent browser storage. Deployment is a **single-operator, single-host** profile, not a multi-tenant service.

## One registration engine

```text
Real imagery + labels
  → explicit / georeferenced overlap and GSD prior
  → minimal percentile normalization
  → pretrained ALIKED + LightGlue and complementary RIFT2
  → agreement ranking and coarse geometric guided tiles
  → MAGSAC++ → grid selection → conservative paired refinement
  → final transform → native raster + mapping + measured diagnostics
```

Affine is the default. Homography is optional. Similarity uses OpenCV RANSAC for its robust partial-affine estimator; affine/homography use MAGSAC++. TPS, general lunar camera-model reprojection, IIRS/SELENE validation, learned uncertainty calibration, and domain fine-tuning are **not implemented/validated release capabilities**.

The CLI and spawned API compute worker share `backend/lunarcv/engine.py`. Original-pixel mappings include crop origins, actual resize factors, and pixel-center conventions; they are exported in `transform.json`. Numeric match caches are bound to input, configuration, code, and pinned model hashes. The worker reuses pretrained models. RIFT2's empty coarse result disables repeated secondary calls only within that run; it never invents matches.

## Verified development results

Real pair: OHRC `ch2_ohr_ncp_20210401T2357376656_d_img_d18` / LRO NAC `M1350459544RE`. These are development search windows, not independently georeferenced truth.

| Diagnostic | Verified result |
| --- | ---: |
| Candidates / geometric inliers | 173 / 12 |
| Fit RMSE, native reference pixels | 1.572110 |
| Source grid occupancy / hull | 12.50% / 2.529% |
| Reference grid occupancy | 18.75% |
| Accepted local refinements | 0 |
| Independent accuracy | Unavailable |
| Quality decision | **REJECT** |
| Previous fresh engine invocation | 38.992 s (one run) |
| Optimized fresh engine median | 21.697 s (3 runs; 21.134–22.254 s) |
| Cached engine invocation | 2.630 s (one run) |

Timings are on an RTX 4070 Laptop GPU and exclude interpreter/import startup; they include hashing, matching and exports. The three fresh process wall times were 25.705–26.778 s. Optimized and original correspondence CSVs and native matrices agree exactly. RIFT2 histogram accumulation was optimized without changing bin counts. Lower fit residuals on alternative match subsets were **not** treated as evidence of better accuracy.

Verification: 42 ordinary backend/geography tests, an opt-in real-scene fresh/cache regression, strict frontend TypeScript/lint/build checks, and two real-backend desktop/mobile browser tests. Read [the current engineering report](Docs/production_readiness_report.md) for evidence, limitations and scoring; [the earlier backend report](Docs/backend_verification_report.md) is retained as a historical baseline.

## Verification and reproducibility

```bash
make lint
make test
make frontend-check
# With both servers running:
make browser-test
make real-browser-test
# CLI outputs must use new directories:
backend/.venv/bin/lunarcv-register --output-dir outputs/runs/development-01
backend/.venv/bin/lunarcv-inspect outputs/runs/development-01
```

Independent controls, when acquired separately from matching, can be scored **after fitting** with `--controls`. The software requires provenance, measurement uncertainty, native coordinates and at least six unused controls. No controls are manufactured for this demo. See [evaluation protocol](Docs/evaluation_protocol.md).

## Deployment and public release

Docker configurations use Node 22, same-origin Nginx routing, bounded uploads, persistent storage/model cache, and one compute worker. **Docker execution remains unverified on this host because Docker Desktop WSL integration is unavailable.** See [deployment notes](Docs/deployment/docker.md).

Before exposing the API, set `PUBLIC_MODE=true` and a strong `API_KEY`, configure HTTPS at your deployment boundary, and retain the one-worker profile. Keys are shared operator access, not user isolation. Cancellation/time budgets are checked at stage boundaries; a running native call is not forcibly preempted. Automatic disk retention is not implemented.

Run `make release-check` before publishing. Project-code license selection, bundled RIFT2 descriptor provenance/license, and redistribution review of already tracked mission-derived assets and the reference paper remain blockers. The frontend build excludes the legacy `public` imagery directory, but that does **not** remove assets already in Git history. No restricted assets, screenshots, repository release, or public deployment have been published by this work. Read [release gates and primary licensing sources](Docs/public_release.md).

The evidence-based current engineering assessment is **68/100**, up from the previous backend assessment of 60/100. The 90+ target remains blocked by real scientific validation, distributed matching success, broader payload coverage, operational deployment trials, and release rights—not by presentation quality.
