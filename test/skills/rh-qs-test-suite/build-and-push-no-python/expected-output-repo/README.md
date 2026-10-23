# qs-test-quickstart

## Image publishing

- Publish images to `quay.io/rh-ai-quickstart`.
- Publish automatically on every push to the `main` and `dev` branches of the
  `rh-ai-quickstart` organization, including pushes caused by merged PRs. Do
  not skip a push because the release version is unchanged.
- Never publish images from a forked repository.
- Allow a manual workflow dispatch to select either `main` or `dev` and
  build and publish the version returned by `make version`.
- `make version` prints the release version used for image tags.
- `make build-all-images` and `make push-all-images` use the hosted runner's
  container tooling directly. They do not use Python, `uv`, or another
  application runtime.
- GitHub Actions must read `QUAY_USERNAME` and `QUAY_PASSWORD` from repository secrets.
