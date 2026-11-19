#!/usr/bin/env python3
"""Run both dev servers with bounded process-tree cleanup. Use WSL on Windows."""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

def main():
    root=Path(__file__).resolve().parents[1]
    processes=[]
    commands=[(["uv","run","--frozen","uvicorn","app.main:app","--reload","--host","127.0.0.1","--port","8000"],root/"backend"),(["npm.cmd" if os.name=="nt" else "npm","run","dev"],root/"frontend")]
    try:
        for command,cwd in commands:
            if not shutil.which(command[0]):
                raise RuntimeError(f"Required executable missing: {command[0]}")
            options={"creationflags":subprocess.CREATE_NEW_PROCESS_GROUP} if os.name=="nt" else {"start_new_session":True}
            processes.append(subprocess.Popen(command,cwd=cwd,**options))
        print("Frontend: http://localhost:5173 · API: http://localhost:8000/docs",flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.25)
        return next((process.returncode for process in processes if process.returncode),0)
    except KeyboardInterrupt:
        return 0
    finally:
        for process in processes:
            if process.poll() is not None:
                continue
            if os.name=="nt":
                subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],check=False,capture_output=True)
            else:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=8)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL)

if __name__=="__main__":
    raise SystemExit(main())
