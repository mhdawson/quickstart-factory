# GitHub secrets and variables

Configure at **organization** or **repository** level before enabling workflows that call external LLMs or Quay.

## Repository secrets

| Secret | Used in | Purpose |
|--------|---------|---------|
| `LLM_API_TOKEN_EVAL` | Nightly evals | Evaluation / judge model API |
| `LLM_API_TOKEN_INFERENCE` | Nightly deploy/tests | Model serving the app uses under test |
| `LLM_API_TOKEN_EVAL_70B` | Nightly long / prod evals | Larger model for long conversation tests |
| `QUAY_USERNAME` | `build-and-push` | Registry login |
| `QUAY_PASSWORD` | `build-and-push` | Registry login |
| `PROD_TOKEN` | Nightly prod | `oc login` token |
| `PROD_SERVER` | Nightly prod | OpenShift API URL |

**Validation pattern** (first step in job):

```yaml
- name: Validate LLM_API_TOKEN_EVAL secret
  shell: bash
  env:
    LLM_API_TOKEN: ${{ secrets.LLM_API_TOKEN_EVAL }}
  run: |
    if [ -z "${LLM_API_TOKEN}" ]; then
      echo "LLM_API_TOKEN_EVAL secret is missing or empty."
      exit 1
    fi
```

Domain-specific secrets (e.g. ServiceNow in it-self-service-agent) are added only when the PRD requires them—document each in the design doc.

## Repository variables

| Variable | Typical use |
|----------|-------------|
| `LLM_URL_EVAL` | Eval harness endpoint |
| `LLM_URL_INFERENCE` | Inference endpoint for deployed chart |
| `LLM_ID_INFERENCE` | Model ID passed to Helm |
| `LLM_INFERENCE` | Display / chart value for LLM selection |
| `LLM_URL_EVAL_70B` | Nightly long eval endpoint |

Pass to Make/Helm via workflow `env:`:

```yaml
env:
  LLM_URL: ${{ vars.LLM_URL_EVAL }}
  LLM_API_TOKEN: ${{ secrets.LLM_API_TOKEN_EVAL }}
```

## Promotion / automation

The `create-dev-to-main-pr` and `create-dev-to-main-bump-pr` workflows use the
built-in `GITHUB_TOKEN`. They declare `contents: write` and `pull-requests: write`
permissions and require no additional repository secrets.

Events created with `GITHUB_TOKEN` do not trigger new workflow runs, except for
`workflow_dispatch` and `repository_dispatch` events.

## Security rules

- Do not echo secrets in logs; use `env:` on steps, not inline `${{ secrets.* }}` in `run:` strings when avoidable.
- PR E2E workflows use `pull_request` and must not reference repository secrets or variables. Put tests that need repository configuration in nightly workflows.
- Mock tokens are acceptable only for **static** validation (e.g. `HF_TOKEN: mock_hf_token_for_ci` for helm template/kubeconform).

## Quickstart checklist

```
- [ ] LLM eval required? → LLM_API_TOKEN_EVAL + LLM_URL_EVAL
- [ ] Kind E2E with real inference? → LLM_API_TOKEN_INFERENCE + LLM_*_INFERENCE vars
- [ ] Push to Quay? → QUAY_* + workflow guard repository_owner
- [ ] Prod nightly? → PROD_* + dedicated namespace + uninstall step
```
