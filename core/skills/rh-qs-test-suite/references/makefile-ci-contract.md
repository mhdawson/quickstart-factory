# Makefile CI contract

GitHub Actions should call **Make targets**, not duplicate dependency-install or
Helm-render logic. For uv-based quickstarts, align Makefile `UV_VERSION` with
workflow `env.UV_VERSION` (it-self-service-agent uses `0.8.9` as a canonical
example). For other dependency managers, follow the repository's own setup and
version pins.

The tables below describe common targets; they are not permission to assume a
quickstart uses uv or implements every target. Inspect its `Makefile`, dependency
manifests, and existing workflows before generating CI. Call only targets that
exist or that the requested change adds. Preserve existing names and defaults.
For a pip/requirements quickstart, keep its existing requirements-check target
(for example, `check-deps`), use Python setup, and omit uv setup and uv-specific
checks unless the repository actually uses uv and defines those checks. Make
`deps-all` depend on that requirements check. Helm render targets should retain
the Makefile's namespace default, while CI passes its own namespace as an
override.

## Version and dependency hygiene

| Target | CI usage |
|--------|----------|
| `check-uv-version` | Fail if runner uv ≠ Makefile `UV_VERSION` |
| `check-lockfiles` | `uv lock` drift detection |
| `check-requirements` | `requirements.txt` in sync with lockfiles (if pip path used) |
| `deps-all` | Install all workspace packages for lint/test |

## Quality and unit tests

| Target | CI usage |
|--------|----------|
| `lint` / per-linter targets | flake8, black, isort, ruff—match scaffold choices |
| `lint-mypy-per-directory` | Optional; mypy per package |
| `check-logging` | Custom logging policy (if adopted) |
| `test-all` / `test` | pytest across packages |

## Helm validation (no cluster)

| Target | CI usage |
|--------|----------|
| `helm-export-validate-demo` | Render manifests + kubeconform; env `NAMESPACE`, mock `HF_TOKEN` |
| `helm-depend` | `helm dependency build` before Kind install |

## Kind / E2E

| Target | CI usage |
|--------|----------|
| `oc` | Install `oc` CLI into `$GITHUB_WORKSPACE/bin` |
| `build-all-images` | `REGISTRY=localhost:5001`, optional `USE_PIP_INSTALL=true` |
| `push-all-images` | `PUSH_EXTRA_AGRS="--tls-verify=false"` for local registry |
| `namespace` | `NAMESPACE=<test>` |
| `helm-install-test` | Chart install with `LLM`, `LLM_ID`, `LLM_URL`, `LLM_API_TOKEN`, Kind-specific `--set` |
| `helm-uninstall` | Cleanup prod/nightly namespaces |

## Integration tests (name per quickstart)

Examples from it-self-service-agent—replace with design-specific targets:

| Target | Purpose |
|--------|---------|
| `test-session-serialization-integration` | Session store behavior |
| `test-session-reclaim-integration` | Reclaim path |
| `test-short-resp-integration-request-mgr` | Short LLM eval on Request Manager |
| `test-long-resp-integration-request-mgr` | Nightly long eval |

## Evaluations

| Target | CI usage |
|--------|----------|
| `sync-evaluations` | Install eval harness deps (separate uv project or extra) |
| `check-known-bad-conversations` | Regression gate without full deploy |

## Release / versioning

| Target | CI usage |
|--------|----------|
| `version` | Emit semver for image tags (`build-and-push`) |
| `BASE_VERSION` variable | Authoritative release version consumed by `scripts/bump_release.py --verify` |
| `helm-install-prod` | Nightly against real cluster |

## Nightly contract (canonical names)

`subagents/nightly-tests-prompt.md` expects the canonical names `rh-qs-deploy`/`rh-qs-scaffold` already establish: `deploy` (install), `test`, `undeploy` (uninstall), `verify-deploy` (smoke test). Any quickstart that went through `rh-qs-deploy` should already have all three. For older quickstarts missing one, the subagent searches for an equivalent existing target (e.g. `install-full`, `helm-install-prod`, `e2e-ui`, `helm-uninstall`) rather than renaming anything — it uses whatever real name it finds and records the mapping in `.qs-factory/pipeline/nightly-tests-manifest.yaml`.

## Environment variables workflows pass

| Variable | Set by |
|----------|--------|
| `NAMESPACE` | Workflow `env.E2E_NAMESPACE` or job input |
| `REGISTRY` | `localhost:5001` for Kind; `quay.io/rh-ai-quickstart` for push |
| `VERSION` | `steps.version.outputs.version` on prod nightlies |
| `LLM_URL`, `LLM_API_TOKEN`, `LLM_ID`, `LLM` | secrets + vars |

## Monorepo quickstart (packages/*) mapping

| it-self-service-agent style | Quickstart factory layout |
|----------------------------|---------------------------|
| Multi-service `build-all-images` | `make build` or per-package Containerfile targets |
| `helm-install-test` | Kind E2E |
| `verify-deploy` | Post-install smoke — gate before `rh-qs-document` |
| `test-all` | `make test` → turbo/pytest/vitest per design |

Keep target names stable once branch protection references job names tied to those makes.
