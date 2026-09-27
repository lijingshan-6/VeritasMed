"""Launch the source-bound audit panel, independently of retrieval or GPU services."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent


def main():
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise SystemExit("Install Node.js >=22.12 with npm first.")
    for port in (8001, 5174):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                raise SystemExit(f"Port {port} is already in use; stop that local service first.") from None
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONIOENCODING": "utf-8",
           "PYTHONNOUSERSITE": "1", "VITE_API_URL": "http://127.0.0.1:8001", "VITE_AUDIT_ONLY": "1", "VITE_REPLAY_ONLY": "0"}
    if not (ROOT / "frontend/node_modules").is_dir():
        subprocess.run([npm, "ci"], cwd=ROOT / "frontend", env=env, check=True)
    children = []
    try:
        children.append(subprocess.Popen([sys.executable, "-m", "uvicorn", "medrag.api.audit_app:app",
                                          "--host", "127.0.0.1", "--port", "8001"], cwd=ROOT, env=env))
        children.append(subprocess.Popen([npm, "run", "dev", "--", "--port", "5174"], cwd=ROOT / "frontend", env=env))
        print("Audit panel: http://127.0.0.1:5174/audit — Ctrl+C stops both services.", flush=True)
        while all(p.poll() is None for p in children):
            time.sleep(.5)
        raise SystemExit("An audit service exited; see its output above.")
    except KeyboardInterrupt:
        pass
    finally:
        for child in reversed(children):
            if child.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"], capture_output=True)
                else:
                    child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()


if __name__ == "__main__":
    main()
