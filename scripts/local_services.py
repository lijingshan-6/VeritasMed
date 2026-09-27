"""Shared lifecycle for the three local demo launchers."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent


def require_frontend(*ports: int) -> str:
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise SystemExit("Install Node.js >=22.12 with npm first.")
    for port in ports:
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                raise SystemExit(f"Port {port} is already in use; stop that local service first.") from None
    return npm


def demo_environment(**overrides: str) -> dict[str, str]:
    # Explicit flags also override stale Vite settings in frontend/.env.local.
    return {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONIOENCODING": "utf-8",
            "PYTHONNOUSERSITE": "1", "VITE_API_URL": "", "VITE_AUDIT_ONLY": "0",
            "VITE_REPLAY_ONLY": "0", "VITE_CONVERSATION_DEMO": "0", "VITE_MEDICAL_DEMO": "0",
            **overrides}


def wait_for_api(process, port: int, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while process.poll() is None and time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError(f"The local API did not start on port {port}; see its output above.")


def launch_services(npm: str, api_app: str, api_port: int, frontend_port: int,
                    env: dict[str, str], page: str = "/") -> None:
    if not (ROOT / "frontend/node_modules").is_dir():
        subprocess.run([npm, "ci"], cwd=ROOT / "frontend", env=env, check=True)
    children = []
    try:
        children.append(subprocess.Popen(
            [sys.executable, "-m", "uvicorn", api_app, "--host", "127.0.0.1", "--port", str(api_port)],
            cwd=ROOT, env=env,
        ))
        wait_for_api(children[0], api_port)
        children.append(subprocess.Popen(
            [npm, "run", "dev", "--", "--port", str(frontend_port)], cwd=ROOT / "frontend", env=env,
        ))
        print(f"VeritasMed: http://127.0.0.1:{frontend_port}{page} — Ctrl+C stops both services.", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(0.5)
        raise SystemExit("A demo service exited; see its output above.")
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
                    child.wait()
