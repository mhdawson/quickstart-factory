# validate-skill Subagents

| Name | Purpose | Input | Output | When used | Why subagent |
|---|---|---|---|---|---|
| `validation-skill-prompt.md` | Verify that this meta-skill uses only its fixed disposable quickstart context | Fixed slug, target skill, fixture root | Context status | Phase 0 | Prevents a fixture run from overwriting a real quickstart |
| `case-runner-prompt.md` | Run one target-skill case from a fresh fixture | Target skill path, prompt, fixture root, copied quickstart root, optional answers | Execution status, artifacts, questions, final target-skill report | Once per case | Keeps target-skill execution isolated from orchestration and evaluation |
| `output-rater-prompt.md` | Independently rate actual output against baseline | Actual quickstart root, expected-output root, fixture contract | Score, evidence, differences | After each completed case | Avoids allowing the executor to grade its own work |
