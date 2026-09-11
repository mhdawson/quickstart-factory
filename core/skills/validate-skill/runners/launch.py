#!/usr/bin/env python3
"""Launch one foreground agent adapter and capture its final response."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Allow direct execution as ``python runners/launch.py``.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runners import RunnerRequest, adapter_for


def normalize_final_response(value: str) -> str:
    """Remove one Markdown fence around an otherwise machine-readable result."""
    normalized = value.strip()
    lines = normalized.splitlines()
    if len(lines) >= 2 and lines[0].strip().startswith("```") and lines[-1].strip() == "```":
        normalized = "\n".join(lines[1:-1]).strip()
    return normalized + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", choices=("codex", "claude", "cursor", "gemini"), required=True)
    parser.add_argument("--skill-name")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--network-profile", choices=("isolated", "network"), default="isolated")
    parser.add_argument("--allowed-domain", action="append", default=[])
    args = parser.parse_args()

    request = RunnerRequest(
        prompt=args.prompt,
        workspace=args.workspace.resolve(),
        output_path=args.output.resolve(),
        skill_name=args.skill_name,
        network_profile=args.network_profile,
        allowed_domains=tuple(args.allowed_domain),
    )
    spec = adapter_for(args.adapter).build(request)
    environment = os.environ.copy()
    environment.update(spec.environment)
    # Keep Git discovery inside the disposable quickstart boundary.  Without
    # this, a fixture nested under the Factory checkout inherits the Factory's
    # .git metadata and branch list when the target skill runs git commands.
    # Set the ceiling at the parent so a real .git in the quickstart remains
    # usable, while parent repositories are never discovered.
    environment["GIT_CEILING_DIRECTORIES"] = str(request.workspace.parent.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        args.output.unlink()

    completed = subprocess.run(
        list(spec.command),
        cwd=request.workspace,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)
        return completed.returncode

    # Codex writes its final response directly. Claude and Cursor return it on
    # stdout, so capture that response for run_case.py's YAML gate.
    if args.output.is_file():
        args.output.write_text(normalize_final_response(args.output.read_text()))
    else:
        args.output.write_text(normalize_final_response(completed.stdout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
