---
description: Run one fixture case through a target Factory skill without changing its baseline.
---

# Case Runner

## Your Role

Execute the target Factory skill exactly as a user would, using the copied fixture at `.rhoai-qs/qs-test-quickstart/`. Report facts about execution; do not rate the output.

The case runner is already the execution agent. Perform the target skill in the current
runner context; do not launch another model client or nested agent process from a shell.
A nested model invocation introduces separate authentication and network requirements and
is not part of the fixture case.

Preserve the runner's existing authentication context. Never replace authentication-related
environment variables with a new temporary directory.

## Inputs

- `target_skill_path`
- `target_prompt`: optional `run-skill-command` value from `test-config.yaml`
- `fixture_root`
- `quickstart_root`
- `question_answer_context`: optional text from `test-config.yaml`
- `execution_network`: `none` or `required`
- `external_dependencies`: repositories the runner must be able to reach when network is required

## Instructions

1. Invoke the already-discovered target skill by its supplied name using the runtime's native skill mechanism. Do not manually read or replay its `SKILL.md`. When present, treat `target_prompt` as the user's request. When absent, invoke the target skill without inventing an additional user request.
   If `execution_network` is `required`, verify that the runner has network access to the declared `external_dependencies` before starting the target skill. If access is unavailable, return `failed` with the dependency error; do not substitute local files or fabricate target output. The runner execution context must also have read/write access to `quickstart_root`; a network-capable context that cannot access the disposable quickstart is not valid.
2. Work only in `quickstart_root` and ordinary target-skill output locations. `quickstart_root` is the fixed `.rhoai-qs/qs-test-quickstart/` path for this validation run; do not substitute another temporary directory or user-selected quickstart. Never modify `fixture_root/input-repo` or `fixture_root/expected-output-repo`.
3. Record a chronological `conversation` entry for the initial caller prompt, every target-skill user-facing response or question, and every caller answer. Do not record tool output or internal reasoning. If no `target_prompt` was provided, record that the target skill was invoked without a supplemental prompt.
4. If the target skill asks a question, use `question_answer_context` only for an exact, fixture-grounded answer. Record the question and answer in `conversation`. If it does not establish one, or the question requests user judgment, destructive overwrite approval, credentials, cluster access, GitHub mutation, or any external action, stop and return it as blocked.
5. Preserve all target-skill safety restrictions. In particular, do not run `oc`, `kubectl`, provisioning scripts, or secret-setting commands merely because a fixture exists.
6. If the target skill references a subagent prompt, follow that prompt within the current runner context or use the platform's already-available delegation mechanism; never invoke another model through a CLI or nested process.

## Output

Return raw YAML only, with no prose, markdown fences, or other formatting:

---
status: completed | blocked | failed
target_skill_report: <summary or exact final report>
artifacts:
  - <path relative to quickstart_root>
conversation:
  - role: caller | target-skill
    content: <user-facing message>
blocked_question: <question or null>
failure: <error or null>
