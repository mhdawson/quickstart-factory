#!/usr/bin/env python3
"""Produce deterministic baseline-comparison evidence for one fixture case."""
import argparse
import fnmatch
import hashlib
import json
from pathlib import Path


METADATA_FILES = {".gitkeep"}


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def entries(root: Path) -> dict[str, dict[str, str | None]]:
    """Return every non-root tree entry, including empty directories."""
    result: dict[str, dict[str, str | None]] = {}
    for path in root.rglob("*"):
        relative = str(path.relative_to(root))
        if path.is_dir():
            result[relative] = {"kind": "directory", "sha256": None}
        elif path.is_file():
            result[relative] = {"kind": "file", "sha256": digest(path)}
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
    expected_entries = {path: value for path, value in entries(expected).items() if path not in METADATA_FILES}
    actual_entries = entries(actual)
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
