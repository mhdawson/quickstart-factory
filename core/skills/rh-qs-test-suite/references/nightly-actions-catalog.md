# Nightly testing: quickstart-ci-testing actions catalog

Used by `subagents/nightly-tests-prompt.md`. Source repo: `rh-ai-quickstart/quickstart-ci-testing`. Reference workflows: `rh-ai-quickstart/ai-supply-chain-agent` — `test-ai-supply-chain-agent.yml`, `nightly-main.yml`, `nightly-development.yml`.

## Why copy instead of reference remotely

`quickstart-ci-testing`'s own README states composite actions cannot be referenced cross-repo (`uses: org/repo/.github/actions/x@ref` doesn't work for composite actions the way it does for whole reusable workflows), so the actions must be copied into `.github/actions/` in the consuming repo. There is no versioning/tagging scheme upstream — copying is a straight directory sync, re-checked (diff + prompt) on every run of the nightly subagent in case the source has changed.

This action set is separate from the `prepare-runner`/`kind`/`inspect` actions `rh-qs-test-suite` may already have added for PR-time Kind E2E (see `composite-actions.md`) — both sets can coexist under `.github/actions/` without conflict; they serve different jobs (ephemeral PR-time Kind vs. real-cluster nightly).

## Actions inventory

| Action | Purpose | Key inputs |
|--------|---------|------------|
| `setup-and-deploy` | Prepares the runner, clones the quickstart at a given ref, deploys it to OpenShift (or Kind, if `use_kind: true`) | `repo_url`, `ref`, `namespace` (default `quickstart-ci-project-1` — override per quickstart), `deploy_command` (required), `setup_commands`, `use_kind`, `build_images`, `build_images_command`, `push_images_command` |
| `clone-quickstart` | Clones the target repo at a ref (called internally by `setup-and-deploy`) | `repo_url`, `ref`, `submodules` |
| `setup-openshift` | `oc` login/context setup for the OpenShift path (called internally by `setup-and-deploy`) | — |
| `prepare-runner` | Frees runner disk space before a deploy/build | `swap-storage` |
| `run-quickstart-tests` | Runs the test command in the cloned quickstart directory, uploads results | `test_command` (required), `test_working_dir` (default `./quickstart`), `pre_test_command`, `upload_results`, `upload_retention_days` (default 2) |
| `run-tests` | Lower-level test execution step called internally by `run-quickstart-tests` | — |
| `cleanup` | Tears down the deployment | `cleanup_command` (required), `working_dir` (default `./quickstart`) |

`setup-and-deploy` validates preconditions before running: `build_images` requires `use_kind: true`; when not using Kind, it errors early if `PROD_TOKEN`/`PROD_SERVER` secrets are missing.

## Reusable test workflow skeleton

`.github/workflows/test-<slug>.yml`:

```yaml
name: Test <slug>

on:
  workflow_call:
    inputs:
      branch:
        required: true
        type: string
  workflow_dispatch:
    inputs:
      branch:
        description: Branch to deploy and test
        default: main
        type: string

concurrency:
  group: <slug>-ci-testing
  cancel-in-progress: false

jobs:
  test:
    name: <slug> (${{ inputs.branch }})
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      # Toolchain setup steps, derived from this repo's own README/Makefile —
      # e.g. astral-sh/setup-uv@v6 pinned to the Makefile's UV_VERSION, only
      # if this repo actually uses uv. See "Step 2: Detect toolchain/runtime
      # setup requirements" in subagents/nightly-tests-prompt.md.

      - name: Setup and deploy
        uses: ./.github/actions/setup-and-deploy
        timeout-minutes: 15
        with:
          repo_url: https://github.com/${{ github.repository }}
          ref: ${{ inputs.branch }}
          namespace: <slug>-ci-project-1
          deploy_command: "make deploy"
        env:
          PROD_TOKEN: ${{ secrets.PROD_TOKEN }}
          PROD_SERVER: ${{ secrets.PROD_SERVER }}

      - name: Run tests
        uses: ./.github/actions/run-quickstart-tests
        timeout-minutes: 30
        with:
          test_command: "make test"
          upload_results: "test-results"

      - name: Cleanup
        if: always()
        uses: ./.github/actions/cleanup
        with:
          cleanup_command: "make undeploy"
```

## Nightly caller skeleton

`.github/workflows/nightly-main.yml` (repeat for the dev branch with a later cron and `branch: <dev-branch>`):

```yaml
name: Nightly - <slug> (main)

on:
  workflow_dispatch:
  schedule:
    - cron: "0 5 * * *"

jobs:
  test:
    uses: ./.github/workflows/test-<slug>.yml
    with:
      branch: main
    secrets: inherit
```

Stagger cron times across `nightly-main.yml`/`nightly-<dev>.yml` by at least an hour — they share a concurrency group and namespace, so overlapping schedules just queue rather than run in parallel, but staggering keeps failures easy to attribute to one branch.

## Namespace/ServiceAccount provisioning script

`scripts/ci/setup-nightly-namespace.sh` — run by a human against the target cluster, never by an agent:

```bash
#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-<slug>-ci-project-1}"
SA_NAME="${SA_NAME:-<slug>-ci-1}"
TOKEN_DURATION="${TOKEN_DURATION:-8760h}"

oc create namespace "$NAMESPACE"
oc create sa "$SA_NAME" -n "$NAMESPACE"
oc adm policy add-role-to-user admin \
  "system:serviceaccount:${NAMESPACE}:${SA_NAME}" \
  -n "$NAMESPACE"

echo
echo "PROD_SERVER: $(oc whoami --show-server)"
echo "PROD_TOKEN:"
oc create token "$SA_NAME" -n "$NAMESPACE" --duration="$TOKEN_DURATION"

echo
echo "Set the two values above as repository secrets PROD_SERVER and PROD_TOKEN"
echo "(Settings -> Secrets and variables -> Actions) before enabling the nightly workflows."
```

This grants **namespace-scoped** `admin` only — not cluster-admin. If the quickstart's chart needs cluster-scoped resources (see the cluster-admin check in `nightly-tests-prompt.md`), this script alone is not sufficient and the nightly subagent's report will say so.

## Toolchain setup — no fixed list either

Like secrets/variables, the runner setup steps before `setup-and-deploy` are not templated from `ai-supply-chain-agent` (its `astral-sh/setup-uv@v6` step is specific to that quickstart being `uv`-based). Each quickstart's `nightly-tests-prompt.md` run first identifies the selected job container or runner image, then derives only missing or version-specific setup from that repo's `README.md`, `Makefile`, lockfiles, and existing PR workflows. A Makefile command alone is not grounds to install a tool: GitHub-hosted `ubuntu-latest`, for example, already provides Helm. See "Step 2: Detect toolchain/runtime setup requirements" in `nightly-tests-prompt.md`.

## Required secrets/variables — no fixed list

`PROD_TOKEN` and `PROD_SERVER` are the only two names ever assumed, because they're structural to `setup-and-deploy`'s cluster-access mechanism, independent of any quickstart's own app. Every other secret/variable a given quickstart's `deploy`/`test` targets need must be discovered per-repo (see "Step 2: Detect required secrets and variables" in `nightly-tests-prompt.md`) — never hardcoded here or assumed from another quickstart's example (e.g. `ai-supply-chain-agent`'s own `MODEL_ID`/`MODEL_URL`/`API_KEY` are specific to that quickstart, not a template to reuse elsewhere).
