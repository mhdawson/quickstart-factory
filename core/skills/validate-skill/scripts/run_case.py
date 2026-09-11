#!/usr/bin/env python3
"""Run one validation case and publish a post-run output manifest."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import yaml


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def output_manifest(root: Path) -> tuple[list[dict[str, str | None]], str]:
    entries: list[dict[str, str | None]] = []
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if path.is_dir():
            entries.append({"path": relative, "kind": "directory", "sha256": None})
        elif path.is_file():
            entries.append({"path": relative, "kind": "file", "sha256": digest(path)})
    encoded = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return entries, hashlib.sha256(encoded).hexdigest()


def atomic_write(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=f".{path.name}.", delete=False) as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        temporary = Path(stream.name)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-path", required=True)
    parser.add_argument("--quickstart-root", required=True)
    parser.add_argument("--runner-output", required=True, help="Runner result file, written by the runner command")
    parser.add_argument("--completion-output", required=True, help="Validator-owned completion record")
    parser.add_argument("--runner-command", nargs=argparse.REMAINDER, required=True)
    args = parser.parse_args()

    repository = Path.cwd().resolve()
    quickstart = Path(args.quickstart_root).resolve()
    expected_root = repository / ".rhoai-qs" / "qs-test-quickstart"
    if quickstart != expected_root:
        parser.error("quickstart-root must be .rhoai-qs/qs-test-quickstart")
    if not quickstart.is_dir():
        parser.error(f"quickstart root not found: {quickstart}")
    if not args.runner_command:
        parser.error("runner-command must not be empty")

    replacements = {
        "{runner_output}": str(Path(args.runner_output).resolve()),
        "{quickstart_root}": str(quickstart),
        "{case_path}": str((repository / args.case_path).resolve()),
    }
    command = [
        argument.replace("{runner_output}", replacements["{runner_output}"])
        .replace("{quickstart_root}", replacements["{quickstart_root}"])
        .replace("{case_path}", replacements["{case_path}"])
        for argument in args.runner_command
    ]
    unresolved = [argument for argument in command if re.search(r"\{[a-z_]+\}", argument)]
    if unresolved:
        parser.error(f"unresolved runner-command placeholder(s): {', '.join(unresolved)}")
    process = subprocess.run(command, cwd=repository, env=os.environ.copy(), check=False)
    result_path = Path(args.runner_output).resolve()
    result: dict[str, object] | None = None
    if result_path.is_file():
        try:
            loaded = yaml.safe_load(result_path.read_text())
            if isinstance(loaded, dict):
                result = loaded
        except yaml.YAMLError:
            result = None

    status = result.get("status") if result else None
    if process.returncode != 0 or status != "completed":
        failure = {
            "status": "failed",
            "process_exit": process.returncode,
            "runner_status": status,
            "runner_result": result,
            "failure": "runner did not complete successfully",
        }
        atomic_write(Path(args.completion_output).resolve(), failure)
        print(json.dumps(failure, indent=2))
        return 1

    entries, tree_hash = output_manifest(quickstart)
    completion = {
        "status": "completed",
        "process_exit": process.returncode,
        "runner_status": status,
        "output_tree_hash": f"sha256:{tree_hash}",
        "output_manifest": entries,
    }
    atomic_write(Path(args.completion_output).resolve(), completion)
    print(json.dumps(completion, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
