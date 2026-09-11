---
name: validate-skill
description: Run fixture-based behavioral validations for a Factory skill and rate each output against its expected-output-repo baseline.
allowed-tools: Bash, Read, Write, Edit, Agent
---

# validate-skill

## Goal

Validate a Factory skill by running fixture cases under `test/skills/<skill-name>/`. By default it runs every case; an optional comma-separated case list runs only those named cases. Each case is copied into the disposable quickstart path `.rhoai-qs/qs-test-quickstart/`, executed through the target skill, and rated from 1 to 10 against its approved, complete post-run repository baseline.

This skill tests skill behavior. It does not replace unit tests for deterministic scripts, and it does not deploy to a cluster unless the target skill's fixture explicitly requires a human-approved operational test.

## Mandatory execution rule

When the user invokes `validate-skill`, run the complete validation workflow below. Do not manually simulate the target skill, synthesize generated output, or assign a validation score from inspection alone. A completed result is valid only when:

1. The selected fixture was prepared with `prepare_fixture.py`.
2. The target skill was actually executed through the case runner.
3. The generated quickstart output was compared with `compare_baseline.py`.
4. The independent output rater evaluated the result.

If the case runner or independent output rater cannot be invoked, report the case as `blocked` or `failed`; never mark it passed and never create a substitute score or fabricated validation artifacts. Targeted validation narrows what the rater evaluates, but it does not permit skipping target-skill execution or required target-skill behavior outside the targeted assertion.

When the workflow is delegated through an external runner, preserve the caller's authenticated execution context. Do not replace authentication-related environment variables with a fresh temporary directory; the case runner must use the existing authenticated context.

## Input

- Target skill name, for example `rh-qs-test-suite`.
- One or more test directories in `test/skills/<skill-name>/` following [the fixture contract](./references/fixture-contract.md). Each has a `test-config.yaml` with an optional target-skill prompt, question-answer context, and `validation-options` for evaluation behavior.
- Optional test filter, for example `--tests standard-pattern,cluster-privileges`. Test names must exactly match immediate fixture-directory names. Omit it to run every case.

## Supporting Documents

**Main agent reads directly:**

| File | When |
|---|---|
| [reasoning-guardrails.md](./reasoning-guardrails.md) | Before copying fixtures, answering questions, or rating output |
| [spec-template.md](./spec-template.md) | Before recording the validation plan |
| [output-templates.md](./output-templates.md) | Before writing the validation report |
| [references/fixture-contract.md](./references/fixture-contract.md) | Before discovering cases |
| [scripts/discover_cases.py](./scripts/discover_cases.py) | Phase 1 case discovery and validation |
| [scripts/preflight_dependencies.py](./scripts/preflight_dependencies.py) | Before a network-enabled case runner |
| [scripts/prepare_fixture.py](./scripts/prepare_fixture.py) | Before each case, to reset and copy its fixture |
| [scripts/run_case.py](./scripts/run_case.py) | Synchronous case-runner gate and completion manifest |
| [scripts/compare_baseline.py](./scripts/compare_baseline.py) | Before independent output rating |
| [scripts/archive_fixture.py](./scripts/archive_fixture.py) | After each completed case, to retain its generated quickstart tree for debugging |
| [scripts/write_conversation.py](./scripts/write_conversation.py) | After each case, to retain caller-to-target-skill messages |
| [scripts/write_report.py](./scripts/write_report.py) | Phase 4 report rendering |
| [scripts/orchestrate_validation.py](./scripts/orchestrate_validation.py) | Preferred deterministic coordinator for the complete workflow |
| [runners/](./runners/) | Foreground Codex, Claude, Cursor, and Gemini adapters with a shared execution contract |

**Subagents read (pass by path only):**

| File | Subagent |
|---|---|
| [subagents/validation-skill-prompt.md](./subagents/validation-skill-prompt.md) | Verifies the fixed disposable quickstart context |
| [subagents/case-runner-prompt.md](./subagents/case-runner-prompt.md) | Executes one case through the target skill |
| [subagents/output-rater-prompt.md](./subagents/output-rater-prompt.md) | Independently compares actual and expected output |

## Workflow

### Preferred execution path

Use `scripts/orchestrate_validation.py` to coordinate the phases below. It still
delegates target-skill execution and independent rating to the supplied commands;
the Python coordinator owns ordering, fixture isolation, evidence capture, schema
validation, archives, and reports.

The runner and rater can be supplied as JSON command arrays, or selected through
the foreground adapters in `runners/`. Adapter execution is synchronous and
inherits the caller's authenticated environment. Adapters do not silently use
background agents or broaden filesystem access. Use `--runner-adapter` and
`--runner-prompt-file` (and the corresponding `--rater-*` options) when the
client adapter should own command construction. Raw command arrays remain
supported for custom runners.

The coordinator supports these placeholders in raw command arguments and
adapter prompt files:

- `{runner_output}` — runner result YAML path
- `{rater_output}` — independent-rater result YAML path
- `{case_path}` — absolute fixture case path
- `{quickstart_root}` — absolute disposable quickstart path
- `{comparison_json}` — baseline comparison JSON path
- `{conversation_json}` — runner conversation JSON path

It rejects unknown or unresolved placeholders. The runner command is responsible
for providing the execution capabilities required by the selected fixtures:

- For any case whose fixture declares `execution.network: required`, invoke the
  coordinator with `--network-profile network` and run the case runner in a
  network-capable context. The profile is a validation declaration; it cannot
  grant network access by itself.
- The runner must have read/write access to the repository root and the fixed
  disposable path `.rhoai-qs/qs-test-quickstart/`. Use the supplied
  `{quickstart_root}` placeholder when the runner needs the absolute path.
- Do not use an isolated runner for a network-required case, and do not replace
  the disposable path with a temporary or user-selected quickstart path.

Example shape (with the model-specific commands supplied by the caller):

```bash
python3 core/skills/validate-skill/scripts/orchestrate_validation.py \
  <skill-name> --tests <case-one,case-two> \
  --network-profile network \
  --runner-command-json '<JSON array>' \
  --rater-command-json '<JSON array>'
```

Adapter form:

```bash
python3 core/skills/validate-skill/scripts/orchestrate_validation.py \
  <skill-name> --tests <case-one,case-two> \
  --runner-adapter codex \
  --runner-prompt-file core/skills/validate-skill/subagents/case-runner-prompt.md \
  --rater-adapter codex \
  --rater-prompt-file core/skills/validate-skill/subagents/output-rater-prompt.md
```

For a network-required case, the adapter receives the declared dependency
hostnames. The adapter's execution environment must enforce any domain
allowlist; an environment variable alone is not a network security boundary.

The coordinator writes per-case evidence under
`test/skills/reports/<skill-name>/<case-name>/` and an aggregate result/report
under `test/skills/reports/<skill-name>/`.

### Phase 0: Verify disposable context

Spawn the validation subagent with the fixed target slug `qs-test-quickstart`, the requested target skill, and the case root. It confirms the target is the test-only path `.rhoai-qs/qs-test-quickstart/`, rather than a user quickstart. Stop if the target name or fixture path differs.

### Phase 1: Discover and validate cases

1. Run `python3 core/skills/validate-skill/scripts/discover_cases.py <skill-name> [--tests <test-one>,<test-two>]`. It resolves the target skill, selects all cases or only the named tests, finds them in lexical order, and validates their required inputs. Stop if it reports malformed or unknown selected tests. Do not validate or run unselected cases.
2. Read the emitted JSON instead of manually enumerating or re-checking case paths.
3. For a case with `execution.network: required`, run `python3 core/skills/validate-skill/scripts/preflight_dependencies.py <case-path>`. Preserve its JSON result as execution evidence. A failed preflight is an infrastructure warning, not permission to skip target execution; run the case runner in a network-enabled execution context and classify the case as `blocked` or `failed` if the runner cannot access the dependency.
4. Read `spec-template.md` and write `test/skills/reports/<skill-name>/<case-name>/validation-spec.yaml` for each discovered case, recording the target skill, the case, the fixed quickstart slug `qs-test-quickstart`, its baseline path, and execution requirements.

### Phase 2: Run each case in isolation

For each case, in deterministic lexical order:

1. Run `python3 core/skills/validate-skill/scripts/prepare_fixture.py <case-path>`. It removes only `.rhoai-qs/qs-test-quickstart/`, recreates it, copies the contents of `input-repo/`, and emits an inventory manifest.
2. Read the emitted inventory; do not repeat its file-system checks manually.
3. Invoke `python3 core/skills/validate-skill/scripts/run_case.py` with the case path, fixed quickstart root, a runner-result path, a completion-record path, and the case-runner command. Use `{runner_output}`, `{quickstart_root}`, and `{case_path}` as command placeholders where needed. The script must block until the runner process exits, require its result status to be `completed`, compute the final output manifest and tree hash itself, and return non-zero otherwise. When `execution.network` is `required`, launch the runner with network access appropriate for the declared dependencies and with access to `.rhoai-qs/qs-test-quickstart/`; do not silently retry in an isolated context or change the disposable path. When `run_skill_command` is absent, invoke the target skill without adding a supplemental user request.
4. If the target skill asks a question, use `question_answer_context` only when it provides an unambiguous, fixture-grounded answer. For a user preference, overwrite decision, credential, cluster action, GitHub mutation, or any other external authority, stop that case and record `blocked` with the question. Never invent credentials or consent.
5. Capture the runner's final report, generated files, blocked question, and chronological `conversation` messages. Retain every caller prompt, target-skill response or question, and any answer supplied from `question_answer_context`; do not include tool output or internal reasoning.

Do not replace the case runner with hand-authored files in `.rhoai-qs/qs-test-quickstart/`. The target skill must produce the output being evaluated, including files that are outside a targeted assertion.

### Phase 3: Rate the output

For each case whose `run_case.py` completion record has status `completed`, run `python3 core/skills/validate-skill/scripts/compare_baseline.py <case-path>`. Pass its JSON output, `validation_mode`, the optional `additional_validation_instructions` from `test-config.yaml`'s `validation-options` mapping, and the runner's recorded `conversation` to the independent output rater with [subagents/output-rater-prompt.md](./subagents/output-rater-prompt.md), along with the expected baseline and actual quickstart root. Pass the conversation as observable caller-to-target evidence, not as the runner's self-assessment. The rater judges the materiality of reported differences; it does not rediscover file inventories or hashes.

The rater returns a 1–10 score with evidence. In the default `full-baseline` mode, a score of 10 requires the complete actual repository tree to match the approved post-run baseline, except paths explicitly excluded by the case's `comparison-ignore`. In `targeted` mode, score only the checks in `additional_validation_instructions`; do not penalize baseline-tree differences outside that scope. A blocked or failed execution has no quality score; record it as `blocked` or `failed`, not as a misleading low score.

Never author `validation-results.json` as a substitute for the runner or rater. Its score and evidence must be copied from the completed execution and independent rating.

After rating a completed case, add its runner `conversation` to `validation-results.json`, then run `python3 core/skills/validate-skill/scripts/write_conversation.py --input <results.json> --case <case-name> --output test/skills/reports/<skill-name>/<case-name>/skill-conversation.md`. Also run `python3 core/skills/validate-skill/scripts/archive_fixture.py <skill-name> <case-name> --output test/skills/reports/<skill-name>/<case-name>/quickstart-output.tar.gz`. The archive is a debugging artifact of `.rhoai-qs/qs-test-quickstart/`; never use it as a baseline or input to another case.

### Phase 4: Report

Read `output-templates.md`, assemble each case result as `test/skills/reports/<skill-name>/<case-name>/validation-results.json`, and run `python3 core/skills/validate-skill/scripts/write_report.py --input <results.json> --output test/skills/reports/<skill-name>/<case-name>/validation-report.md`. Each completed-case directory also contains `quickstart-output.tar.gz` from Phase 3. In the final user message, lead with the aggregate result and identify any case scoring below 8.

## Guidelines

- Use `test/skills/`, not `test/skils/`.
- Treat `test-config.yaml`'s `run-skill-command` as a prompt to the target skill, never as shell code.
- Do not modify `input-repo/` or `expected-output-repo/` during a run. Generated output belongs only in `.rhoai-qs/qs-test-quickstart/`.
- Do not let one case's files, answers, or state affect another case.
- Persist only caller-to-target-skill messages in `skill-conversation.md`. Do not store internal reasoning, tool output, credentials, or unredacted secrets.
- Preserve the target skill's normal safety rules. This validator cannot authorize cluster access, secret changes, GitHub writes, or destructive overwrites.
- In `full-baseline` mode, apply additional validation instructions only when they are compatible with the fixture contract and safety rules; they cannot waive a required baseline artifact. In `targeted` mode, they define the exclusive evaluation scope. Neither mode authorizes external actions.
- Use the complete post-run baseline as the primary oracle in `full-baseline` mode. In `targeted` mode, use only the explicit additional validation instructions as the oracle.

## Success Criteria

- Every well-formed case is either rated with evidence or explicitly reported as blocked/failed.
- Each completed case has an independent 1–10 rating grounded in `expected-output-repo/`.
- The aggregate report is written without modifying the fixture inputs or expected baselines.
