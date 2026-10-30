# Workflow skeletons

Trimmed patterns from `it-self-service-agent`. Replace names, makes, and namespaces for `<slug>`.
These are examples, not a universal contract: the PR-checks example below is
for a uv-based quickstart. Inspect the quickstart's Makefile and dependency
manifests first, and adapt setup and targets to that repository as described in
the PR-check adaptation guidance in `SKILL.md`.

## PR trigger and concurrency preamble

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]

concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number }}
  cancel-in-progress: true

```

## pr-checks.yml — uv quickstart with matching Make targets

```yaml
name: Pull Request - Quality Checks & Unit Tests

env:
  UV_VERSION: "0.8.9" # replace with the quickstart's Makefile value

jobs:
  code-quality-check:
    name: Code Quality Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with:
          ref: ${{ github.event.pull_request.base.ref || github.ref }}
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: astral-sh/setup-uv@v9.0.0
        with:
          version: ${{ env.UV_VERSION }}
      - run: make check-uv-version
      - run: make check-lockfiles
      - run: make deps-all
      - run: make lint

  helm-export-validate:
    name: Helm export validation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: azure/setup-helm@v4
        with:
          version: v3.17.0
      - uses: bmuschko/setup-kubeconform@v1
      - run: make helm-export-validate-demo
        env:
          NAMESPACE: ci-demo
          HF_TOKEN: mock_hf_token_for_ci

  pull-request-tests:
    name: Run unit-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v9.0.0
        with:
          version: ${{ env.UV_VERSION }}
      - run: make deps-all
      - run: make test-all
```

## pr-e2e-tests.yml — PR E2E (`pull_request_target`)

Before generating this workflow, copy the shared actions from `quickstart-ci-testing` into `.github/actions/` using the same shallow-clone/diff/prompt process as nightly testing. Also copy repository-relative companion files referenced by those actions. The shared `setup-kind/action.yaml` invokes `scripts/ci/kind-with-registry.sh` from the consuming repository root, so a Kind workflow must include that script at the same path.

The shared `clone-quickstart` action runs `git clone --branch`, so `setup-and-deploy.ref` must be a branch or tag. Use `github.event.pull_request.head.ref` for PRs and `github.ref_name` for other events. Do not pass `github.event.pull_request.head.sha` or `github.sha`; the clone action cannot check out a bare commit SHA.

Use `make test-short-e2e` as the required PR E2E test target. Include `make test-short-eval` only when that target exists in the quickstart’s `Makefile`; if it does not exist, do not add it to the workflow.

Before generating `pr-e2e-tests.yml`, determine what the quickstart deploys and uses, then classify its runtime compatibility:

1. Inspect the architecture spec, deployment contract, Helm chart/subcharts, values, Make targets, scripts, and existing workflows.
2. Identify OpenShift-only requirements such as `Route`, `ImageStream`, `BuildConfig`, `DeploymentConfig`, `SecurityContextConstraints`, OpenShift AI custom resources, OpenShift operators, or external services reachable only through the target OpenShift cluster.
3. Determine whether the workload can run unchanged in Kind, including its container images, storage, service discovery, ingress, credentials, and external dependencies.
4. If the quickstart is OpenShift-only, use OpenShift with `use_kind: false` and the required cluster secrets. If the Makefile provides `build-all-images` and `push-all-images`, set `build_images: true`; the shared action provisions an ephemeral project registry, builds and pushes through `localhost:5001`, and deploys with the in-cluster registry address.
5. If the quickstart can run in both OpenShift and Kind, use Kind with `use_kind: true` and `build_images: true` for PR E2E because it is isolated and does not require cluster secrets.
6. If compatibility is ambiguous, ask the user instead of guessing.

Always include `permissions: {contents: read}` and use a PR-safe concurrency group based on `github.event.pull_request.number || github.run_id`. For `pull_request_target`, checkout the trusted base branch before invoking local actions; pass the PR head repository and branch to `setup-and-deploy`. If the workflow uses OpenShift credentials, restrict the job to same-repository pull requests and validate required secrets before deployment.

Set `persist-credentials: false` on the trusted-base checkout. For image builds,
explicitly pass `build_images_command` and `push_images_command` mapped to
existing Makefile targets rather than relying on action defaults. When
`run-quickstart-tests` uploads results, set `upload_retention_days: 30`.
Before reporting completion, verify every local action path and every
repository-relative helper referenced by the copied actions exists.

```yaml
name: Pull Request - Integration + End to End Tests

on:
  pull_request_target:
    types: [opened, synchronize, reopened]
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * *'

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.run_id }}
  cancel-in-progress: true

env:
  UV_VERSION: "0.8.9"
  PYTHON_VERSION: "3.12"
  E2E_NAMESPACE: test

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Validate LLM_API_TOKEN_EVAL secret
        env:
          LLM_API_TOKEN: ${{ secrets.LLM_API_TOKEN_EVAL }}
        run: test -n "$LLM_API_TOKEN"

      - uses: actions/checkout@v5
        with:
          ref: ${{ github.event.pull_request.base.ref || github.ref }}
          persist-credentials: false

      # Adapt or remove these toolchain steps to match the quickstart.
      - uses: astral-sh/setup-uv@v6
        with:
          version: ${{ env.UV_VERSION }}
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Setup and deploy
        uses: ./.github/actions/setup-and-deploy
        timeout-minutes: 15
        with:
          repo_url: https://github.com/${{ github.event.pull_request.head.repo.full_name || github.repository }}
          ref: ${{ github.event.pull_request.head.ref || github.ref_name }}
          namespace: ${{ env.E2E_NAMESPACE }}
          use_kind: true
          build_images: true
          kind_pre_deploy_command: "make helm-depend"
          deploy_command: "make helm-install-test"
          # Map these to the build and push targets present in this Makefile.
          build_images_command: "make build-all-images"
          push_images_command: "make push-all-images"
        env:
          LLM_API_TOKEN: ${{ secrets.LLM_API_TOKEN_INFERENCE }}

      - name: Run tests
        uses: ./.github/actions/run-quickstart-tests
        timeout-minutes: 30
        with:
          pre_test_command: "make sync-evaluations"
          test_command: "make test-short-e2e && make test-short-eval"
          upload_results: "evaluations/results"
          upload_retention_days: 30
        env:
          LLM_URL: ${{ vars.LLM_URL_EVAL }}
          LLM_API_TOKEN: ${{ secrets.LLM_API_TOKEN_EVAL }}

      - name: Cleanup
        if: always()
        uses: ./.github/actions/cleanup
        with:
          cleanup_command: "make helm-uninstall"
```

Adapt only the quickstart-specific target names and environment mapping. Inspect the resolved Make targets to discover required application variables and secrets, then map them at step scope. A value required by both deployment and testing must appear in both the `setup-and-deploy` and `run-quickstart-tests` `env:` blocks. Keep the shared action names and copy behavior aligned with nightly testing. The shared `run-quickstart-tests` action handles the working directory and artifact upload through its `test_working_dir` and `upload_results` inputs; use those inputs for nonstandard paths and do not add a separate manual artifact step unless the action cannot represent the required behavior.

## pr-branch-check.yml — dev → main

```yaml
name: Require dev branch for main PRs

on:
  pull_request:
    branches: [main]

jobs:
  validate-pr-branch:
    runs-on: ubuntu-latest
    steps:
      - run: |
          PR_SOURCE_BRANCH="${{ github.event.pull_request.head.ref }}"
          PR_SOURCE_REPO="${{ github.event.pull_request.head.repo.full_name }}"
          TARGET_REPO="${{ github.repository }}"
          if [ "${PR_SOURCE_REPO}" != "${TARGET_REPO}" ]; then
            echo "::error::PR must come from the same repository"
            exit 1
          fi
          if [ "${PR_SOURCE_BRANCH}" = "dev" ] || [[ "${PR_SOURCE_BRANCH}" =~ ^dev-[a-f0-9]+$ ]]; then
            echo "OK"
          else
            echo "::error::PR must come from dev or dev-<commit>"
            exit 1
          fi
```

## build-and-push.yaml

Use the skill-local [build-and-push workflow reference](./build-and-push-workflow.yaml). It combines push triggers for `main` and `dev` with manual dispatch, checks the repository owner and fork status, and calls the quickstart's Makefile build and push targets. Adapt the registry and toolchain steps to the quickstart.

## create-dev-to-main-pr.yml

Use the skill-local [promotion workflow reference](./create-dev-to-main-pr-workflow.yml), [release helper](./bump_release.py), and [release manifest](./bump-release.manifest.json). Copy the helper and manifest into `scripts/`, then adapt the manifest to every file that must carry the release version. The workflow verifies the target dev commit and `origin/main`, requires the dev version to be greater, creates `dev-<short-sha>`, and opens the promotion PR.

## create-dev-to-main-bump-pr.yml

Use the skill-local [dev version-bump workflow reference](./create-dev-to-main-bump-pr-workflow.yml) with the same `scripts/bump_release.py` helper and `scripts/bump-release.manifest.json`. It is manually dispatched, reads the current release version on `dev`, defaults to the next patch version (or accepts a requested higher version), updates the manifest paths, verifies alignment, and opens or updates a PR into `dev`. The separate `create-dev-to-main-pr.yml` workflow promotes the resulting dev changes to `main`.

## Evaluations artifact tarball (reusable snippet)

```yaml
- name: Create evaluations tarball
  if: always()
  run: |
    if [ -d "evaluations/results" ]; then
      tar -czf evaluations-results-${{ github.run_id }}.tar.gz -C evaluations results/
    else
      mkdir -p evaluations/results
      echo "No evaluation results" > evaluations/results/README.txt
      tar -czf evaluations-results-${{ github.run_id }}.tar.gz -C evaluations results/
    fi
```

## Path filters (monorepo)

For smaller repos, add `paths` filters like `ai-supply-chain-agent`:

```yaml
on:
  pull_request:
    paths:
      - "packages/**"
      - "deploy/**"
      - ".github/**"
```

Use when PR noise from docs-only changes should not run Kind E2E.
