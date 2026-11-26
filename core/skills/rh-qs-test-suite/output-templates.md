# rh-qs-test-suite Output Templates

The skill produces CI workflow files and a pipeline manifest that records what was implemented and validated. Secret values must never be written to either artifact.

## `.qs-factory/pipeline/test-suite-manifest.yaml`

```yaml
spec_version: 1
quickstart_name: "<quickstart name>"
slug: "<resolved slug>"
skill: rh-qs-test-suite
created_at: "<ISO 8601 UTC timestamp>"

workflow_profile: minimal | standard | agent-evals | release-train | focused
spec:
  path: .qs-factory/pipeline/test-suite-spec-refined.yaml
  content_hash: "sha256:<hash>"
files:
  created: []
  updated: []
  preserved: []
make_targets:
  verified: []
  added: []
environment_requirements:
  secrets:
    - name: <secret-name>
      required_by: <workflow or target>
      reason: <repository-backed explanation>
  variables: []
validation:
  workflow_targets_exist: true
  local_action_paths_exist: true
  pull_request_secrets_safe: true
  kind_compatibility_checked: true
acceptance_criteria:
  - criterion_id: ac-1
    status: pass | fail | not_applicable
    evidence: "<observed file or validation result>"
github_follow_up:
  required_status_checks: []
  settings_not_applied: true
```

`created` and `updated` contain repository-relative paths. `verified` lists every Make target referenced by generated workflows; `added` lists targets changed as part of the requested scope. Report GitHub branch-protection changes here as follow-ups unless they were actually applied.

## Completion Report

Summarize the selected profile, workflows and supporting files created or updated, validation results, required secret/variable names, and GitHub-side follow-up steps. Do not include secret values. Distinguish files checked locally from settings that require a GitHub administrator.
