"""Start live Ask using a separate embedded Qdrant store."""
import argparse
import subprocess
import sys

from local_services import ROOT, demo_environment, launch_services, require_frontend


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-index", action="store_true", help="Reuse an already initialized demo store")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--medical", action="store_true", help="Use the bundled original GRADE trial abstract")
    mode.add_argument("--conversations", action="store_true", help="Use three original papers for the v0.8 conversation demo")
    args = parser.parse_args()
    npm = require_frontend(8000, 5173)
    store, collection, flags = (
        ("conversation-qdrant", "medrag_conversation_demo", ["--conversations"]) if args.conversations else
        ("medical-qdrant", "medrag_medical_demo", ["--medical"]) if args.medical else
        ("qdrant", "medrag_demo", [])
    )
    env = demo_environment(
        QDRANT_PATH=str(ROOT / ".demo-runtime" / store), QDRANT_COLLECTION=collection,
        MEDRAG_DATA_DIR=str(ROOT / ".demo-runtime"),
        VITE_CONVERSATION_DEMO="1" if args.conversations else "0",
        VITE_MEDICAL_DEMO="1" if args.medical or args.conversations else "0",
    )
    if not args.skip_index:
        subprocess.run([sys.executable, "scripts/bootstrap_demo.py", *flags], cwd=ROOT, env=env, check=True)
    launch_services(npm, "medrag.api.app:app", 8000, 5173, env)


if __name__ == "__main__":
    main()
