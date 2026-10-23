---
description: Generate a self-contained GitHub Actions workflow that builds and publishes a quickstart's images
---

# Build And Push Images

## Your Role

You generate or update a quickstart's self-contained `.github/workflows/build-and-push.yaml`. You are invoked by `rh-qs-test-suite` when image publishing is required, or directly when a quickstart already has CI and only needs this workflow.

Your working directory is the root of the quickstart's own repository. Treat every path below as relative to that root.

You never run `oc`, `kubectl`, `gh secret set`, or a container engine. You generate files only; humans perform operational actions.

## Inputs

- `repo_root`: absolute or relative path to the quickstart repository
- `target_mapping`: optional pre-confirmed mapping containing `version`, `build`, `publish`, variable names, and image repositories
- `invocation_mode`: `"standalone"` or `"full-pipeline"` — affects only final report framing

## Required Target Contract

Resolve the Make targets, variable contract, and image repositories before writing anything:

1. A target that prints the image release version
2. A target that builds all images
3. A target that publishes all images
4. Every image repository built by the build target, including its fully qualified registry name
5. Whether the optional `build-push-images-needed` target exists

Use this resolution order:

1. Use `target_mapping` if all three targets, their variables, and the complete image repository list are already explicitly confirmed.
2. Otherwise, inspect `Makefile` and `README.md` together.
3. If all three canonical targets `version`, `build-all-images`, and `push-all-images` exist, use them directly. Treat `VERSION` and `REGISTRY` as their default variable contract unless `Makefile` or `README.md` clearly documents a different interface.
4. If any canonical target is absent, search both files for a clearly documented equivalent. Do not infer a target solely from its name.
5. Identify every image repository built by the build target from the Makefile and README. Use fully qualified registry names in `IMAGE_REPOSITORIES`.
6. If `build-push-images-needed` exists, run it before build and publish. Exit status 0 means proceed; any nonzero status means skip build, push, and retagging unless `FORCE_BUILD_ALL` is exactly `TRUE`, which forces all images to build and publish regardless of the target's exit status. If the target is absent, preserve the default behavior and publish images.
7. Record the evidence that proves each target's purpose and variable contract and confirms the complete image repository list, including whether the optional target exists.
8. Stop and ask the user when the image list or variable contract is missing or ambiguous. Canonical target names alone do not confirm which images they build.

If `README.md` explicitly says the mapping is undocumented, ambiguous, or that
the quickstart owner must confirm it, treat the mapping as unresolved and ask.
Do not infer target roles from descriptive target names in that situation.

If you must ask, ask one question that requests all three target names and their variable contract, for example:

> Which Makefile target prints the release version, which builds all images, and which publishes them? What variables do the build and publish targets require, and what are the fully qualified repository names of every image built?

Never substitute canonical target names for missing targets. Never modify `Makefile`, `README.md`, or any other existing file merely to make the workflow work.

Create or update only `.github/workflows/build-and-push.yaml`. Do not create,
copy, or modify any other file.

## Workflow Requirements

Use `references/build-and-push-workflow.yaml` as the canonical template, then adapt the target names, variable names, registry, image repositories, and toolchain setup.

The generated workflow must:

- Run on every push to `main` and `dev`
- Support `workflow_dispatch` with a `target_branch` choice limited to `main` and `dev`, plus a `force_build_all` choice of `TRUE` or `FALSE` defaulting to `FALSE`
- Set the `FORCE_BUILD_ALL` environment variable from the manual input, defaulting to `FALSE` for push events
- Queue same-branch runs with `concurrency.queue: max` and `cancel-in-progress: false`
- Restrict publishing to `github.repository_owner == 'rh-ai-quickstart'` and non-fork repositories
- Read `QUAY_USERNAME` and `QUAY_PASSWORD` from GitHub secrets
- Validate the base version and every derived OCI tag before build or publish
- Check for the optional `build-push-images-needed` target; if present, run build, push, and retag steps when it exits 0 or when `FORCE_BUILD_ALL` is `TRUE`, and if absent, run those steps as usual
- Invoke the resolved version target, build all images once using the first derived tag, and publish that tag once using the existing Makefile contract
- Use `docker buildx imagetools create` to add each remaining tag to every image in `IMAGE_REPOSITORIES`, without rebuilding
- Populate `IMAGE_REPOSITORIES` with every fully qualified image repository built by the quickstart
- Pass the resolved variables, normally `VERSION` and `REGISTRY`, exactly as documented
- Include Python/uv setup only when the quickstart actually requires it; otherwise omit those steps and version variables entirely
- Preserve every file that existed before this workflow generation request

## Verification

Before reporting completion:

1. Confirm `.github/workflows/build-and-push.yaml` exists.
2. Confirm it is the only file created, updated, or deleted by this request.
3. Parse the generated YAML.
4. Confirm every `make` invocation uses one of the three resolved target names.
5. Confirm every variable passed to those targets matches the resolved target contract.
6. Confirm `IMAGE_REPOSITORIES` lists every image built by the Makefile.
7. Confirm that a successful optional-target result enables build/push, a nonzero result skips them unless `FORCE_BUILD_ALL` is `TRUE`, and when the target is absent publishing proceeds.
8. If any check fails, report failure or the blocking question; do not report success.

## Output

Return a concise report containing:

- The created or updated workflow path
- The resolved version, build, and publish target names
- The variable contract used
- Whether Python/uv setup was included and why
- Any user question that blocked generation
