"""Download the pinned official archive and write a deterministic pilot manifest."""
import argparse
import hashlib
import json
import tarfile
import urllib.request
from pathlib import Path

from medrag.verification.scifact import ARCHIVE_SHA256, ARCHIVE_URL, FILES, prepare_pilot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(".benchmark-runtime/scifact"))
    parser.add_argument("--manifest", type=Path,
                        default=Path("data/verification/scifact_pilot/selection.json"))
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    archive = args.cache / "data.tar.gz"
    if not archive.exists():
        request = urllib.request.Request(ARCHIVE_URL, headers={"User-Agent": "VeritasMed-research"})
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != ARCHIVE_SHA256:
            raise ValueError("Upstream archive changed; do not silently adopt new data")
        archive.write_bytes(data)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Cached archive does not match the pinned SHA256")
    with tarfile.open(archive, "r:gz") as tar:
        for name in FILES:
            member = tar.extractfile(f"data/{name}")
            if member is None:
                raise ValueError(f"Missing archive member: {name}")
            data = member.read()
            destination = args.cache / name
            if destination.exists() and destination.read_bytes() != data:
                raise ValueError(f"Modified cached file: {destination}")
            destination.write_bytes(data)
    _, manifest = prepare_pilot(args.cache)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    if args.manifest.exists():
        if json.loads(args.manifest.read_text(encoding="utf-8")) != manifest:
            raise ValueError("Existing manifest differs; select a new output path")
    else:
        args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(args.manifest), "selection": manifest["selection"]}, indent=2))


if __name__ == "__main__":
    main()
