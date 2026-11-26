# Reasoning Guardrails for rh-qs-test-suite

Use these concern areas while planning CI changes. They guide analysis rather than act as a mechanical checklist; skip concerns that do not apply to the requested workflow set.

## How to Use

1. Analyze the request and repository evidence freely.
2. Periodically consider the relevant concerns below.
3. Resolve unknowns from the Makefile, architecture spec, existing workflows, or user input.
4. Keep unresolved assumptions visible in the spec instead of turning them into requirements.

## Concern Areas

### 1. Scope and workflow selection

- Does the request call for the full CI profile, nightly testing only, or image publishing only?
- Does the architecture testing strategy justify each proposed workflow?
- Are optional release workflows actually part of the quickstart's branch model?

Look at the user's request, architecture spec, existing workflow files, and Git branch metadata.

### 2. Makefile as the source of truth

- Do all workflow `make` calls map to existing targets or additions described in the spec?
- Does dependency setup match the actual package manager and pinned versions?
- Are current target names and namespace defaults preserved?

Look at Makefile target bodies, dependency manifests, and current CI workflows.

### 3. Fork and secret safety

- Can a `pull_request` workflow run untrusted code with repository secrets?
- Are secret-dependent tests scheduled only in workflows with the intended trust boundary?
- Are detected secret and variable requirements grounded in repository evidence?

Look at event triggers, `secrets.*` and `vars.*` references, Makefile variables, and Helm defaults.

### 4. Kind and OpenShift fit

- Can the selected E2E path run on Kind, or does it depend on OpenShift-only APIs or cluster permissions?
- Are shared actions accompanied by every repository-relative support file they use?
- Are cluster-admin needs described accurately for nightly provisioning?

Look at charts, action files, scripts, and the deploy/test targets.

### 5. Existing repository state

- Will a generated file overwrite a user-maintained workflow or action?
- Are existing shared actions identical to the canonical source?
- Does the change fit the quickstart's existing branch and release conventions?

Inspect current files before proposing replacements. Preserve existing differences unless the spec calls for an update.

## Additional Concerns

### Focused image publishing request

The standalone generator may modify only `.github/workflows/build-and-push.yaml`. Do not expand the scope to make unrelated targets or workflows fit.

### Nightly workflow request

Nightly target environment requirements are quickstart-specific. Discover them from repository evidence; do not reuse another quickstart's secret list.

## Dynamic Reasoning Example

The request asks for Kind-based PR E2E, but the Makefile's install target deploys an OpenShift-only resource. The architecture spec describes those tests as nightly production checks.

That evidence means a Kind workflow is not a safe fit. Record the mismatch in the spec, keep those tests in nightly testing, and ask for guidance if the request still requires PR E2E.

## When to Stop Checking

Once each selected workflow has a repository-backed trigger, target mapping, trust boundary, and output path, proceed. Do not force release or cluster checks into minimal profiles.

## Self-Check Before Implementation

- Does the refined spec list every file and target to be changed?
- Are secrets excluded from untrusted PR workflows?
- Can the requested E2E workflow run on its stated platform?
- Are ambiguities and GitHub-side follow-ups clearly recorded?
