---
name: rh-qs-test-suite
description: |
  Build production-grade GitHub Actions workflows for AI Quickstarts: split PR checks, Kind-based E2E,
  LLM evaluations, image publish, nightly schedules, and dev→main promotion. Use after rh-qs-deploy
  when Helm and Makefile deploy targets exist, or when expanding CI beyond rh-qs-scaffold basics.
---

# rh-qs-test-suite

**Category:** `github/`  
**Reference implementation:** [it-self-service-agent](https://github.com/rh-ai-quickstart/it-self-service-agent) `.github/`

For image publishing, use the skill-local [build-and-push workflow reference](./references/build-and-push-workflow.yaml) as the canonical pattern. It replaces the external example for this workflow.

## Trigger

- Helm chart and Makefile deploy targets exist from **`rh-qs-deploy`** if not create it.
- Architecture spec **`.qs-factory/designs/architecture-spec.yaml`** defines testing strategy (unit / integration / E2E / evals) — this skill runs inside `.rhoai-qs/<slug>/` itself (the scaffolded quickstart repo), so the architecture spec is in `.qs-factory/` right there, no `../` needed
- Optional: replace or extend minimal workflows from **`rh-qs-scaffold`**

## Nightly-only fast path

If the request is scoped to nightly testing specifically (e.g. "add nightly testing to `<slug>`", "update the nightly workflow", "refresh the nightly CI setup") rather than the full CI build-out, skip straight to it: resolve the slug/repo as usual, then invoke **`subagents/nightly-tests-prompt.md`** directly (`invocation_mode: standalone`) and report its result. Do not run the PR-checks/E2E/build-and-push phases for this request — they are unrelated to what was asked. This is the same subagent step 8 below delegates to; the only difference is you stop after it instead of continuing the rest of the workflow.

## Build-and-push-only fast path

If the request is scoped to image publishing specifically (e.g. "create only the build-and-push workflow", "update image publishing", "fix the build-and-push workflow") rather than the full CI build-out, resolve the quickstart repository and then invoke **`subagents/build-and-push-prompt.md`** directly (`invocation_mode: standalone`). Do not run the PR-checks/E2E/nightly/promotion phases for this request. This is the same subagent step 7 below delegates to; the only difference is you stop after it instead of continuing the rest of the workflow.

This is a hard scope gate: in standalone build-and-push mode, the only repository
file this path may create or update is `.github/workflows/build-and-push.yaml`.
Do not modify `Makefile`, `README.md`, Helm files, scripts, or any other
workflow merely to make the generated workflow work.

## What it does

1. Splits CI into **focused workflows** (quality, unit tests, Kind E2E, evals, image build) instead of one monolithic job
2. Adds **composite actions** under `.github/actions/` (`prepare-runner`, `kind`, `inspect`)
3. Adds **`scripts/ci/`** helpers (Kind + local registry, optional integration hooks)
4. Defines a **Makefile CI contract** so workflows only call `make` targets
5. Documents required **secrets and repository variables**
6. Configures **branch protection** status checks to match workflow job names
7. Optionally adds **dev→main promotion** workflows for mature quickstarts, and delegates **nightly** workflow generation to `subagents/nightly-tests-prompt.md` (also invokable on its own — see "Nightly-only fast path" above)

## Workflow

```
- [ ] 1. Read design testing strategy + PRD eval requirements
- [ ] 2. Add Makefile CI targets (see references/makefile-ci-contract.md)
- [ ] 3. Add scripts/ci/kind-with-registry.sh (Podman-compatible)
- [ ] 4. Add composite actions (prepare-runner, kind, inspect)
- [ ] 5. Add PR workflows (checks, e2e, branch policy — as needed), starting from
      the matching workflow skeleton and adapting only repo-specific setup and
      Make targets
- [ ] 6. Configure repo secrets/vars (see references/secrets-and-variables.md)
- [ ] 7. When publishing images, invoke `subagents/build-and-push-prompt.md` to add the self-contained workflow for push to main/dev and manual dispatch
- [ ] 8. When design requires nightly testing, invoke `subagents/nightly-tests-prompt.md`; add dev→main promotion workflow separately if needed
- [ ] 9. Register required status checks in branch protection
- [ ] 10. Open test PR and confirm all workflows green
```

## Design principles (from it-self-service-agent)

| Principle | Practice |
|-----------|----------|
| Makefile as CI API | Workflows run `make <target>`; no duplicated install logic in YAML |
| Pin tool versions | Pin the tools this quickstart uses; when it uses uv, workflow `UV_VERSION` must match the Makefile |
| Concurrency | `group: ${{ github.workflow }}-${{ github.event.pull_request.number }}` + `cancel-in-progress: true` on PRs |
| Split by risk/cost | Fast lint/unit on `pull_request`; heavy Kind/evals on `pull_request_target` or schedule |
| Fail fast on secrets | First step validates required secrets before checkout/cluster work |
| Debug on failure | `if: failure()` → composite `inspect` (or upload cluster logs) |
| Artifacts | Tar and upload `evaluations/results` (or test reports) with `retention-days: 30` |
| Fork safety | `pull_request` for untrusted code; `pull_request_target` only when org secrets are required — checkout `github.event.pull_request.head.sha` |

## Workflow set (choose per design)

| Workflow file | Trigger | Purpose |
|---------------|---------|---------|
| `pr-checks.yml` | `pull_request` | Applicable dependency checks, lint, mypy/ruff, Helm export/kubeconform, unit tests |
| `pr-e2e-tests.yml` | `pull_request_target`, schedule, `workflow_dispatch` | Kind deploy + integration + short evals |
| `pr-pip-install-build.yml` | `pull_request` | Validate alternate install path (`use_pip_install`) |
| `pr-evaluation-check.yml` | `pull_request_target` | Known-bad conversation / regression eval gate |
| `pr-branch-check.yml` | `pull_request` → `main` | Enforce `dev` or `dev-<sha>` source branch |
| `build-and-push.yaml` | `push` to `main`/`dev`, `workflow_dispatch` | Self-contained build and push using Makefile targets; validates OCI tags and supports `FORCE_BUILD_ALL=TRUE` on manual dispatch to override the optional image-needed target |
| `test-<slug>.yml` | `workflow_call`, `workflow_dispatch` | Reusable deploy + test + teardown against a real OpenShift namespace, via actions copied from `quickstart-ci-testing` — generated by `subagents/nightly-tests-prompt.md` |
| `nightly-main.yml` / `nightly-<dev-branch>.yml` | `schedule`, `workflow_dispatch` | Thin scheduled callers of `test-<slug>.yml`, one per long-lived branch — generated by `subagents/nightly-tests-prompt.md` |
| `create-dev-to-main-pr.yaml` | `workflow_dispatch` | Version-checked promotion PR with temp branch |

Full catalog and naming conventions: [references/workflow-catalog.md](./references/workflow-catalog.md)

## Repository layout to add

```
.github/
├── workflows/
│   ├── pr-checks.yml
│   ├── pr-e2e-tests.yml          # if integration/e2e in design
│   ├── pr-branch-check.yml         # if using dev/main promotion model
│   └── build-and-push.yaml         # if publishing to quay.io/rh-ai-quickstart
├── actions/
│   ├── prepare-runner/action.yaml
│   ├── kind/action.yaml
│   └── inspect/action.yml
scripts/ci/
└── kind-with-registry.sh
```

Skeleton YAML: [references/workflow-skeletons.md](./references/workflow-skeletons.md)

## Composite actions

| Action | Role |
|--------|------|
| `prepare-runner` | Free disk (`jlumbroso/free-disk-space`); log memory/swap before Kind |
| `kind` | Install Kind → registry cluster → `make build/push` → `make helm-install-test` |
| `inspect` | On failure, capture namespace/events/logs (stub OK until wired) |

Details and inputs: [references/composite-actions.md](./references/composite-actions.md)

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

Configure in GitHub **before** enabling `pull_request_target` E2E workflows:

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
| **Standard** | `pr-checks.yml` + `pr-e2e-tests.yml` + `kind` action + `scripts/ci/` |
| **Agent + evals** | Standard + `pr-evaluation-check.yml` + eval artifact upload |
| **Release train** | Full + `pr-branch-check.yml` + `build-and-push.yaml` + `create-dev-to-main-pr.yaml` + nightlies |

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

Open a PR and confirm workflows pass. For `pull_request_target`, validate from a branch in the same repo (fork PRs may not receive secrets).

## Output

- `.github/workflows/*` and `.github/actions/*` committed
- `scripts/ci/*` for Kind/registry
- Makefile targets documented in README (via `rh-qs-document`)
- Branch protection updated with correct required checks

## Next skill

When CI workflows are green on a test PR → **`rh-qs-verify-deploy`**, then **`rh-qs-document`**

## References

- [Workflow catalog](./references/workflow-catalog.md) — map each it-self-service-agent workflow to quickstart use
- [Composite actions](./references/composite-actions.md) — `prepare-runner`, `kind`, `inspect`
- [Secrets and variables](./references/secrets-and-variables.md)
- [Makefile CI contract](./references/makefile-ci-contract.md)
- [Workflow skeletons](./references/workflow-skeletons.md) — copy-paste YAML starters
- [Build-and-push workflow reference](./references/build-and-push-workflow.yaml) — canonical local workflow for automatic and manual image publishing
- [Build-and-push subagent](./subagents/build-and-push-prompt.md) — deterministic Make-target resolution and workflow generation
- [Nightly actions catalog](./references/nightly-actions-catalog.md) — `quickstart-ci-testing` actions, reusable test workflow + nightly caller skeletons, provisioning script (used by `subagents/nightly-tests-prompt.md`)
