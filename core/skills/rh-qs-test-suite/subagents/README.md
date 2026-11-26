# Subagents

| Name | Purpose | Input | Output | When used | Why subagent |
|---|---|---|---|---|---|
| `validation-skill-prompt.md` | Resolve the quickstart slug for the session | `user_message`, `existing_slugs`, `is_entry_point`, `calling_skill` | JSON resolution result | Phase 0 before reading or writing quickstart files | Prevents changes in the wrong quickstart when multiple repos are present |
| `spec-validator-prompt.md` | Check the proposed workflow plan against repository evidence | `repo_root`, `spec_path` | Markdown findings with blockers, warnings, and evidence | After drafting and before implementation | Independent consistency check before workflows or Makefiles change |
| `ci-workflows-prompt.md` | Generate requested PR, Kind, branch-policy, and release workflows | `repo_root`, `spec_path` | Workflow files, required Makefile changes, and verification report | Implementation phase for selected PR/release workflows | Keeps repository inspection and multi-file generation focused on the refined spec |

## Workflow Generators

| Name | Purpose | Input | Output | When used | Why subagent |
|------|---------|-------|--------|-----------|---------------|
| `build-and-push-prompt.md` | Generate a self-contained build-and-push workflow from the quickstart's real Makefile target contract | `repo_root`, `spec_path`, optional `target_mapping`, `invocation_mode` | `.github/workflows/build-and-push.yaml` plus a report of resolved targets, variables, and toolchain setup | Implementation phase for image publishing, including image-only requests | Target discovery and toolchain selection are self-contained and deterministic; the prompt requires evidence before generation |
| `nightly-tests-prompt.md` | Generate reusable OpenShift test and scheduled nightly workflows, copy shared composite actions, and report required secrets/variables and toolchain setup | `slug`, `repo_root`, `spec_path`, `invocation_mode` (`standalone` or `full-pipeline`) | `.qs-factory/pipeline/nightly-tests-manifest.yaml` plus a report | Implementation phase for nightly testing, including nightly-only requests | Target resolution, environment discovery, cluster-permission checks, and action copying are focused tasks with independently invokable behavior |
