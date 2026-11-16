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
- On `main`, publish the release version, a version-plus-commit tag, and
  `latest`. On `dev`, publish `<version>-dev`, a version-plus-commit tag, and
  `dev`.
- `make build-all-images` builds every quickstart image.
- `make push-all-images` publishes the built images using `REGISTRY` and `VERSION`.
- `make build-push-images-needed` exits 0 when image build/push is needed and nonzero otherwise.
- The image build uses Python 3.11 and `uv` 0.5.24.
- GitHub Actions must read `QUAY_USERNAME` and `QUAY_PASSWORD` from repository secrets.
