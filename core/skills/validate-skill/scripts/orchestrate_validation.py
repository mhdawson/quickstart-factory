#!/usr/bin/env python3
"""Run the deterministic phases of a validate-skill session.

Model execution remains delegated through the supplied runner and rater command
arrays. This script owns fixture isolation, evidence capture, schema gates, and
report assembly so those handoffs cannot be completed manually or out of order.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

import yaml


PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")
KNOWN_PLACEHOLDERS = {
    "case_path",
    "conversation_json",
    "comparison_json",
    "quickstart_root",
    "rater_output",
    "runner_output",
}


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, indent=2) + "\n")


def reset_report_dir(path: Path) -> None:
    """Start a case with no evidence left over from an earlier run."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def run(command: list[str], root: Path, timeout: int) -> tuple[int, str, str, bool]:
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            command,
            cwd=root,
            env=os.environ.copy(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, stdout, stderr, False
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            remaining_stdout, remaining_stderr = process.communicate()
            stdout = stdout or remaining_stdout
            stderr = stderr or remaining_stderr
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        return 124, stdout, stderr, True


def save_process_log(path: Path, command: list[str], stdout: str, stderr: str, timed_out: bool) -> None:
    lines = ["command:", json.dumps(command), f"timed_out: {str(timed_out).lower()}", "", "stdout:", stdout, "", "stderr:", stderr]
    write_text(path, "\n".join(lines))


def load_mapping(path: Path, label: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"{label} is not valid YAML: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a YAML mapping")
    return value


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not valid JSON: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


def expand(command: list[str], replacements: dict[str, str]) -> list[str]:
    expanded = []
    for argument in command:
        matches = PLACEHOLDER_RE.findall(argument)
        unknown = [name for name in matches if name not in KNOWN_PLACEHOLDERS]
        if unknown:
            raise ValueError(f"unknown command placeholder(s): {', '.join(sorted(set(unknown)))}")
        value = argument
        for name, replacement in replacements.items():
            value = value.replace("{" + name + "}", replacement)
        if PLACEHOLDER_RE.search(value):
            raise ValueError(f"unresolved command placeholder in argument: {argument}")
        expanded.append(value)
    return expanded


def validate_context(root: Path, skill: str, case_path: Path) -> dict[str, Any]:
    expected_root = (root / ".rhoai-qs" / "qs-test-quickstart").resolve()
    fixture_root = (root / "test" / "skills" / skill).resolve()
    valid = (
        expected_root == (root / ".rhoai-qs" / "qs-test-quickstart").resolve()
        and case_path.resolve().is_relative_to(fixture_root)
    )
    result = {
        "resolution": "resolved" if valid else "error",
        "slug": "qs-test-quickstart" if valid else None,
        "confidence": "high",
        "error_message": None if valid else "fixture path is outside the target skill's test directory",
    }
    return result


def write_spec(root: Path, skill: str, case: dict[str, Any], run_at: str, report_dir: Path) -> None:
    spec = {
        "spec_version": 1,
        "skill": "validate-skill",
        "target_skill": skill,
        "quickstart_slug": "qs-test-quickstart",
        "created_at": run_at,
        "test_filter": case["name"],
        "cases": [
            {
                "name": case["name"],
                "input_repo": f"test/skills/{skill}/{case['name']}/input-repo",
                "expected_output_repo": f"test/skills/{skill}/{case['name']}/expected-output-repo",
                "test_config": case["test_config"],
                "run_skill_command": case.get("run_skill_command"),
                "question_answer_context": case.get("question_answer_context"),
                "validation_options": {
                    "mode": case["validation_mode"],
                    "additional_instructions": case.get("additional_validation_instructions"),
                },
                "execution": {
                    "network": case["execution_network"],
                    "external_dependencies": case["external_dependencies"],
                },
                "completion": {
                    "runner_gate": "core/skills/validate-skill/scripts/run_case.py",
                    "status": "completed",
                },
            }
        ],
        "acceptance_criteria": [
            {
                "id": "isolated-fixtures",
                "description": "Each case starts with a fresh qs-test-quickstart copy.",
                "validation": "prepare_fixture.py runs before every case.",
                "requires_user_approval": False,
            },
            {
                "id": "baseline-rating",
                "description": "Every completed case has an evidence-based 1–10 rating.",
                "validation": "The independent rater result is schema-validated.",
                "requires_user_approval": False,
            },
        ],
    }
    write_text(report_dir / "validation-spec.yaml", yaml.safe_dump(spec, sort_keys=False))


def validate_runner_result(result: dict[str, Any]) -> None:
    if result.get("status") != "completed":
        return
    conversation = result.get("conversation")
    if not isinstance(conversation, list) or not conversation:
        raise ValueError("completed runner result must contain a non-empty conversation")
    for message in conversation:
        if not isinstance(message, dict) or message.get("role") not in {"caller", "target-skill"} or not isinstance(message.get("content"), str):
            raise ValueError("runner conversation contains an invalid message")
    if not isinstance(result.get("artifacts", []), list):
        raise ValueError("runner artifacts must be a list")


def validate_rater_result(result: dict[str, Any], case_name: str) -> None:
    if result.get("case") != case_name:
        raise ValueError(f"rater case mismatch: expected {case_name!r}")
    score = result.get("score")
    if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 10:
        raise ValueError("rater score must be an integer from 1 to 10")
    if not isinstance(result.get("summary"), str) or not result["summary"].strip():
        raise ValueError("rater summary must be a non-empty string")
    if not isinstance(result.get("required_artifacts"), list) or not isinstance(result.get("differences", []), list):
        raise ValueError("rater required_artifacts and differences must be lists")


def conversation_from_runner(runner_result: dict[str, Any]) -> list[dict[str, str]]:
    conversation = runner_result.get("conversation")
    return conversation if isinstance(conversation, list) else []


def render_prompt(template: str, replacements: dict[str, str]) -> str:
    rendered = template
    for name, value in replacements.items():
        rendered = rendered.replace("{" + name + "}", value)
    return rendered


def dependency_domains(dependencies: list[str]) -> list[str]:
    domains = []
    for dependency in dependencies:
        hostname = urlparse(dependency).hostname
        if hostname and hostname not in domains:
            domains.append(hostname)
    return domains


def adapter_command(
    root: Path,
    adapter: str,
    skill_name: str | None,
    prompt: str,
    output_path: Path,
    quickstart_root: Path,
    network_profile: str,
    domains: list[str],
) -> list[str]:
    command = [
        sys.executable,
        str(root / "core/skills/validate-skill/runners/launch.py"),
        "--adapter",
        adapter,
    ]
    if skill_name:
        command.extend(["--skill-name", skill_name])
    command.extend(
        [
            "--prompt",
            prompt,
            "--workspace",
            str(quickstart_root),
            "--output",
            str(output_path),
            "--network-profile",
            network_profile,
        ]
    )
    for domain in domains:
        command.extend(["--allowed-domain", domain])
    return command


def render_case_report(root: Path, report_dir: Path) -> None:
    command = [
        sys.executable,
        str(root / "core/skills/validate-skill/scripts/write_report.py"),
        "--input",
        str(report_dir / "validation-results.json"),
        "--output",
        str(report_dir / "validation-report.md"),
    ]
    code, stdout, stderr, timed_out = run(command, root, 60)
    if code != 0 or timed_out:
        raise RuntimeError(f"write_report.py failed: {stderr or stdout}")


def render_conversation(root: Path, report_dir: Path, case_name: str) -> None:
    command = [
        sys.executable,
        str(root / "core/skills/validate-skill/scripts/write_conversation.py"),
        "--input",
        str(report_dir / "validation-results.json"),
        "--case",
        case_name,
        "--output",
        str(report_dir / "skill-conversation.md"),
    ]
    code, stdout, stderr, timed_out = run(command, root, 60)
    if code != 0 or timed_out:
        raise RuntimeError(f"write_conversation.py failed: {stderr or stdout}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_name")
    parser.add_argument("--tests", default=None)
    parser.add_argument("--runner-command-json", help="JSON array command for the case runner")
    parser.add_argument("--rater-command-json", help="JSON array command for the independent rater")
    parser.add_argument("--runner-adapter", choices=("codex", "claude", "cursor", "gemini"))
    parser.add_argument("--runner-prompt-file", type=Path)
    parser.add_argument("--rater-adapter", choices=("codex", "claude", "cursor", "gemini"))
    parser.add_argument("--rater-prompt-file", type=Path)
    parser.add_argument("--network-profile", choices={"isolated", "network"}, default="isolated")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--rater-timeout-seconds", type=int, default=600)
    args = parser.parse_args()

    root = Path.cwd().resolve()
    if bool(args.runner_adapter) == bool(args.runner_command_json):
        parser.error("provide exactly one of --runner-command-json or --runner-adapter")
    if args.runner_adapter and not args.runner_prompt_file:
        parser.error("--runner-adapter requires --runner-prompt-file")
    if bool(args.rater_adapter) == bool(args.rater_command_json):
        parser.error("provide exactly one of --rater-command-json or --rater-adapter")
    if args.rater_adapter and not args.rater_prompt_file:
        parser.error("--rater-adapter requires --rater-prompt-file")

    runner_command = None
    rater_command = None
    try:
        if args.runner_command_json:
            runner_command = json.loads(args.runner_command_json)
        if args.rater_command_json:
            rater_command = json.loads(args.rater_command_json)
    except json.JSONDecodeError as error:
        parser.error(f"runner/rater command must be valid JSON arrays: {error}")
    if runner_command is not None and (not isinstance(runner_command, list) or not all(isinstance(item, str) for item in runner_command)):
        parser.error("runner-command-json must be a JSON array of strings")
    if rater_command is not None and (not isinstance(rater_command, list) or not all(isinstance(item, str) for item in rater_command)):
        parser.error("rater-command-json must be a JSON array of strings")

    discover = [sys.executable, str(root / "core/skills/validate-skill/scripts/discover_cases.py"), args.skill_name]
    if args.tests is not None:
        discover.extend(["--tests", args.tests])
    code, stdout, stderr, timed_out = run(discover, root, 60)
    if code != 0:
        print(stdout, end="")
        print(stderr, file=sys.stderr, end="")
        return code
    try:
        discovered = json.loads(stdout)
    except json.JSONDecodeError as error:
        parser.error(f"discover_cases.py did not return JSON: {error}")
    if discovered.get("errors"):
        print(json.dumps(discovered, indent=2))
        return 1
    network_required = any(case.get("execution_network") == "required" for case in discovered.get("cases", []))
    if network_required and args.network_profile != "network":
        print(
            json.dumps(
                {
                    "errors": [
                        "At least one selected case requires network access; "
                        "run with --network-profile network and provide a network-capable runner command."
                    ]
                },
                indent=2,
            )
        )
        return 1

    run_at = datetime.now(timezone.utc).isoformat()
    context = validate_context(root, args.skill_name, root / "test" / "skills" / args.skill_name)
    if context["resolution"] != "resolved":
        print(json.dumps(context, indent=2))
        return 1

    aggregate_cases: list[dict[str, Any]] = []
    for case in discovered["cases"]:
        case_path = (root / case["path"]).resolve()
        report_dir = root / "test" / "skills" / "reports" / args.skill_name / case["name"]
        reset_report_dir(report_dir)
        write_spec(root, args.skill_name, case, run_at, report_dir)

        prepare = [sys.executable, str(root / "core/skills/validate-skill/scripts/prepare_fixture.py"), case["path"]]
        code, prepare_out, prepare_err, timed_out = run(prepare, root, 60)
        save_process_log(report_dir / "prepare.log", prepare, prepare_out, prepare_err, timed_out)
        if code != 0:
            aggregate_cases.append({"name": case["name"], "status": "failed", "score": None, "summary": "Fixture preparation failed.", "evidence": [], "differences": [], "blocked_or_failure": prepare_err or prepare_out})
            continue

        preflight = [sys.executable, str(root / "core/skills/validate-skill/scripts/preflight_dependencies.py"), case["path"]]
        code, preflight_out, preflight_err, timed_out = run(preflight, root, 60)
        try:
            preflight_json = json.loads(preflight_out)
        except json.JSONDecodeError:
            preflight_json = {"status": "invalid-output", "stdout": preflight_out, "stderr": preflight_err}
        write_json(report_dir / "preflight.json", preflight_json)
        save_process_log(report_dir / "preflight.log", preflight, preflight_out, preflight_err, timed_out)

        runner_output = report_dir / "runner-result.yaml"
        completion_output = report_dir / "completion.json"
        case_replacements = {
            "case_path": str(case_path),
            "quickstart_root": str((root / ".rhoai-qs" / "qs-test-quickstart").resolve()),
            "runner_output": str(runner_output.resolve()),
        }
        if args.runner_adapter:
            runner_prompt = render_prompt(args.runner_prompt_file.read_text(), case_replacements)
            runner_prompt += (
                "\n\nValidation inputs:\n"
                f"target_skill_name={args.skill_name}\n"
                f"target_skill_path={(root / 'core/skills' / args.skill_name).resolve()}\n"
                f"target_prompt={case.get('run_skill_command') or 'none'}\n"
                f"fixture_root={case_path}\n"
                f"quickstart_root={case_replacements['quickstart_root']}\n"
                f"execution_network={case.get('execution_network', 'none')}\n"
                f"external_dependencies={case.get('external_dependencies', [])}\n"
            )
            qa_context = case.get('question_answer_context')
            if qa_context:
                runner_prompt += (
                    "\n\n---\n\n"
                    "## Question-Answer Context (HOLD IN RESERVE)\n\n"
                    "**CRITICAL:** The following context is ONLY for answering questions that the target skill explicitly asks during execution. "
                    "Do NOT provide this information proactively or use it as general background context. "
                    "Wait for the skill to ask a specific question, then check if this context provides a fixture-grounded answer. "
                    "If it does, record the question in the conversation, then provide this answer. "
                    "If the skill asks a question and this context does NOT provide an answer, stop and return blocked.\n\n"
                    f"```\n{qa_context}\n```\n"
                )
            runner_command_for_case = adapter_command(
                root,
                args.runner_adapter,
                args.skill_name,
                runner_prompt,
                runner_output.resolve(),
                (root / ".rhoai-qs" / "qs-test-quickstart").resolve(),
                "network" if case["execution_network"] == "required" else "isolated",
                dependency_domains(case.get("external_dependencies", [])),
            )
        else:
            runner_command_for_case = runner_command
        case_runner = [
            sys.executable,
            str(root / "core/skills/validate-skill/scripts/run_case.py"),
            "--case-path",
            case["path"],
            "--quickstart-root",
            ".rhoai-qs/qs-test-quickstart",
            "--runner-output",
            str(runner_output),
            "--completion-output",
            str(completion_output),
            "--runner-command",
            *runner_command_for_case,
        ]
        code, runner_out, runner_err, timed_out = run(case_runner, root, args.timeout_seconds)
        save_process_log(report_dir / "case-runner.log", case_runner, runner_out, runner_err, timed_out)
        if not completion_output.is_file():
            completion = {"status": "failed", "failure": "case runner produced no completion record", "process_exit": code}
            write_json(completion_output, completion)
        else:
            completion = load_json(completion_output, "completion record")

        try:
            runner_result = load_mapping(runner_output, "runner result") if runner_output.is_file() else {"status": "failed", "failure": completion.get("failure")}
        except ValueError as error:
            runner_result = {"status": "failed", "failure": str(error)}
        write_text(report_dir / "runner-result.yaml", yaml.safe_dump(runner_result, sort_keys=False))
        try:
            validate_runner_result(runner_result)
        except ValueError as error:
            runner_result = {"status": "failed", "failure": str(error), "runner_result": runner_result}

        if completion.get("status") != "completed" or runner_result.get("status") != "completed":
            result = {
                "name": case["name"],
                "status": "failed" if not runner_result.get("blocked_question") else "blocked",
                "score": None,
                "summary": "Target-skill execution did not complete.",
                "evidence": [f"Network profile: {args.network_profile}", f"Preflight status: {preflight_json.get('status', 'unknown')}"],
                "differences": [],
                "blocked_or_failure": runner_result.get("blocked_question") or runner_result.get("failure") or completion.get("failure", "unknown runner failure"),
                "conversation": conversation_from_runner(runner_result),
            }
            write_json(report_dir / "validation-results.json", {"target_skill": args.skill_name, "run_at": run_at, "cases": [result]})
            render_conversation(root, report_dir, case["name"]) if result["conversation"] else None
            render_case_report(root, report_dir)
            aggregate_cases.append(result)
            continue

        conversation = conversation_from_runner(runner_result)
        conversation_path = report_dir / "conversation.json"
        write_json(conversation_path, {"messages": conversation})
        comparison_command = [sys.executable, str(root / "core/skills/validate-skill/scripts/compare_baseline.py"), case["path"]]
        code, comparison_out, comparison_err, timed_out = run(comparison_command, root, 60)
        save_process_log(report_dir / "comparison.log", comparison_command, comparison_out, comparison_err, timed_out)
        try:
            comparison = json.loads(comparison_out)
        except json.JSONDecodeError as error:
            comparison = {"case": case["name"], "differences": [{"kind": "invalid-comparison", "detail": str(error)}], "extra_files": [], "extra_paths": []}
        write_json(report_dir / "comparison.json", comparison)

        replacements = {
            "case_path": str(case_path),
            "conversation_json": str(conversation_path),
            "comparison_json": str(report_dir / "comparison.json"),
            "quickstart_root": str((root / ".rhoai-qs" / "qs-test-quickstart").resolve()),
            "rater_output": str((report_dir / "rater-result.yaml").resolve()),
            "runner_output": str(runner_output.resolve()),
        }
        if args.rater_adapter:
            rater_prompt = render_prompt(args.rater_prompt_file.read_text(), replacements)
            rater_prompt += (
                "\n\nEvaluation inputs:\n"
                f"fixture_contract_path={(root / 'core/skills/validate-skill/references/fixture-contract.md').resolve()}\n"
                f"expected_output_root={(case_path / 'expected-output-repo').resolve()}\n"
                f"actual_quickstart_root={replacements['quickstart_root']}\n"
                f"case_name={case['name']}\n"
                f"comparison_json={replacements['comparison_json']}\n"
                f"conversation={replacements['conversation_json']}\n"
                f"validation_mode={case.get('validation_mode', 'full-baseline')}\n"
                f"additional_validation_instructions={case.get('additional_validation_instructions') or 'null'}\n"
            )
            rater = adapter_command(
                root,
                args.rater_adapter,
                None,
                rater_prompt,
                (report_dir / "rater-result.yaml").resolve(),
                (root / ".rhoai-qs" / "qs-test-quickstart").resolve(),
                "isolated",
                [],
            )
            rater_error = None
        else:
            try:
                rater = expand(rater_command, replacements)
            except ValueError as error:
                rater = []
                rater_error = str(error)
            else:
                rater_error = None

        if rater_error:
            rater_code, rater_out, rater_err, rater_timed_out = 1, "", rater_error, False
        else:
            rater_code, rater_out, rater_err, rater_timed_out = run(rater, root, args.rater_timeout_seconds)
        save_process_log(report_dir / "rater.log", rater or ["invalid-command"], rater_out, rater_err, rater_timed_out)
        rater_path = report_dir / "rater-result.yaml"
        try:
            rater_result = load_mapping(rater_path, "rater result") if rater_path.is_file() else {}
        except ValueError as error:
            rater_result = {"case": case["name"], "error": str(error)}
        try:
            if rater_code != 0 or rater_timed_out:
                raise ValueError(f"rater process failed with exit code {rater_code}")
            validate_rater_result(rater_result, case["name"])
        except ValueError as error:
            result = {
                "name": case["name"],
                "status": "failed",
                "score": None,
                "summary": "Independent output rating failed schema validation.",
                "evidence": ["Target-skill execution completed.", f"Preflight status: {preflight_json.get('status', 'unknown')}"],
                "differences": [],
                "blocked_or_failure": str(error),
                "conversation": conversation,
            }
        else:
            differences = []
            for difference in rater_result.get("differences", []):
                differences.append(f"{difference.get('path', 'unknown')}: {difference.get('detail', difference)}")
            result = {
                "name": case["name"],
                "status": "passed",
                "score": rater_result["score"],
                "summary": rater_result["summary"],
                "evidence": [
                    f"Target command: {case.get('run_skill_command') or 'none'}",
                    f"Network profile: {args.network_profile}",
                    f"Preflight status: {preflight_json.get('status', 'unknown')}",
                    f"Runner tree hash: {completion.get('output_tree_hash', 'unknown')}",
                    "Independent rater result passed schema validation.",
                ],
                "differences": differences,
                "blocked_or_failure": "None.",
                "conversation": conversation,
            }

        write_json(report_dir / "validation-results.json", {"target_skill": args.skill_name, "run_at": run_at, "cases": [result]})
        render_conversation(root, report_dir, case["name"])
        render_case_report(root, report_dir)
        if completion.get("status") == "completed":
            archive_command = [
                sys.executable,
                str(root / "core/skills/validate-skill/scripts/archive_fixture.py"),
                args.skill_name,
                case["name"],
                "--output",
                str(report_dir / "quickstart-output.tar.gz"),
            ]
            archive_code, archive_out, archive_err, archive_timed_out = run(archive_command, root, 60)
            save_process_log(report_dir / "archive.log", archive_command, archive_out, archive_err, archive_timed_out)
            if archive_code != 0:
                result["status"] = "failed"
                result["score"] = None
                result["blocked_or_failure"] = f"archive_fixture.py failed: {archive_err or archive_out}"
                write_json(report_dir / "validation-results.json", {"target_skill": args.skill_name, "run_at": run_at, "cases": [result]})
                render_case_report(root, report_dir)
        aggregate_cases.append(result)

    aggregate = {"target_skill": args.skill_name, "run_at": run_at, "cases": aggregate_cases}
    aggregate_dir = root / "test" / "skills" / "reports" / args.skill_name
    write_json(aggregate_dir / "validation-results.json", aggregate)
    summary_lines = [
        f"# Validation aggregate: {args.skill_name}",
        "",
        f"Run: {run_at}",
        "",
        "| Case | Status | Score | Summary |",
        "|---|---|---:|---|",
    ]
    for result in aggregate_cases:
        score = f"{result['score']}/10" if result.get("score") is not None else "—"
        summary_lines.append(f"| {result['name']} | {result['status']} | {score} | {result.get('summary', '')} |")
    below = [result["name"] for result in aggregate_cases if isinstance(result.get("score"), int) and result["score"] < 8]
    summary_lines.extend(["", f"Cases below 8: {', '.join(below) if below else 'None.'}", ""])
    write_text(aggregate_dir / "validation-report.md", "\n".join(summary_lines))
    print(json.dumps(aggregate, indent=2))
    return 0 if all(result["status"] == "passed" for result in aggregate_cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
