#!/usr/bin/env python3
"""Fetch shared repositories used by fixture expected-output baselines."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import yaml


def run_git(arguments: list[str], cwd: Path | None = None) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "git command failed").strip()
        raise RuntimeError(detail)
    return completed.stdout.strip()


def normalized_repository(value: str) -> str:
    return value.removesuffix(".git").rstrip("/")


def load_dependencies(case_config: Path) -> list[dict[str, str]]:
    config = yaml.safe_load(case_config.read_text()) or {}
    dependencies = config.get("baseline-dependencies", [])
    if not isinstance(dependencies, list):
        raise ValueError(f"{case_config}: baseline-dependencies must be a list")
    result = []
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            raise ValueError(f"{case_config}: baseline dependency must be a mapping")
        name = dependency.get("name")
        repository = dependency.get("repository")
        ref = dependency.get("ref", "main")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise ValueError(f"{case_config}: invalid baseline dependency name")
        if not isinstance(repository, str) or not repository.strip():
            raise ValueError(f"{case_config}: baseline dependency {name} has no repository")
        if not isinstance(ref, str) or not ref.strip():
            raise ValueError(f"{case_config}: baseline dependency {name} has no ref")
        result.append({"name": name, "repository": repository.strip(), "ref": ref.strip()})
    return result


def sync_dependency(cache: Path, dependency: dict[str, str]) -> dict[str, str]:
    repository = dependency["repository"]
    ref = dependency["ref"]
    if cache.is_symlink():
        raise RuntimeError(f"refusing to use a symlink as dependency cache: {cache}")

    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=f".{cache.name}-", dir=cache.parent) as temporary:
            checkout = Path(temporary) / "checkout"
            run_git(["clone", "--depth", "1", "--branch", ref, repository, str(checkout)])
            os.replace(checkout, cache)
    else:
        if not cache.is_dir() or not (cache / ".git").exists():
            raise RuntimeError(f"dependency cache exists but is not a git checkout: {cache}")
        origin = run_git(["remote", "get-url", "origin"], cwd=cache)
        if normalized_repository(origin) != normalized_repository(repository):
            raise RuntimeError(f"dependency cache origin mismatch at {cache}: {origin}")
        run_git(["fetch", "--depth", "1", "origin", ref], cwd=cache)
        run_git(["reset", "--hard", "FETCH_HEAD"], cwd=cache)

    checkout_root = Path(run_git(["rev-parse", "--show-toplevel"], cwd=cache)).resolve()
    if checkout_root != cache.resolve():
        raise RuntimeError(f"dependency checkout resolved outside its cache path: {checkout_root}")
    action_path = cache / ".github" / "actions"
    if not action_path.is_dir():
        raise RuntimeError(f"shared action directory not found: {action_path}")
    return {
        **dependency,
        "cache_path": str(cache),
        "commit": run_git(["rev-parse", "HEAD"], cwd=cache),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_name")
    parser.add_argument("case_names", nargs="*", help="selected fixture case names")
    args = parser.parse_args()

    root = Path.cwd().resolve()
    skill_root = root / "test" / "skills" / args.skill_name
    if not skill_root.is_dir():
        parser.error(f"fixture skill directory not found: {skill_root}")
    cases_root = skill_root
    case_names = sorted(args.case_names) if args.case_names else sorted(
        path.name for path in cases_root.iterdir() if path.is_dir() and path.name != ".shared-dependencies" and path.name != "reports"
    )

    dependencies_by_name: dict[str, dict[str, str]] = {}
    for case_name in case_names:
        config_path = skill_root / case_name / "test-config.yaml"
        if not config_path.is_file():
            parser.error(f"test config not found for selected case {case_name}: {config_path}")
        for dependency in load_dependencies(config_path):
            previous = dependencies_by_name.get(dependency["name"])
            if previous and previous != dependency:
                parser.error(f"baseline dependency {dependency['name']} has conflicting declarations")
            dependencies_by_name[dependency["name"]] = dependency

    synced = []
    try:
        for name, dependency in sorted(dependencies_by_name.items()):
            parsed = urlparse(dependency["repository"])
            if parsed.scheme not in {"https", "ssh"} or not parsed.netloc:
                raise ValueError(f"baseline dependency {name} must use an HTTPS or SSH repository URL")
            cache = skill_root / ".shared-dependencies" / name
            synced.append(sync_dependency(cache, dependency))
    except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as error:
        print(json.dumps({"status": "unavailable", "dependencies": synced, "error": str(error)}, indent=2))
        return 1

    print(json.dumps({"status": "synced" if synced else "not-required", "dependencies": synced}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
