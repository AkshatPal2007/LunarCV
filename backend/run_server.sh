#!/bin/bash
# Start the FastAPI development server

cd "$(dirname "$0")"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
