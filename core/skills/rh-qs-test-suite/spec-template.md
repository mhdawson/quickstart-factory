---
description: Template for the rh-qs-test-suite implementation specification
---

# Test Suite Specification Template

This spec records the implementation plan for adding or updating CI workflows in the quickstart repository. It is written before implementation to `.qs-factory/pipeline/test-suite-spec.yaml`; after validation, the refined version is written to `.qs-factory/pipeline/test-suite-spec-refined.yaml`. The agent validates and follows the refined spec without asking the user to approve it.

## YAML Structure

```yaml
spec_version: 1
quickstart_name: "<name from README or architecture spec>"
slug: "<resolved quickstart slug>"
skill: rh-qs-test-suite
created_at: "<ISO 8601 UTC timestamp>"

inputs:
  prior_manifests:
    - path: .qs-factory/designs/architecture-spec.yaml
      skill: rh-qs-architect
      content_hash: "sha256:<computed SHA-256>"
    - path: .qs-factory/pipeline/deploy-manifest.yaml
      skill: rh-qs-deploy
      content_hash: "sha256:<computed SHA-256>"
    - path: .qs-factory/pipeline/deploy-state.yaml
      skill: rh-qs-debug-and-deploy
      content_hash: "sha256:<computed SHA-256>"
  user_inputs:
    - type: request
      source: "<requested workflow scope and constraints>"

components:
  workflow_profile: minimal | standard | agent-evals | release-train | focused
  workflows:
    - file: .github/workflows/pr-checks.yml
      trigger: pull_request
      purpose: "<checks this workflow provides>"
      action: create | update | retain
      rationale: "<evidence from request/design/repo>"
  make_targets:
    - target: <existing-target>
      action: reuse | add | omit
      used_by: [.github/workflows/pr-checks.yml]
      evidence: "<Makefile target or documented reason to add>"
  shared_actions:
    required: []
    source: quickstart-ci-testing
    companion_files: []
  environment:
    secrets: []
    variables: []
    pull_request_secret_free: true
  branch_protection:
    required_status_checks: []
    github_settings_to_apply: []
  files:
    create: []
    update: []
    preserve: []

acceptance_criteria:
  - id: ac-1
    description: "Only the requested workflow set and supporting files are changed"
    validation: "Compare changed paths with components.files"
    requires_user_approval: false
  - id: ac-2
    description: "Every workflow make target exists in the final Makefile"
    validation: "Inspect each workflow make call and resolve it to a Makefile target"
    requires_user_approval: false
  - id: ac-3
    description: "Pull request workflows do not expose repository secrets to PR code"
    validation: "Inspect event triggers, job/step environments, and secret references"
    requires_user_approval: false

validation_rules:
  - id: vr-1
    check: "The selected workflows match the request and architecture testing strategy"
    severity: blocker
  - id: vr-2
    check: "Every make target is present or has an explicit addition plan"
    severity: blocker
  - id: vr-3
    check: "No repository secret is exposed to an untrusted pull_request workflow"
    severity: blocker
  - id: vr-4
    check: "Kind E2E is selected only when the quickstart can run on Kind"
    severity: blocker
  - id: vr-5
    check: "GitHub-side branch protection changes are identified as follow-up actions"
    severity: warning

dependencies:
  - spec: architecture-spec.yaml
    fields_used: [testing_strategy]
    content_hash: "sha256:<computed SHA-256>"
  - spec: deploy-manifest.yaml
    fields_used: [helm, make_targets]
    content_hash: "sha256:<computed SHA-256>"
  - spec: deploy-state.yaml
    fields_used: [overall_status, resources, e2e_results]
    content_hash: "sha256:<computed SHA-256>"
```

## Field Guidance

- Use only the relevant workflow profile. Focused nightly and image publishing specs list only their requested feature.
- `files.create`, `files.update`, and `files.preserve` must make the implementation boundary explicit.
- List Make targets from repository evidence. A missing target is `add` only when the request or selected workflow needs it.
- Record secrets and variables by name and purpose; never store values.
- If an upstream manifest is absent, remove it from `prior_manifests` and `dependencies`, and record the missing evidence in `user_inputs` or a validation warning. The deploy state is produced by `rh-qs-debug-and-deploy`, which precedes this skill in the pipeline.
- Every implementation change must be represented in the refined spec before it is applied.
