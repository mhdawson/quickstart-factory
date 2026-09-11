"""Claude Code adapter for validate-skill."""

from __future__ import annotations

from pathlib import Path

from .contract import RunnerRequest, RunnerSpec

# core/skills/validate-skill/runners/claude.py -> repo root is 4 parents up.
_REPO_ROOT = Path(__file__).resolve().parents[4]


def _strip_frontmatter(prompt: str) -> str:
    """Drop a leading YAML frontmatter block, if present.

    A prompt beginning with a bare "---" is parsed by Claude's CLI as an
    unknown option rather than positional prompt text, so any frontmatter
    left on the prompt (e.g. from an unstripped subagent-prompt markdown
    file) must be removed before it reaches the command line.
    """
    if not prompt.startswith("---"):
        return prompt
    lines = prompt.split("\n")
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[index + 1 :]).lstrip("\n")
    return prompt


_RAW_YAML_REMINDER = (
    "\n\n**CRITICAL: Output ONLY raw YAML. No markdown code fences. No prose before or after.**\n"
    "Return the complete YAML object as plain text without any ```yaml, ```, or other formatting."
)


class ClaudeAdapter:
    """Build a synchronous Claude Code invocation.

    Claude's permission flags do not enforce network egress. The adapter
    exports the requested domains so a container/proxy wrapper can enforce
    them, while keeping the agent in its normal permission mode by default.

    The runner subprocess runs with the disposable quickstart as its cwd, so
    without extra directory access it cannot read the target skill's
    SKILL.md or any repo-relative docs it references. The adapter grants the
    repository root so those reads succeed. When the case declares network
    is required, it also bypasses permission prompts so fetches/tool calls
    against the declared dependencies are not left blocked on a prompt that
    nothing can answer in this non-interactive run.
    """

    name = "claude"

    def build(self, request: RunnerRequest) -> RunnerSpec:
        prompt = _strip_frontmatter(request.prompt)
        if request.skill_name:
            prompt = f"/{request.skill_name}\n{prompt}"
        prompt += _RAW_YAML_REMINDER
        command = [
            "claude",
            "--print",
            prompt,
            "--output-format",
            "text",
            "--add-dir",
            str(request.workspace),
            "--add-dir",
            str(_REPO_ROOT),
        ]
        if request.network_profile == "network":
            command += ["--permission-mode", "bypassPermissions"]
        environment = {
            "VALIDATE_NETWORK_PROFILE": request.network_profile,
            "VALIDATE_ALLOWED_DOMAINS": ",".join(request.allowed_domains),
            "VALIDATE_OUTPUT_PATH": str(request.output_path),
        }
        return RunnerSpec(tuple(command), environment)
