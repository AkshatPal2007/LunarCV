# API contracts

Base path `/api/v1`; interactive schema: `/docs`, JSON schema: `/api/v1/openapi.json`. When configured, send `X-API-Key` on all endpoints except health/root (including downloads). Never put keys in query strings.

| Method/path | Purpose |
| --- | --- |
| GET `/health` | Process liveness; not scientific validity |
| GET `/ready` | Storage/model availability; can return 503 |
| GET `/images` | Real raw/uploaded product IDs and sizes |
| GET `/images/{id}/metadata` | Header dimensions/dtype; does not decode whole product |
| GET `/pairs` | Actual local development-scene availability and declared search request |
| POST `/upload` | Stream image multipart field `file`, max 2 GiB |
| POST `/upload/{id}/label` | PDS4 XML for uploaded IMG, max 2 MiB; immutable once attached |
| POST `/register` | Validate products/windows, queue job; 400/404/409/422/429/503 on failure |
| GET `/jobs?limit=30` | Durable recent history, max 100; no absolute source paths |
| GET `/jobs/{id}` | Actual state/progress/message |
| DELETE `/jobs/{id}` | Request cancellation at stage boundary; 409 if terminal |
| GET `/jobs/{id}/results` | Terminal metrics/error/artifact URLs |
| GET `/jobs/{id}/visualization` | Terminal native-coordinate points, frames and available artifacts; 409 before terminal |
| GET `/files/{id}/{filename}` | Contained artifact file retrieval |
| GET `/config/processing` | Actual default processing configuration |
| GET `/config/correspondence-points` | Deprecated historical processing-coordinate showcase, not current evidence |
| GET `/config/transform-matrix` | Deprecated historical showcase transform, not current evidence |

`POST /register` body:

```json
{"source_image_id":"uploaded-or-raw-id","reference_image_id":"other-id","matcher":"ensemble","features":"aliked","model":"affine","source_bounds":[0,0,1024,1024],"reference_bounds":[0,0,1024,1024],"source_scale_xy":[1,1]}
```

Those numbers illustrate the API syntax, not evaluation imagery or a demonstrated overlap. Bounds are exclusive native XY integers, inside product dimensions, at most 32 million pixels per window. Scale divisors must be positive finite values. Matcher: ensemble/lightglue/rift2; features: aliked/disk/sift; transform: affine/similarity/homography. No silent crop or quality-threshold override is exposed.

States: pending → processing → completed/failed/cancelled. `completed` can contain `quality_decision: REJECT`. Never infer success from HTTP 200 or completion alone. Progress reports stage boundaries, not estimated completion time.

Visualization points use original zero-based pixel centers (x column, y row), preserving CSV precision. The matrix maps original source→original reference pixels; quicklooks need processing-frame conversion. `confidence` is a model/ranking score, not a calibrated accuracy probability. Missing independent controls yield `status: unavailable` and null independent RMSE.

The UI uses authenticated blobs for images and downloads. Examples for all endpoints and cancellation are in [COMMANDS.md](../../COMMANDS.md). Deploy one API worker for the single-host SQLite/GPU ownership model.
