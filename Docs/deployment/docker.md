# Docker deployment profile

The supplied configuration is a single-host, single-operator deployment with one API process and one spawned compute worker. Docker execution remains **unverified** on the development host: Docker Desktop WSL integration is unavailable. Static YAML/configuration review is not an executed container test.

```bash
cp .env.example .env
docker compose config --quiet
docker compose build
docker compose up -d
docker compose logs -f
docker compose down
```

Frontend: http://localhost:5173; API loopback: http://localhost:8000. Nginx proxies `/api` to the backend, accepts bounded 2-GiB uploads, sends no-store/security headers and supports blob image loading. Frontend builds with Node 22 and npm ci; no mission `public` directory is copied into the build. Backend uses Python 3.11 and the frozen uv lock. First model acquisition needs network access; prefetch pinned weights before offline operation.

`./data` and `./outputs` retain inputs, jobs/results and match cache. `model-cache` retains pretrained weights. A raw-data volume must also contain the metadata pair manifest and OHRC XML label. Missing files produce an unavailable scene, not a replacement dataset. Do not delete data/model volumes to resolve a scientific failure.

Before external exposure set `PUBLIC_MODE=true`, set a strong shared `API_KEY`, configure HTTPS at the reverse-proxy boundary, and verify the real target environment. There is no multi-tenant ownership model or automatic disk retention. Cancellation/time limits check stage boundaries; a native matcher call is not forcibly interrupted. Use exactly one API worker.

Development compose:

```bash
docker compose -f docker-compose.dev.yml config --quiet
docker compose -f docker-compose.dev.yml up --build
```

The development proxy uses `API_PROXY_TARGET=http://backend:8000`. Runtime `VITE_API_URL` does not configure a compiled frontend and is no longer used.

Publication remains blocked by original-code licensing, bundled RIFT2 descriptor provenance/license, and imagery/paper redistribution rights. Existing Git assets/history need review even though static frontend output excludes them. See [release gates](../public_release.md), [current verification](../production_readiness_report.md), and [all commands](../../COMMANDS.md).
