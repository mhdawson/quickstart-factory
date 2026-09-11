#!/usr/bin/env python3
"""Check declared Git repositories before a validation case needs them."""
import argparse
import json
import subprocess
from pathlib import Path

import yaml


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_path")
    args = parser.parse_args()

    config_path = Path(args.case_path) / "test-config.yaml"
    config = yaml.safe_load(config_path.read_text()) or {}
    execution = config.get("execution", {})
    network = execution.get("network", "none")
    dependencies = execution.get("external-dependencies", [])
    if network != "required" or not dependencies:
        print(json.dumps({"network": network, "dependencies": [], "status": "not-required"}, indent=2))
        return 0

    results = []
    for dependency in dependencies:
        try:
            completed = subprocess.run(
                ["git", "ls-remote", dependency, "HEAD"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            reachable = completed.returncode == 0
            result = {"dependency": dependency, "status": "reachable" if reachable else "unreachable"}
            if not reachable:
                result["error"] = (completed.stderr or "git ls-remote failed").strip().splitlines()[-1]
        except (OSError, subprocess.TimeoutExpired) as error:
            result = {"dependency": dependency, "status": "unreachable", "error": str(error)}
        results.append(result)

    status = "reachable" if all(result["status"] == "reachable" for result in results) else "unreachable"
    print(json.dumps({"network": network, "dependencies": results, "status": status}, indent=2))
    return 0 if status == "reachable" else 1


if __name__ == "__main__":
    raise SystemExit(main())
