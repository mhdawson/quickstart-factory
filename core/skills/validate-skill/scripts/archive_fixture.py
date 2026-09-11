#!/usr/bin/env python3
"""Archive a completed disposable quickstart for fixture debugging."""
import argparse
import tarfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_name")
    parser.add_argument("case_name")
    parser.add_argument("--output", required=True, help="archive path relative to the repository root")
    args = parser.parse_args()

    root = Path.cwd().resolve()
    expected_case = root / "test" / "skills" / args.skill_name / args.case_name
    if not expected_case.is_dir():
        parser.error(f"case not found: {expected_case}")
    source = root / ".rhoai-qs" / "qs-test-quickstart"
    if not source.is_dir() or source.is_symlink():
        parser.error(f"refusing to archive invalid disposable target: {source}")

    output = (root / args.output).resolve()
    try:
        output.relative_to(root / "test" / "skills" / "reports" / args.skill_name / args.case_name)
    except ValueError:
        parser.error("output must be under the case report directory")
    if output.suffixes[-2:] != [".tar", ".gz"]:
        parser.error("output must end in .tar.gz")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:
        archive.add(source, arcname="qs-test-quickstart", recursive=True)
    print(output.relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
