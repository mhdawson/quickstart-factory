---
name: rh-qs-test-suite
description: >-
  Build production-grade GitHub Actions workflows for AI Quickstarts: split PR checks, Kind-based E2E,
  LLM evaluations, image publish, nightly schedules, and dev→main promotion. Use after rh-qs-debug-and-deploy
  when Helm and Makefile deploy targets exist, or when expanding CI beyond rh-qs-scaffold basics.
argument-hint: "Build or update CI workflows for a quickstart, or request nightly or image publishing only"
allowed-tools: Bash, Read, Write, Edit, Agent
---

# rh-qs-test-suite

**Category:** `github/`  
**Reference implementation:** [it-self-service-agent](https://github.com/rh-ai-quickstart/it-self-service-agent) `.github/`

## Goal

Plan and implement the requested CI workflow set for the resolved quickstart, recording the planned scope and resulting files in `.qs-factory/pipeline/test-suite-spec.yaml` and `.qs-factory/pipeline/test-suite-manifest.yaml`.

## Input

- A full CI build-out, or a focused request for nightly testing or image publishing
- Existing quickstart repository, Makefile, workflow files, and architecture testing strategy
- Optional upstream `.qs-factory/designs/architecture-spec.yaml`, `.qs-factory/pipeline/deploy-manifest.yaml`, and `.qs-factory/pipeline/deploy-state.yaml`

## Supporting Documents

**Main agent reads:**

- [Reasoning guardrails](./reasoning-guardrails.md)
- [Spec template](./spec-template.md)
- [Output templates](./output-templates.md)
- Relevant files in `references/`

**Subagents read:** their assigned prompt, the refined spec, and only the repository/reference files named by that prompt. Pass the prompt path to the subagent; do not load subagent prompts into the main context.

| Subagent prompt | Used for |
|---|---|
| `subagents/validation-skill-prompt.md` | Phase 0 quickstart resolution |
| `subagents/spec-validator-prompt.md` | Validate the proposed CI plan before implementation |
| `subagents/ci-workflows-prompt.md` | Generate requested PR, Kind, branch-policy, and release workflows |
| `subagents/build-and-push-prompt.md` | Image publishing workflow |
| `subagents/nightly-tests-prompt.md` | Reusable OpenShift tests and nightly callers |

## Workflow

### Phase 0: Resolve quickstart

This skill runs inside `.rhoai-qs/<slug>/`. List candidates with `ls -1 ../ 2>/dev/null` and invoke `subagents/validation-skill-prompt.md` before reading or writing quickstart files. Follow the result handling in `docs/foundation/validation-skill-template.md#main-agent-handling`.

### Phase 1: Analyze and draft the spec

Read the architecture testing strategy, relevant upstream manifests, Makefile, existing workflows, and the references needed for the request. Ask the user only for missing or ambiguous information needed to write the spec or complete the requested implementation. Check for an existing `test-suite-spec.yaml` and upstream content hashes before resuming. Write the initial spec to `.qs-factory/pipeline/test-suite-spec.yaml`; do not modify implementation files yet.

For nightly-only and build-and-push-only requests, keep the spec scoped to that capability and invoke only its dedicated generator after spec validation. Treat the spec as the implementation plan; do not ask the user to approve it. Preserve the build-and-push prompt's rule that standalone mode changes only `.github/workflows/build-and-push.yaml`.

### Phase 2: Validate and refine

Invoke `subagents/spec-validator-prompt.md` with the spec and repository root. Fix blocker findings in the spec, write `.qs-factory/pipeline/test-suite-spec-refined.yaml`, and revalidate up to two times. Do not start implementation while blockers remain. Ask the user only when a blocker depends on information or a decision needed to finish the spec or implementation; otherwise resolve it from repository evidence.

### Phase 3: Implement

Invoke `subagents/ci-workflows-prompt.md` with `repo_root` and the refined `spec_path` for the requested PR, Kind, branch-policy, or release workflows. Use `subagents/build-and-push-prompt.md` with `repo_root`, `spec_path`, and `invocation_mode` for image publishing. Use `subagents/nightly-tests-prompt.md` with the resolved `slug`, `repo_root`, `spec_path`, and `invocation_mode` for nightly testing. Preserve existing target names and make only targets included in the refined spec.

When a request includes more than one generator, run them sequentially where they may copy or update shared files, and give each the same refined spec. Do not add workflows omitted from the spec.

### Phase 4: Post-validate and record

Check every requested workflow and local action path, verify each `make <target>` call exists in the final Makefile, confirm the generated files match the refined spec, and record acceptance-criteria results and output paths in `.qs-factory/pipeline/test-suite-manifest.yaml` using [output-templates.md](./output-templates.md). Report any unverified GitHub settings as follow-up actions rather than claiming they were applied.

## Guidelines

- Treat the architecture testing strategy and the quickstart's actual Makefile as authoritative.
- Keep PR workflows fork-safe: never expose repository secrets to `pull_request` code.
- Do not invent Make targets, secrets, repository variables, branch models, or workflow requirements.
- For Kind E2E, confirm the quickstart can run in Kind before generating the workflow.
- Respect the focused-request scope gates. Ask the user only for information needed to draft the spec or complete implementation; do not request spec approval.
- If required upstream inputs are missing, record the gap and ask for the missing information before writing dependent artifacts.

For image publishing, use the skill-local [build-and-push workflow reference](./references/build-and-push-workflow.yaml) as the canonical pattern. It replaces the external example for this workflow.

## Trigger

- Run after **`rh-qs-debug-and-deploy`**, or when the user requests CI expansion for an existing quickstart.
- Architecture spec **`.qs-factory/designs/architecture-spec.yaml`** defines testing strategy (unit / integration / E2E / evals) — this skill runs inside `.rhoai-qs/<slug>/` itself (the scaffolded quickstart repo), so the architecture spec is in `.qs-factory/` right there, no `../` needed
- Optional: replace or extend minimal workflows from **`rh-qs-scaffold`**

## Nightly-only fast path

If the request is scoped to nightly testing specifically (e.g. "add nightly testing to `<slug>`", "update the nightly workflow", "refresh the nightly CI setup"), complete Phases 0–2 with a nightly-only spec, then invoke **`subagents/nightly-tests-prompt.md`** with the resolved slug, repo root, refined spec path, and `invocation_mode: standalone`; post-validate. Do not run unrelated phases.

## Build-and-push-only fast path

If the request is scoped to image publishing specifically (e.g. "create only the build-and-push workflow", "update image publishing", "fix the build-and-push workflow"), complete Phases 0–2 with a build-and-push-only spec, then invoke **`subagents/build-and-push-prompt.md`** with the repo root, refined spec path, and `invocation_mode: standalone`; post-validate. Do not run unrelated phases.

This is a hard scope gate: in standalone build-and-push mode, the only repository
file this path may create or update is `.github/workflows/build-and-push.yaml`.
Do not modify `Makefile`, `README.md`, Helm files, scripts, or any other
workflow merely to make the generated workflow work.

## CI capabilities

1. Splits CI into **focused workflows** (quality, unit tests, Kind E2E, evals, image build) instead of one monolithic job
2. Adds **composite actions** under `.github/actions/`; PR E2E and nightly both copy the shared actions from `quickstart-ci-testing`
3. Adds **`scripts/ci/`** helpers (Kind + local registry, optional integration hooks)
4. Defines a **Makefile CI contract** so workflows only call `make` targets
5. Documents required **secrets and repository variables**
6. Identifies **branch protection** status checks that should match workflow job names
7. Optionally adds **dev→main promotion** and **dev version-bump PR** workflows for mature quickstarts, and delegates **nightly** workflow generation to `subagents/nightly-tests-prompt.md` (also invokable on its own — see "Nightly-only fast path" above)

## CI generation requirements

The workflow generator follows the refined spec and the relevant files in `references/`. Treat the quickstart's Makefile, dependency manifests, and current workflows as authoritative. The reference target list and skeletons are examples, not requirements to add every target or use a particular package manager.

- For `pr-e2e-tests.yml`, pass `github.event.pull_request.head.ref` to the shared clone action; it accepts branches/tags, not commit SHAs.
- Set `persist-credentials: false` on the PR E2E `actions/checkout` step. This prevents the automatic `GITHUB_TOKEN` from remaining in Git config for later steps, even when the workflow uses no repository secrets or variables.
- Use `test-short-e2e` as the PR E2E target. Include `test-short-eval` only when it already exists.
- Never add secrets or repository variables to `pr-e2e-tests.yml`; keep secret-dependent tests in nightly workflows.
- When PR E2E targets require values omitted by the secret-free PR policy, add a YAML comment beside the affected Make commands naming the targets and values, explicitly stating they are unavailable to `pull_request` runs, and noting they belong in nightly testing.
- For Kind E2E, use `build_images: true` and explicitly map build/push targets when `build-all-images` and `push-all-images` exist.
- Set `upload_retention_days: 30` when uploading test results through `run-quickstart-tests`.
- Confirm the quickstart can run on Kind before generating a Kind workflow; OpenShift-only tests belong in nightly workflows.
- Use PR-specific concurrency and cancel superseded runs.
- Shared composite actions must include every repository-relative companion file they reference. Use the existing diff-and-prompt procedure when destination files differ.
- Document required secrets, variables, and status checks; do not claim GitHub settings were applied unless they actually were.

## Design principles (from it-self-service-agent)

| Principle | Practice |
|-----------|----------|
| Makefile as CI API | Workflows run `make <target>`; no duplicated install logic in YAML |
| Pin tool versions | Pin the tools this quickstart uses; when it uses uv, workflow `UV_VERSION` must match the Makefile |
| Concurrency | PR E2E: workflow group by PR number/run ID with `cancel-in-progress: true`. |
| Split by risk/cost | Fast lint/unit and Kind E2E on `pull_request`; heavy secret-dependent evals on schedule |
| Fail fast on secrets | First step validates required secrets before checkout/cluster work |
| Debug on failure | `if: failure()` → composite `inspect` (or upload cluster logs) |
| Artifacts | Tar and upload `evaluations/results` (or test reports) with `retention-days: 30` |
| Fork safety | Use `pull_request` for PR workflows and do not expose repository secrets to PR code |

## Workflow set (choose per design)

| Workflow file | Trigger | Purpose |
|---------------|---------|---------|
| `pr-checks.yml` | `pull_request` | Applicable dependency checks, lint, mypy/ruff, Helm export/kubeconform, unit tests |
| `pr-e2e-tests.yml` | `pull_request`, schedule, `workflow_dispatch` | Kind deploy via shared `quickstart-ci-testing` actions + integration + short tests; no repository secrets or variables |
| `pr-branch-check.yml` | `pull_request` → `main` | Enforce `dev` or `dev-<sha>` source branch |
| `build-and-push.yaml` | `push` to `main`/`dev`, `workflow_dispatch` | Self-contained build and push using Makefile targets; validates OCI tags and supports `FORCE_BUILD_ALL=TRUE` on manual dispatch to override the optional image-needed target |
| `test-<slug>.yml` | `workflow_call`, `workflow_dispatch` | Reusable deploy + test + teardown against a real OpenShift namespace, via actions copied from `quickstart-ci-testing` — generated by `subagents/nightly-tests-prompt.md` |
| `nightly-main.yml` / `nightly-<dev-branch>.yml` | `schedule`, `workflow_dispatch` | Thin scheduled callers of `test-<slug>.yml`, one per long-lived branch — generated by `subagents/nightly-tests-prompt.md` |
| `create-dev-to-main-pr.yml` | `workflow_dispatch` | Promotion PR requiring aligned release artifacts and a dev version later than main, with temp branch |
| `create-dev-to-main-bump-pr.yml` | `workflow_dispatch` | Bumps the dev release version and opens or updates a PR into `dev` |

Full catalog and naming conventions: [references/workflow-catalog.md](./references/workflow-catalog.md)

## Repository layout to add

```
.github/
├── workflows/
│   ├── pr-checks.yml
│   ├── pr-e2e-tests.yml          # if integration/e2e in design; uses shared `quickstart-ci-testing` actions
│   ├── pr-branch-check.yml         # if using dev/main promotion model
│   ├── build-and-push.yaml         # if publishing to quay.io/rh-ai-quickstart
│   ├── create-dev-to-main-pr.yml   # if promoting dev releases to main
│   └── create-dev-to-main-bump-pr.yml # create version bump PRs on dev
├── actions/
│   ├── setup-and-deploy/action.yml
│   ├── run-quickstart-tests/action.yml
│   └── cleanup/action.yml
scripts/ci/
└── kind-with-registry.sh
scripts/
├── bump_release.py
└── bump-release.manifest.json    # if using dev/main promotion or version-bump PRs
```

Skeleton YAML: [references/workflow-skeletons.md](./references/workflow-skeletons.md)

## Composite actions

PR E2E and nightly use the shared `quickstart-ci-testing` actions (`setup-and-deploy`, `run-quickstart-tests`, and `cleanup`). Copy those actions into `.github/actions/` before generating either workflow, along with repository-relative support files referenced by the actions. In particular, the shared `setup-kind` action invokes `scripts/ci/kind-with-registry.sh` from the quickstart root.

## Makefile CI contract

Add or map only the targets needed by the selected workflows. Preserve target
names already present in the quickstart; treat this list as the CI contract for
features the quickstart actually uses, not as a requirement to add every target.

| Target | Used by |
|--------|---------|
| `check-uv-version` | PR quality |
| `check-lockfiles` / `update-lockfiles` | PR quality |
| `deps-all` | PR unit + quality |
| `test-all` or `test` | PR unit |
| `helm-export-validate-demo` | PR helm (kubeconform) |
| `helm-depend` | Kind action |
| `build-all-images` / `push-all-images` | Kind + build-and-push |
| `helm-install-test` | Kind E2E |
| `helm-install-prod` | Nightly prod (optional) |
| `verify-deploy` | Post-install smoke (required before rh-qs-document) |
| `sync-evaluations` | E2E with LLM evals |
| `test-*-integration` | Named integration tests from design |

Full list: [references/makefile-ci-contract.md](./references/makefile-ci-contract.md)

### Adapt PR checks to the quickstart

Before generating `pr-checks.yml`, inspect the quickstart's `Makefile`, dependency
manifests, and existing workflows. The repository's actual commands and targets
are authoritative; the reference contract and workflow skeleton are examples,
not a requirement to add uv or to call every canonical target.

- Preserve existing Make target names. Do not rename a target or invent a
  replacement such as `check-requirements` when the repository already exposes
  the requested behavior under another name.
- Add a missing target only when the user requests it or it is needed for the
  requested workflow, and ensure the final workflow calls the target that was
  actually added.
- Select dependency setup from the repository's manifests and Makefile. For a
  pip/requirements quickstart, use pinned Python setup and its existing
  requirements check; do not add uv setup, `UV_VERSION`, or uv-specific checks
  unless the repository uses uv and those Make targets exist.
- When adding a pip install target, make it depend on the existing requirements
  check. When adding a Helm render target, preserve the Makefile's namespace
  default; if none exists, use the quickstart's established default and let CI
  override it for its namespace.
- Before reporting completion, read the generated workflow and confirm every
  `make <target>` call exists in the final Makefile. Confirm required existing
  targets are called directly when the request requires that, even if another
  target depends on them. Give workflow jobs the descriptive names used by
  required status checks. Preserve the selected skeleton's workflow name, PR
  event types, pinned action versions, and Python version unless repository
  configuration or the user requires a different value. Keep Makefile defaults
  unchanged unless the request requires a change.

Build-and-push generation is delegated to [the dedicated prompt](./subagents/build-and-push-prompt.md). It resolves the version, build, and publish targets from the quickstart's Makefile and README, asks for missing or ambiguous mappings before writing anything, and never substitutes canonical target names for absent targets.

## Secrets and variables

Configure in GitHub before enabling workflows that need repository secrets:

- **Secrets:** `LLM_API_TOKEN_EVAL`, `LLM_API_TOKEN_INFERENCE`, `QUAY_USERNAME`, `QUAY_PASSWORD`
- **Variables:** `LLM_URL_EVAL`, `LLM_ID_INFERENCE`, `LLM_INFERENCE`, `LLM_URL_INFERENCE`

Nightly testing has its own, per-quickstart secret/variable requirements — `PROD_TOKEN`/`PROD_SERVER` are always required, everything else is discovered from that quickstart's `deploy`/`test` targets rather than assumed. See [nightly-actions-catalog.md](./references/nightly-actions-catalog.md) and `subagents/nightly-tests-prompt.md`.

Never commit tokens. Use mock tokens only where workflows explicitly allow (e.g. `HF_TOKEN: mock_hf_token_for_ci` for helm template validation).

Catalog: [references/secrets-and-variables.md](./references/secrets-and-variables.md)

## Branch protection

Required status checks should match **job names** (or workflow names) users see in the PR UI, for example:

- `Code Quality Check`
- `Run unit-tests`
- `Helm export validation`
- `Run e2e tests (uv sync with evals)` — if E2E enabled

For repos using **dev → main**: require `Validate PR comes from dev branch` on PRs to `main`.

## Minimal vs full quickstart

| Profile | Include |
|---------|---------|
| **Minimal** | `pr-checks.yml` only (extends scaffold `ci.yaml` pattern) |
| **Standard** | `pr-checks.yml` + `pr-e2e-tests.yml` + shared `quickstart-ci-testing` actions + `scripts/ci/` |
| **Agent + evals** | Standard + eval artifact upload through `pr-e2e-tests.yml` |
| **Release train** | Full + `pr-branch-check.yml` + `build-and-push.yaml` + `create-dev-to-main-bump-pr.yml` + `create-dev-to-main-pr.yml` + nightlies |

Match profile to the **Testing strategy** section in `.qs-factory/designs/architecture-spec.yaml`.

## Verification

```bash
# Local parity with CI
make check-lockfiles
make lint
make test-all
make helm-export-validate-demo NAMESPACE=ci-demo HF_TOKEN=mock_hf_token_for_ci

# Kind path (requires podman/docker + kind)
bash scripts/ci/kind-with-registry.sh
make helm-install-test NAMESPACE=test REGISTRY=localhost:5001 ...
```

Open a PR and confirm workflows pass. PR E2E workflows use `pull_request` and do not receive repository secrets; run secret-dependent checks in nightly workflows.

Before reporting a PR E2E workflow complete, verify every local `uses: ./...`
path exists and inspect copied actions for repository-relative script references.
For Kind, confirm `scripts/ci/kind-with-registry.sh` exists, the workflow
passes explicit build and push Make targets, and uploaded results use the
30-day retention input.

## Output

- `.qs-factory/pipeline/test-suite-spec.yaml` and `.qs-factory/pipeline/test-suite-spec-refined.yaml`
- `.qs-factory/pipeline/test-suite-manifest.yaml` with implementation and validation results
- `.github/workflows/*` and `.github/actions/*` created or updated
- `scripts/ci/*` for Kind/registry
- `scripts/bump_release.py` and `scripts/bump-release.manifest.json` when dev version bumps or dev→main promotion are enabled
- Makefile targets documented in README (via `rh-qs-document`)
- Required branch protection checks documented for a GitHub administrator

## Next skill

When CI workflows are green on a test PR → **`rh-qs-verify-deploy`**, then **`rh-qs-document`**

## References

- [Workflow catalog](./references/workflow-catalog.md) — map each it-self-service-agent workflow to quickstart use
- [Secrets and variables](./references/secrets-and-variables.md)
- [Makefile CI contract](./references/makefile-ci-contract.md)
- [Workflow skeletons](./references/workflow-skeletons.md) — copy-paste YAML starters
- [Build-and-push workflow reference](./references/build-and-push-workflow.yaml) — canonical local workflow for automatic and manual image publishing
- [Create dev-to-main PR workflow](./references/create-dev-to-main-pr-workflow.yml) and [dev version-bump PR workflow](./references/create-dev-to-main-bump-pr-workflow.yml) — canonical release train workflows
- [Release helper](./references/bump_release.py) and [release manifest](./references/bump-release.manifest.json) — shared version read, update, and verification logic
- [Build-and-push subagent](./subagents/build-and-push-prompt.md) — deterministic Make-target resolution and workflow generation
- [Shared CI actions catalog](./references/nightly-actions-catalog.md) — `quickstart-ci-testing` actions, reusable test workflow + nightly caller skeletons, provisioning script (used by PR E2E generation and `subagents/nightly-tests-prompt.md`)
