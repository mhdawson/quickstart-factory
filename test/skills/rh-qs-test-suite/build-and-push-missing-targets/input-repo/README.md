# Quickstart with undocumented image publishing targets

This quickstart publishes all images to `quay.io/rh-ai-quickstart` on pushes to
`main` and `dev`, and supports manual dispatch for either branch. It uses
`QUAY_USERNAME` and `QUAY_PASSWORD` repository secrets and does not require
Python or `uv` on the hosted runner.

The Makefile contains three legacy image-release targets, but their roles and
variable contract are not documented here. Ask the quickstart owner to confirm
which target prints the image release version, which builds all images, and
which publishes them before using those targets in CI.
