#!/usr/bin/env python3
"""Render a caller-to-skill conversation retained in validation results."""
import argparse
import json
from pathlib import Path


def fenced(value: str) -> list[str]:
    marker = "```"
    while marker in value:
        marker += "`"
    return [f"{marker}text", value, marker]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="validation-results.json path")
    parser.add_argument("--case", required=True, help="case name in the results")
    parser.add_argument("--output", required=True, help="Markdown transcript path")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text())
    result = next((item for item in data.get("cases", []) if item.get("name") == args.case), None)
    if result is None:
        parser.error(f"case not found in results: {args.case}")
    messages = result.get("conversation")
    if not isinstance(messages, list) or not messages:
        parser.error("case conversation must be a non-empty list")

    lines = [f"# Skill conversation: {data['target_skill']} / {args.case}", ""]
    for message in messages:
        role = message.get("role") if isinstance(message, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if role not in {"caller", "target-skill"} or not isinstance(content, str):
            parser.error("each conversation item needs role caller|target-skill and string content")
        heading = "Caller" if role == "caller" else "Target skill"
        lines.extend([f"## {heading}", "", *fenced(content), ""])

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
