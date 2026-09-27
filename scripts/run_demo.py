"""Start the local showcase using a separate embedded Qdrant store."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

from local_services import wait_for_api

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-index", action="store_true", help="Reuse an already initialized demo store")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--medical", action="store_true", help="Use the bundled original GRADE trial abstract")
    mode.add_argument("--conversations", action="store_true", help="Use three original papers for the v0.8 conversation demo")
    args = parser.parse_args()
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        parser.error("Install Node.js >=22.12 with npm first.")
    for port in (8000, 5173):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                parser.error(f"Port {port} is already in use. Stop the other local server first.")
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(ROOT / "src"),
        "QDRANT_PATH": str(ROOT / (".demo-runtime/conversation-qdrant" if args.conversations else ".demo-runtime/medical-qdrant" if args.medical else ".demo-runtime/qdrant")),
        "QDRANT_COLLECTION": "medrag_conversation_demo" if args.conversations else "medrag_medical_demo" if args.medical else "medrag_demo",
        "MEDRAG_DATA_DIR": str(ROOT / ".demo-runtime"),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONNOUSERSITE": "1",
        # Same-origin Vite proxy; don't inherit another project's .env.local URL.
        "VITE_API_URL": "",
        "VITE_AUDIT_ONLY": "0",
        "VITE_REPLAY_ONLY": "0",
        "VITE_CONVERSATION_DEMO": "1" if args.conversations else "0",
        "VITE_MEDICAL_DEMO": "1" if args.medical or args.conversations else "0",
    })
    if not args.skip_index:
        command = [sys.executable, "scripts/bootstrap_demo.py"] + (["--conversations"] if args.conversations else ["--medical"] if args.medical else [])
        subprocess.run(command, cwd=ROOT, env=env, check=True)
    if not (ROOT / "frontend/node_modules").is_dir():
        subprocess.run([npm, "ci"], cwd=ROOT / "frontend", env=env, check=True)
    children = []
    try:
        children.append(subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "medrag.api.app:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=ROOT, env=env,
        ))
        wait_for_api(children[0], 8000)
        children.append(subprocess.Popen([npm, "run", "dev"], cwd=ROOT / "frontend", env=env))
        print("VeritasMed: http://127.0.0.1:5173 — Ctrl+C stops this demo.", flush=True)
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


if __name__ == "__main__":
    main()
