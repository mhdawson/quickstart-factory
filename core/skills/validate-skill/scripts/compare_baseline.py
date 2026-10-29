#!/usr/bin/env python3
"""Produce deterministic baseline-comparison evidence for one fixture case."""
import argparse
import fnmatch
import hashlib
import json
import os
import re
from pathlib import Path

import yaml


METADATA_FILES = {".gitkeep"}


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_within(path: Path, roots: list[Path]) -> bool:
    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def entries(root: Path, allowed_external_roots: list[Path] | None = None) -> dict[str, dict[str, str | None]]:
    """Return every tree entry, expanding links only to declared baseline dependencies."""
    root = root.resolve()
    allowed_roots = [path.resolve() for path in (allowed_external_roots or [])]
    result: dict[str, dict[str, str | None]] = {}

    def visit(directory: Path, relative_directory: Path, ancestors: frozenset[Path]) -> None:
        resolved_directory = directory.resolve(strict=True)
        if resolved_directory in ancestors:
            raise ValueError(f"directory symlink cycle detected at {directory}")
        next_ancestors = ancestors | {resolved_directory}
        with os.scandir(directory) as children:
            for child in sorted(children, key=lambda item: item.name):
                path = Path(child.path)
                relative = relative_directory / child.name
                key = relative.as_posix()
                if child.is_symlink():
                    target = path.resolve(strict=True)
                    if target.is_dir():
                        if is_within(target, [root, *allowed_roots]):
                            result[key] = {"kind": "directory", "sha256": None}
                            visit(path, relative, next_ancestors)
                        else:
                            result[key] = {"kind": "symlink", "sha256": None}
                    elif target.is_file():
                        if is_within(target, [root, *allowed_roots]):
                            result[key] = {"kind": "file", "sha256": digest(path)}
                        else:
                            result[key] = {"kind": "symlink", "sha256": None}
                    else:
                        result[key] = {"kind": "symlink", "sha256": None}
                elif child.is_dir(follow_symlinks=False):
                    result[key] = {"kind": "directory", "sha256": None}
                    visit(path, relative, next_ancestors)
                elif child.is_file(follow_symlinks=False):
                    result[key] = {"kind": "file", "sha256": digest(path)}

    visit(root, Path(), frozenset())
    return result


def matches_ignore(path: str, patterns: set[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_path", help="case path relative to the repository root")
    args = parser.parse_args()
    root = Path.cwd().resolve()
    case = (root / args.case_path).resolve()
    expected = case / "expected-output-repo"
    actual = root / ".rhoai-qs" / "qs-test-quickstart"
    if not expected.is_dir() or not actual.is_dir():
        parser.error("expected-output-repo and .rhoai-qs/qs-test-quickstart must exist")
    ignore_file = case / "comparison-ignore"
    ignored = {line.strip() for line in ignore_file.read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")} if ignore_file.is_file() else set()
    config = yaml.safe_load((case / "test-config.yaml").read_text()) or {}
    baseline_dependencies = config.get("baseline-dependencies", [])
    if not isinstance(baseline_dependencies, list):
        parser.error("test-config.yaml baseline-dependencies must be a list")
    allowed_external_roots = []
    for dependency in baseline_dependencies:
        if (
            not isinstance(dependency, dict)
            or not isinstance(dependency.get("name"), str)
            or not re.fullmatch(r"[A-Za-z0-9_-]+", dependency["name"])
        ):
            parser.error("test-config.yaml contains an invalid baseline dependency")
        dependency_root = root / "test" / "skills" / case.parent.name / ".shared-dependencies" / dependency["name"]
        if dependency_root.is_symlink():
            parser.error(f"baseline dependency cache must not be a symlink: {dependency_root}")
        allowed_external_roots.append(dependency_root)
    try:
        expected_entries = {path: value for path, value in entries(expected, allowed_external_roots).items() if path not in METADATA_FILES}
        actual_entries = entries(actual)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(f"could not enumerate baseline or output tree: {error}")
    required_status = []
    for path in sorted(expected_entries):
        if matches_ignore(path, ignored):
            continue
        expected_kind = expected_entries[path]["kind"]
        actual = actual_entries.get(path)
        status = "missing" if actual is None else "present" if actual["kind"] == expected_kind else "differs"
        required_status.append({"path": path, "status": status})

    differences = []
    for path, expected_entry in sorted(expected_entries.items()):
        if matches_ignore(path, ignored):
            continue
        actual_entry = actual_entries.get(path)
        if actual_entry is None:
            difference = {"path": path, "kind": "missing", "expected_type": expected_entry["kind"]}
            if expected_entry["kind"] == "file":
                difference["expected_sha256"] = expected_entry["sha256"]
            differences.append(difference)
        elif actual_entry["kind"] != expected_entry["kind"]:
            differences.append({"path": path, "kind": "type_mismatch", "expected_type": expected_entry["kind"], "actual_type": actual_entry["kind"]})
        elif expected_entry["kind"] == "file" and actual_entry["sha256"] != expected_entry["sha256"]:
            differences.append({"path": path, "kind": "content_differs", "expected_sha256": expected_entry["sha256"], "actual_sha256": actual_entry["sha256"]})

    extras = sorted(path for path, entry in actual_entries.items() if entry["kind"] == "file" and path not in expected_entries and not matches_ignore(path, ignored))
    extra_paths = sorted(path for path in actual_entries if path not in expected_entries and not matches_ignore(path, ignored))
    actual_files = sorted(path for path, entry in actual_entries.items() if entry["kind"] == "file")
    print(json.dumps({"case": case.name, "required_paths": required_status, "differences": differences, "extra_files": extras, "extra_paths": extra_paths, "actual_files": actual_files, "actual_paths": sorted(actual_entries)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
