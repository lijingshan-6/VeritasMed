"""Generate or verify release-facing historical evaluation reports."""

from __future__ import annotations

import argparse
from pathlib import Path

from medrag.eval.report import load_release, write_or_check


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify outputs without writing")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root with source files")
    parser.add_argument("--summary-output", type=Path, help="JSON output (default: data/eval/release_summary.json)")
    parser.add_argument("--report-output", type=Path, help="Markdown output (default: docs/reports/evaluation_report.md)")
    args = parser.parse_args()
    root = args.root.resolve()
    summary = load_release(root)
    summary_path = args.summary_output or root / "data/eval/release_summary.json"
    report_path = args.report_output or root / "docs/reports/evaluation_report.md"
    try:
        write_or_check(summary, summary_path, report_path, check=args.check)
    except ValueError as exc:
        parser.exit(1, f"{exc}\n")
    action = "verified" if args.check else "generated"
    print(f"Historical evaluation report {action}: {summary_path}, {report_path}")


if __name__ == "__main__":
    main()
