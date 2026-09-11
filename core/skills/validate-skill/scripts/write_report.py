#!/usr/bin/env python3
"""Render a consistent Markdown validation report from agent-produced JSON results."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="JSON file with target_skill and case results")
    parser.add_argument("--output", required=True, help="Markdown report path")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text())
    rows = []
    sections = []
    for result in data["cases"]:
        score = f"{result['score']}/10" if result.get("score") is not None else "—"
        rows.append(f"| {result['name']} | {result['status']} | {score} | {result.get('summary', '')} |")
        sections.extend([
            f"## {result['name']}",
            "",
            "### Evidence",
            "",
            *([f"- {item}" for item in result.get("evidence", [])] or ["- None recorded."]),
            "",
            "### Differences",
            "",
            *([f"- {item}" for item in result.get("differences", [])] or ["- None."]),
            "",
            "### Blocked questions or failures",
            "",
            result.get("blocked_or_failure", "None."),
            "",
        ])
    lines = [
        f"# Validation report: {data['target_skill']}",
        "",
        f"Run: {data.get('run_at', datetime.now(timezone.utc).isoformat())}",
        "Quickstart fixture path: `.rhoai-qs/qs-test-quickstart/`",
        "",
        "| Case | Status | Score | Summary |",
        "|---|---|---:|---|",
        *rows,
        "",
        *sections,
    ]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
