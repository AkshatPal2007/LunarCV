Backend configuration

Algorithm settings are defined and validated by backend/lunarcv/settings.py:RegistrationConfig. The CLI accepts a JSON configuration with --config and explicit matcher/features/model overrides; the API accepts its declared request fields. Every run stores resolved configuration. GET /api/v1/config/processing reports actual defaults.

Deployment settings are in backend/app/config.py. Environment variables override the checkout root .env and current-directory .env files. Start with the root .env.example. CORS origins must be a JSON list, not comma-separated text.

Storage overrides: RAW_DIR, UPLOAD_DIR, RESULTS_DIR, CACHE_DIR, JOB_DB_PATH and EVALUATION_MANIFEST_PATH. Source checkouts use their own data/outputs paths; installed packages default API storage under ~/.local/share/lunarcv, overridden by LUNARCV_HOME. Native input paths and crop bounds are never inferred from upload size.

MAX_UPLOAD_SIZE defaults to 2 GiB. Each processing window defaults to at most 32 million pixels. MAX_PENDING_JOBS defaults to four outstanding jobs; one spawned compute worker owns the GPU. JOB_TIMEOUT_SECONDS defaults to 600 and cancellation/timeouts are checked at stage/tile boundaries. They do not preempt a running native call. Run this deployment profile with one API worker.

Set API_KEY and PUBLIC_MODE=true before public exposure; send X-API-Key with requests. Docker Compose passes both values to the container. This is a single-operator deployment. The integrated frontend sends keys in headers, including artifact requests; multi-tenant ownership is not implemented.

CLEANUP_AFTER_HOURS is reserved legacy configuration. Automatic deletion is not implemented or promised; preserve experimental artifacts and explicitly manage local storage. The current make clean target removes only named rebuildable build/test/lint caches and preserves mission data, runs and environments; it is not retention management.

Use scripts/prefetch_models.py to download and verify the official pinned model assets before offline use. CPU/GPU inference speed is hardware dependent. OMP_NUM_THREADS=2 and OPENBLAS_NUM_THREADS=2 are used in the verified single-host examples. RIFT2 is limited to two descriptor threads and bounded image dimensions.

See backend/README.md for current CLI/API commands and Docs/public_release.md for release gates. Docker execution remains unverified in the current WSL environment because Docker integration is unavailable.
