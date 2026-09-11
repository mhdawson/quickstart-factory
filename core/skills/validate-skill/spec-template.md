# Validation Spec Template

For each case, write `test/skills/reports/<skill-name>/<case-name>/validation-spec.yaml` before running it:

```yaml
spec_version: 1
skill: validate-skill
target_skill: <skill-name>
quickstart_slug: qs-test-quickstart
created_at: <ISO-8601 timestamp>
test_filter: <comma-separated requested test names | null>
cases:
  - name: <case-name>
    input_repo: test/skills/<skill-name>/<case-name>/input-repo
    expected_output_repo: test/skills/<skill-name>/<case-name>/expected-output-repo
    test_config: test/skills/<skill-name>/<case-name>/test-config.yaml
    run_skill_command: <text from test-config.yaml | null>
    question_answer_context: <text from test-config.yaml | null>
    validation_options:
      mode: full-baseline | targeted
      additional_instructions: <text from test-config.yaml | null>
    execution:
      network: none | required
      external_dependencies: <list from test-config.yaml>
    completion:
      runner_gate: core/skills/validate-skill/scripts/run_case.py
      status: completed
acceptance_criteria:
  - id: isolated-fixtures
    description: Each case starts with a fresh qs-test-quickstart copy.
    validation: Confirm the target path is removed and recreated before every case.
    requires_user_approval: false
  - id: baseline-rating
    description: Every completed case has an evidence-based 1–10 rating.
    validation: Inspect the validation report.
    requires_user_approval: false
```
