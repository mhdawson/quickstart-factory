---
description: Generate the requested PR, Kind, branch-policy, and release CI workflows
---

# CI Workflow Implementer

## Your Role

Implement the requested PR and release workflow portion of an `rh-qs-test-suite` plan in the quickstart repository. The orchestrator has resolved the quickstart and validated the spec. Follow the refined spec exactly; do not choose a broader CI profile or change scope.

## Instructions

**Input Parameters:**
- `{repo_root}`: quickstart repository root
- `{spec_path}`: `.qs-factory/pipeline/test-suite-spec-refined.yaml`

Read the refined spec first. Inspect the quickstart's Makefile, dependency manifests, current workflows, architecture testing strategy, and relevant references under `references/`. Use `references/workflow-skeletons.md`, `references/workflow-catalog.md`, and `references/makefile-ci-contract.md` as needed.

### Implement

1. Create or update only the PR, Kind, branch-policy, and release workflow files and Makefile targets listed in the refined spec. Leave build-and-push and nightly files to their dedicated generators.
2. Preserve existing Make target names. Add a target only when the refined spec calls for it and no existing target provides the behavior.
3. Match dependency setup and pinned versions to the repository's manifests, Makefile, or existing workflows. Do not add uv or other tooling when the repository does not use it.
4. Keep every `pull_request` workflow free of repository secrets and variables. Keep secret-dependent checks in nightly workflows.
5. Set `persist-credentials: false` on the PR E2E `actions/checkout` step so its automatic `GITHUB_TOKEN` is not left in Git config for later steps.
6. When PR E2E Make targets require values omitted by the secret-free PR policy, add a YAML comment beside the affected Make commands naming the targets and values, explicitly stating they are unavailable to `pull_request` runs, and noting they belong in nightly testing.
7. Before generating Kind E2E, confirm the quickstart can run in Kind. For the shared clone action, use `github.event.pull_request.head.ref`. Use `test-short-e2e`; include `test-short-eval` only if it exists. When `build-all-images` and `push-all-images` exist, enable image building and map both targets explicitly. Set result upload retention to 30 days.
8. Copy shared actions only when they are included in the refined spec. Include all repository-relative companion files, inspect `uses: ./...` paths, and compare existing destinations before replacing them.
9. Use PR-specific concurrency and cancel superseded runs. Preserve the selected skeleton's event types, workflow name, action pins, and Python version unless repository evidence or the spec requires a change.
10. Treat branch protection as a GitHub-side follow-up. Do not modify repository settings, open PRs, or configure secrets.

If implementation evidence contradicts the refined spec or a required target is missing, stop before writing dependent files and return the conflict to the orchestrator. Ask the user only if the conflict requires information or a decision they must supply.

### Verify

- Every workflow `make` call resolves to a target in the final Makefile.
- Every local `uses: ./...` path exists, including action companion scripts.
- PR workflows do not reference repository secrets or variables.
- Changed paths are within the files listed in the refined spec.

## Output

Return a Markdown report with files created/updated, Make targets reused/added, checks performed and evidence, and GitHub-side follow-ups. Do not include secret values.
