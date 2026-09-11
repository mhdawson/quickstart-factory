#!/usr/bin/env python3
"""Validate and enumerate fixture cases for a Factory skill."""
import json
import sys
from pathlib import Path

import yaml


def parse_test_filter(value: str | None) -> tuple[list[str] | None, list[str]]:
    """Parse a comma-separated case list and return validation errors."""
    if value is None:
        return None, []
    names = [name.strip() for name in value.split(",")]
    errors = []
    if not all(names):
        errors.append("--tests must be a comma-separated list of non-empty test names")
    if len(names) != len(set(names)):
        errors.append("--tests must not name a test more than once")
    return names, errors


def load_test_config(path: Path) -> tuple[dict[str, object] | None, list[str]]:
    """Load the test control file and validate the fields the runner consumes."""
    try:
        config = yaml.safe_load(path.read_text())
    except yaml.YAMLError as error:
        return None, [f"invalid test-config.yaml: {error}"]
    if not isinstance(config, dict):
        return None, ["test-config.yaml must contain a YAML mapping"]

    errors = []
    command = config.get("run-skill-command")
    if command is not None and (not isinstance(command, str) or not command.strip()):
        errors.append("run-skill-command must be a non-empty string when provided")
    context = config.get("question-answer-context")
    if context is not None and (not isinstance(context, str) or not context.strip()):
        errors.append("question-answer-context must be a non-empty string when provided")
    validation_options = config.get("validation-options", {})
    if not isinstance(validation_options, dict):
        return None, ["validation-options must be a YAML mapping when provided"]
    validation_instructions = validation_options.get("additional-instructions")
    if validation_instructions is not None and (not isinstance(validation_instructions, str) or not validation_instructions.strip()):
        errors.append("validation-options.additional-instructions must be a non-empty string when provided")
    validation_mode = validation_options.get("mode", "full-baseline")
    if validation_mode not in {"full-baseline", "targeted"}:
        errors.append("validation-options.mode must be full-baseline or targeted")
    if validation_mode == "targeted" and validation_instructions is None:
        errors.append("targeted validation-options.mode requires additional-instructions")
    execution = config.get("execution", {})
    if not isinstance(execution, dict):
        errors.append("execution must be a YAML mapping when provided")
        execution = {}
    network = execution.get("network", "none")
    if network not in {"none", "required"}:
        errors.append("execution.network must be none or required")
    external_dependencies = execution.get("external-dependencies", [])
    if not isinstance(external_dependencies, list) or any(
        not isinstance(dependency, str) or not dependency.strip()
        for dependency in external_dependencies
    ):
        errors.append("execution.external-dependencies must be a list of non-empty strings")
        external_dependencies = []
    if external_dependencies and network != "required":
        errors.append("execution.external-dependencies requires execution.network: required")
    if errors:
        return None, errors
    return {
        "run_skill_command": command.strip() if command is not None else None,
        "question_answer_context": context.strip() if context is not None else None,
        "additional_validation_instructions": validation_instructions.strip() if validation_instructions is not None else None,
        "validation_mode": validation_mode,
        "execution_network": network,
        "external_dependencies": [dependency.strip() for dependency in external_dependencies],
    }, []


def main() -> int:
    arguments = sys.argv[1:]
    if not arguments or len(arguments) > 3:
        print("usage: discover_cases.py <skill-name> [--tests test-one,test-two]", file=sys.stderr)
        return 2
    skill_name = arguments[0]
    test_filter = None
    if len(arguments) == 3 and arguments[1] == "--tests":
        test_filter = arguments[2]
    elif len(arguments) != 1:
        print("usage: discover_cases.py <skill-name> [--tests test-one,test-two]", file=sys.stderr)
        return 2

    root = Path.cwd().resolve()
    target_skill = root / "core" / "skills" / skill_name
    cases_root = root / "test" / "skills" / skill_name
    requested_cases, errors = parse_test_filter(test_filter)
    if not (target_skill / "SKILL.md").is_file():
        errors.append(f"target skill not found: {target_skill / 'SKILL.md'}")
    if not cases_root.is_dir():
        errors.append(f"case directory not found: {cases_root}")
    cases = []
    if cases_root.is_dir():
        available_cases = {
            case.name: case
            for case in cases_root.iterdir()
            if case.is_dir() and not case.name.startswith(".") and case.name != "reports"
        }
        if requested_cases is None:
            selected_cases = sorted(available_cases)
        else:
            selected_cases = sorted(set(requested_cases))
            unknown = sorted(set(selected_cases) - set(available_cases))
            if unknown:
                errors.append(f"requested case(s) not found: {', '.join(unknown)}")

        for case_name in selected_cases:
            case = available_cases.get(case_name)
            if case is None:
                continue
            config_path = case / "test-config.yaml"
            missing = [name for name in ("input-repo", "expected-output-repo", "test-config.yaml") if not (case / name).exists()]
            if not missing and not any((case / "input-repo").iterdir()):
                missing.append("input-repo contents")
            config = None
            if not missing:
                config, config_errors = load_test_config(config_path)
                missing.extend(config_errors)
            if not missing and config["validation_mode"] == "full-baseline" and not any(path.name != ".gitkeep" for path in (case / "expected-output-repo").iterdir()):
                missing.append("approved expected-output-repo contents")
            if missing:
                errors.append(f"{case.name}: missing {', '.join(missing)}")
            else:
                cases.append({
                    "name": case.name,
                    "path": str(case.relative_to(root)),
                    "test_config": str(config_path.relative_to(root)),
                    **config,
                })
    print(json.dumps({"target_skill": str(target_skill), "cases": cases, "errors": errors}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
