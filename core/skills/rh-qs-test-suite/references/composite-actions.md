# Composite actions

Pattern from `it-self-service-agent/.github/actions/`. Prefer composite actions over 50-step workflows so E2E and pip-install PR jobs stay identical.

**These are PR-time actions only.** Nightly testing uses a separate action set copied from `quickstart-ci-testing` (`setup-and-deploy`, `clone-quickstart`, `cleanup`, `run-quickstart-tests`, `run-tests`, `prepare-runner`, `setup-openshift`) — see [nightly-actions-catalog.md](./nightly-actions-catalog.md) and `subagents/nightly-tests-prompt.md`. Both sets live under `.github/actions/` at once without conflict; they back different jobs (ephemeral Kind for PRs vs. real-cluster deploy for nightly). Note the naming collision on `prepare-runner` — the two repos each ship their own version of that action; keep them namespaced correctly and don't let the nightly copy step overwrite the PR one or vice versa.

## prepare-runner

**Path:** `.github/actions/prepare-runner/action.yaml`

**Purpose:** Kind and image builds need disk; log memory before long runs.

```yaml
inputs:
  swap-storage:
    description: Enable swap via free-disk-space action
    required: false
    default: 'false'
runs:
  using: composite
  steps:
    - uses: jlumbroso/free-disk-space@v1.3.1
      with:
        android: true
        dotnet: true
        haskell: true
        large-packages: false
        docker-images: false
        swap-storage: ${{ inputs.swap-storage }}
        tool-cache: false
    - shell: bash
      run: |
        free -h
        swapon --show || true
        df -h
```

**Usage in workflow:**

```yaml
- uses: ./.github/actions/prepare-runner
  with:
    swap-storage: 'false'
```

## kind

**Path:** `.github/actions/kind/action.yaml`

**Purpose:** One-shot local OpenShift-like path: Kind + registry → build images → helm install test release.

**Required inputs:** `llm`, `llm_id`, `llm_url` (from repository variables in caller workflow).

**Optional inputs:**

| Input | Default | Meaning |
|-------|---------|---------|
| `namespace` | `test` | Target namespace |
| `replica_count` | `1` | Scale for HA integration tests |
| `use_pip_install` | `false` | `make build-all-images` with pip path vs uv |

**Typical steps inside action:**

1. `go install sigs.k8s.io/kind@v0.30.0`
2. `bash ./scripts/ci/kind-with-registry.sh`
3. `make helm-depend`
4. `make build-all-images REGISTRY=localhost:5001 USE_PIP_INSTALL=${{ inputs.use_pip_install }}`
5. `make push-all-images REGISTRY=localhost:5001 PUSH_EXTRA_AGRS="--tls-verify=false"`
6. `make namespace NAMESPACE=...`
7. `make helm-install-test` with `LLM_*` and Kind-specific `--set` overrides

**Env from workflow:** pass `LLM_API_TOKEN: ${{ secrets.LLM_API_TOKEN_INFERENCE }}` on the step that runs helm install.

**Supply-chain variant:** `ai-supply-chain-agent/.github/actions/kind/action.yaml` adds Podman install, `helm-install-kind`, optional `/healthz` smoke, and `skip_image_build` — use when the chart layout matches that repo.

## inspect

**Path:** `.github/actions/inspect/action.yml`

**Purpose:** Run only `if: failure()` after E2E to collect debugging artifacts.

```yaml
inputs:
  artifactPrefix:
    required: true
```

Wire to `kubectl get all`, events, logs, or `oc adm inspect` when ready. A no-op stub is acceptable until the quickstart has namespaces to dump.

## scripts/ci/kind-with-registry.sh

Not a composite action but required by `kind`:

- Local registry on port `5001` (`kind-registry` container)
- Kind cluster with containerd registry config
- Must work with **Podman** when Docker is absent (see it-self-service-agent script header)

Copy from `it-self-service-agent/scripts/ci/kind-with-registry.sh` and adjust registry port / cluster name if the Makefile expects different values.
