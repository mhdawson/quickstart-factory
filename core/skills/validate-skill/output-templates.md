# Validation Report Template

For each case, write these debugging artifacts under `test/skills/reports/<skill-name>/<case-name>/`:

- `validation-results.json` — structured result passed to the report renderer.
- `validation-spec.yaml` — run plan for this case.
- `validation-report.md` — rendered Markdown report.
- `skill-conversation.md` — chronological caller-to-target-skill messages, excluding tool output and internal reasoning.
- `quickstart-output.tar.gz` — archive of the final `.rhoai-qs/qs-test-quickstart/` tree.

The preferred coordinator also retains machine-readable phase evidence in each
case directory (`preflight.json`, `completion.json`, `comparison.json`, runner
and rater results, and process logs) and writes an aggregate
`test/skills/reports/<skill-name>/validation-report.md`.

The report Markdown is:

```markdown
# Validation report: <skill-name>

Run: <ISO-8601 timestamp>
Quickstart fixture path: `.rhoai-qs/qs-test-quickstart/`

| Case | Status | Score | Summary |
|---|---:|---:|---|
| <case-name> | passed | 9/10 | <brief evidence-based summary> |

## <case-name>

### Evidence

- Target command: `<test-config.yaml run-skill-command value, or none>`
- Required baseline artifacts: <list>
- Observed artifacts: <list>

### Differences

- <difference and its impact, or "None">

### Rating

**<n>/10** — <rationale tied to the expected baseline>.

### Blocked questions or failures

<Question and reason, or "None">.
```

The conversation Markdown is:

~~~~markdown
# Skill conversation: <skill-name> / <case-name>

## Caller

```text
<prompt or answer>
```

## Target skill

```text
<user-facing response or question>
```
~~~~
