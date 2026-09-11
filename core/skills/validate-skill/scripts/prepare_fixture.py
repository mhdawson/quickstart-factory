#!/usr/bin/env python3
"""Copy one case's input repository into the fixed disposable quickstart path."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_path", help="case path relative to the repository root")
    args = parser.parse_args()
    root = Path.cwd().resolve()
    case = (root / args.case_path).resolve()
    try:
        case.relative_to(root / "test" / "skills")
    except ValueError:
        parser.error("case_path must be inside test/skills")
    source = case / "input-repo"
    if not source.is_dir():
        parser.error(f"input-repo not found: {source}")
    target = root / ".rhoai-qs" / "qs-test-quickstart"
    if target.is_symlink():
        parser.error("refusing to remove a symlinked disposable target")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            shutil.copytree(item, destination, symlinks=True)
        else:
            shutil.copy2(item, destination, follow_symlinks=False)
    files = [{"path": str(path.relative_to(target)), "sha256": digest(path)} for path in sorted(target.rglob("*")) if path.is_file()]
    print(json.dumps({"case": case.name, "target": str(target), "files": files}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
