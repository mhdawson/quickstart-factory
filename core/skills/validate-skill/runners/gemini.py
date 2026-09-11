"""Gemini CLI adapter for validate-skill."""

from __future__ import annotations

from .contract import RunnerRequest, RunnerSpec


_RAW_YAML_REMINDER = (
    "\n\nCRITICAL OUTPUT CONTRACT: return ONLY the complete YAML object requested by the prompt. "
    "Do not use Markdown fences and do not add prose before or after the YAML. "
    "Quote scalar values that contain a colon followed by a space, a hash, braces, or newlines; "
    "use a YAML block scalar for long or multi-line text.\n"
)


class GeminiAdapter:
    """Build a synchronous, headless Gemini CLI invocation."""

    name = "gemini"

    def build(self, request: RunnerRequest) -> RunnerSpec:
        prompt = request.prompt
        if request.skill_name:
            prompt = f"Use the `{request.skill_name}` skill for this task.\n\n{prompt}"
        prompt += _RAW_YAML_REMINDER
        command = [
            "gemini",
            "--prompt",
            prompt,
            "--output-format",
            "text",
            "--approval-mode=yolo",
            "--skip-trust",
        ]
        environment = {
            "VALIDATE_NETWORK_PROFILE": request.network_profile,
            "VALIDATE_ALLOWED_DOMAINS": ",".join(request.allowed_domains),
            "VALIDATE_OUTPUT_PATH": str(request.output_path),
        }
        return RunnerSpec(tuple(command), environment)
