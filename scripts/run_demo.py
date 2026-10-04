"""Start live Ask on the three bundled papers, using a separate embedded Qdrant store."""
import argparse
import subprocess
import sys

from local_services import ROOT, demo_environment, launch_services, require_frontend


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-index", action="store_true", help="Reuse an already built demo index")
    args = parser.parse_args()
    npm = require_frontend(8000, 5173)
    env = demo_environment(
        QDRANT_PATH=str(ROOT / ".demo-runtime" / "conversation-qdrant"),
        QDRANT_COLLECTION="medrag_conversation_demo",
        MEDRAG_DATA_DIR=str(ROOT / ".demo-runtime"),
    )
    if not args.skip_index:
        subprocess.run([sys.executable, "scripts/bootstrap_demo.py"], cwd=ROOT, env=env, check=True)
    launch_services(npm, "medrag.api.app:app", 8000, 5173, env)


if __name__ == "__main__":
    main()
