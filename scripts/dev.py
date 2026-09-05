#!/usr/bin/env python3
"""Cross-platform dev server launcher for backend + frontend."""

import os
import signal
import subprocess
import sys
from pathlib import Path

def run_dev():
    """Run backend and frontend in parallel with proper cleanup."""
    root_dir = Path(__file__).parent.parent
    backend_dir = root_dir / "backend"
    frontend_dir = root_dir / "frontend"

    print("Starting backend and frontend in parallel...")
    print("Backend: http://localhost:8000")
    print("Frontend: http://localhost:5173")
    print("Press Ctrl+C to stop both servers\n")

    processes = []

    try:
        # Start backend
        backend_cmd = ["uv", "run", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
        backend_proc = subprocess.Popen(backend_cmd, cwd=backend_dir)
        processes.append(backend_proc)

        # Start frontend
        frontend_cmd = ["npm", "run", "dev"]
        frontend_proc = subprocess.Popen(frontend_cmd, cwd=frontend_dir, shell=True)
        processes.append(frontend_proc)

        # Wait for both processes
        for proc in processes:
            proc.wait()

    except KeyboardInterrupt:
        print("\nShutting down servers...")
    finally:
        # Clean up processes
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()

if __name__ == "__main__":
    run_dev()
