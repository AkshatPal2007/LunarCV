# LunarCV scientific workspace

React 19 + TypeScript + Vite; Node 22.12+ is required. Existing React/Vite was retained. The observatory-style interface uses an evidence inspector as its signature: selecting an actual match exposes native source/reference pixels, residual and confidence without presenting them as independent accuracy.

```bash
npm ci
npm run dev
npm run typecheck
npm run lint
npm run format:check
npm run build
```

`/api/v1` is same-origin. Vite proxies to `http://127.0.0.1:8000`; set `API_PROXY_TARGET` only when the backend is elsewhere. Nginx provides the production proxy. `npm run preview` is a static build preview and does not provide the backend proxy; use the development server or Nginx for integration.

API keys stay in component memory and travel in `X-API-Key`, including authenticated blob downloads. Object URLs and polling requests are cleaned up. No simulated results or fallback metrics are used. Strict TypeScript contracts live in `src/workspace/types.ts`; actual API schemas are available from the backend OpenAPI document.

Browser verification needs running servers and Chromium:

```bash
npx playwright install --with-deps chromium
npm test
LUNARCV_REAL_DATA=1 npm test
```

The first test verifies real backend connection and desktop/mobile layout. The second executes the locally acquired real OHRC/LRO development pair and checks its rejection, match inspection, overlays, checkerboard, and durable history. It is skipped without explicit opt-in; no replacement images are created. Screenshots/traces may contain mission imagery and are ignored, local-only outputs.

The Vite public directory is disabled, and Docker excludes it. Old mission images and logos are not included in built frontend assets. Their existing Git tracking still needs a rights review before source publication. See [all project commands](../COMMANDS.md) and [engineering report](../Docs/production_readiness_report.md).
