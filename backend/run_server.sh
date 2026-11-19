#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
exec uv run --frozen uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
