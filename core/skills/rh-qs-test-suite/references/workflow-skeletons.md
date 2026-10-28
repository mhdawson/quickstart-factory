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

## pr-e2e-tests.yml — Kind + evals (`pull_request_target`)

```yaml
name: Pull Request - Integration + End to End Tests

on:
  pull_request_target:
    types: [opened, synchronize, reopened]
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * *'

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
          ref: ${{ github.event.pull_request.head.sha }}

      - uses: ./.github/actions/prepare-runner
        with:
          swap-storage: 'false'

      - uses: astral-sh/setup-uv@v6
        with:
          version: ${{ env.UV_VERSION }}
          python-version: ${{ env.PYTHON_VERSION }}

      - run: |
          make oc
          echo "$GITHUB_WORKSPACE/bin" >> $GITHUB_PATH

      - uses: ./.github/actions/kind
        with:
          namespace: ${{ env.E2E_NAMESPACE }}
          llm: ${{ vars.LLM_INFERENCE }}
          llm_id: ${{ vars.LLM_ID_INFERENCE }}
          llm_url: ${{ vars.LLM_URL_INFERENCE }}
        env:
          LLM_API_TOKEN: ${{ secrets.LLM_API_TOKEN_INFERENCE }}

      - run: kubectl config set-context --current --namespace=${{ env.E2E_NAMESPACE }}

      - run: make test-integration NAMESPACE=${{ env.E2E_NAMESPACE }}

      - run: make sync-evaluations

      - run: make test-short-eval
        if: always()
        env:
          LLM_URL: ${{ vars.LLM_URL_EVAL }}
          LLM_API_TOKEN: ${{ secrets.LLM_API_TOKEN_EVAL }}

      - uses: ./.github/actions/inspect
        if: failure()
        with:
          artifactPrefix: <slug>

      - name: Upload evaluations artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: evaluations-results-${{ github.run_id }}
          path: evaluations-results-${{ github.run_id }}.tar.gz
          retention-days: 30
```

Add tarball creation step before upload (see `pr-e2e-tests.yml` in it-self-service-agent).

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

## create-dev-to-main-bump-r.yml

Use the skill-local [dev version-bump workflow reference](./create-dev-to-main-bump-r-workflow.yml) with the same `scripts/bump_release.py` helper and `scripts/bump-release.manifest.json`. It is manually dispatched, reads the current release version on `dev`, defaults to the next patch version (or accepts a requested higher version), updates the manifest paths, verifies alignment, and opens or updates a PR into `dev`. The separate `create-dev-to-main-pr.yml` workflow promotes the resulting dev changes to `main`.

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
