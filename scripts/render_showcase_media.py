"""Package an actual Playwright replay recording for repository documentation.

Optional dependency: imageio-ffmpeg. No models or network requests.
Run after scripts/record_showcase.mjs; the source recording remains in ignored output/.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets/showcase"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seconds",
        type=float,
        default=46,
        help="Retain the complete operation; omit trailing recording idle time.",
    )
    args = parser.parse_args()
    source = ROOT / "output/playwright/v08-walkthrough-hd.webm"
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    OUT.mkdir(parents=True, exist_ok=True)

    def run(*params):
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", *params], check=True)

    run(
        "-i",
        str(source),
        "-t",
        str(args.seconds),
        "-an",
        "-c:v",
        "libx264",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(OUT / "walkthrough.mp4"),
    )
    # Excerpts, in original order; keep the actual parsing-review screen in the preview.
    spans = [(1, 3), (9, 11), (14, 16), (20, 22), (26, 28), (32, 34), (40, 42)]
    graph = f"[0:v]split={len(spans)}" + "".join(f"[s{i}]" for i in range(len(spans))) + ";"
    graph += (
        ";".join(
            f"[s{i}]trim=start={a}:end={b},setpts=PTS-STARTPTS[v{i}]"
            for i, (a, b) in enumerate(spans)
        )
        + ";"
    )
    graph += "".join(f"[v{i}]" for i in range(len(spans)))
    graph += f"concat=n={len(spans)}:v=1:a=0,fps=5,scale=864:-1:flags=lanczos,split[p][q];"
    graph += "[p]palettegen=max_colors=96[pal];[q][pal]paletteuse=dither=bayer[out]"
    run(
        "-i",
        str(OUT / "walkthrough.mp4"),
        "-filter_complex",
        graph,
        "-map",
        "[out]",
        "-loop",
        "0",
        str(OUT / "preview.gif"),
    )
    screenshots = [
        "ask-answer",
        "audit-overview",
        "audit-direct",
        "audit-qualifiers",
        "audit-review",
    ]
    for name in screenshots:
        shutil.copyfile(ROOT / f"output/playwright/{name}.png", OUT / f"{name}.png")
    names = ["walkthrough.mp4", "preview.gif", *[n + ".png" for n in screenshots]]
    receipt = {
        "recorded_utc_date": "2026-09-30",
        "mode": "Actual UI operation / saved-inference replay; no new model call",
        "saved_inference_source": "data/demo/conversations/run01/v08-grade-follow-up.json",
        "raw_recording": str(source.relative_to(ROOT)).replace("\\", "/"),
        "raw_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "video": {
            "size": [1440, 1000],
            "fps": 12,
            "retained_seconds": args.seconds,
            "processing": "H.264 transcode, unchanged timing; trim trailing idle only; no audio",
        },
        "gif": {"width": 864, "fps": 5, "excerpts_seconds": spans},
        "screenshots": "Unedited screenshots captured by record_showcase.mjs",
        "outputs": {
            name: {
                "bytes": (OUT / name).stat().st_size,
                "sha256": hashlib.sha256((OUT / name).read_bytes()).hexdigest(),
            }
            for name in names
        },
    }
    (OUT / "media.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf8")
    print(json.dumps({name: (OUT / name).stat().st_size for name in names}))


if __name__ == "__main__":
    main()
