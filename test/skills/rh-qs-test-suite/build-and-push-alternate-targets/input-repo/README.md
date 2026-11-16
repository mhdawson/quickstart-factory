# Alternate Make target quickstart

This quickstart publishes all of its images to `quay.io/rh-ai-quickstart`.
Its image repository is `quay.io/rh-ai-quickstart/qs-test-quickstart`.

- `make image-version` prints the release version used for image tags.
- `make build-images VERSION=<tag> REGISTRY=<registry>` builds every image.
- `make publish-images VERSION=<tag> REGISTRY=<registry>` publishes every image.
- The Makefile does not define `version`, `build-all-images`, or `push-all-images`.
- These targets use the hosted runner's container tooling directly and do not
  require Python or `uv`.

The hosted image-publishing workflow should use the existing targets and pass
the `VERSION` and `REGISTRY` variables as documented here.
