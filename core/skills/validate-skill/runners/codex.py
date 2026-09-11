"""Codex CLI adapter for validate-skill."""

from __future__ import annotations

from .contract import RunnerRequest, RunnerSpec


_RAW_YAML_REMINDER = (
    "\n\nCRITICAL OUTPUT CONTRACT: return ONLY the complete YAML object requested by the prompt. "
    "Do not use Markdown fences and do not add prose before or after the YAML. "
    "Quote scalar values that contain a colon followed by a space, a hash, braces, or newlines; "
    "use a YAML block scalar for long or multi-line text.\n"
)


class CodexAdapter:
    """Build a Codex CLI invocation without broadening filesystem access.

    Network mode uses Codex's workspace-write network setting instead of
    falling back to danger-full-access. Domain enforcement remains an
    environment concern; the allowlist is exported for a wrapper/container
    that can enforce it.
    """

    name = "codex"

    def build(self, request: RunnerRequest) -> RunnerSpec:
        prompt = request.prompt
        if request.skill_name:
            prompt = f"Use the `{request.skill_name}` skill for this task.\n\n{prompt}"
        prompt += _RAW_YAML_REMINDER
        command = [
            "codex",
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "--config",
            f'sandbox_workspace_write.network_access={str(request.network_profile == "network").lower()}',
            "--sandbox",
            "workspace-write",
            "--cd",
            str(request.workspace),
            "--output-last-message",
            str(request.output_path),
            "--",
        ]
        environment: dict[str, str] = {}
        if request.network_profile == "network":
            environment["VALIDATE_ALLOWED_DOMAINS"] = ",".join(request.allowed_domains)
        command.append(prompt)
        return RunnerSpec(tuple(command), environment)
