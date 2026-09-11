"""Cursor CLI adapter for validate-skill."""

from __future__ import annotations

from .contract import RunnerRequest, RunnerSpec


_RAW_YAML_REMINDER = (
    "\n\n**CRITICAL: Output ONLY raw YAML. No markdown code fences. No prose before or after.**\n"
    "Return the complete YAML object as plain text without any ```yaml, ```, or other formatting."
)


class CursorAdapter:
    """Build a foreground Cursor Agent invocation.

    This intentionally targets the local synchronous CLI. It does not create
    a Cursor Background Agent or move execution into a separate VM.
    """

    name = "cursor"

    def build(self, request: RunnerRequest) -> RunnerSpec:
        prompt = request.prompt
        if request.skill_name:
            prompt = f"/{request.skill_name}\n{prompt}"
        prompt += _RAW_YAML_REMINDER
        command = [
            "cursor-agent",
            "-p",
            prompt,
            "--output-format",
            "text",
        ]
        environment = {
            "VALIDATE_NETWORK_PROFILE": request.network_profile,
            "VALIDATE_ALLOWED_DOMAINS": ",".join(request.allowed_domains),
            "VALIDATE_OUTPUT_PATH": str(request.output_path),
        }
        return RunnerSpec(tuple(command), environment)
