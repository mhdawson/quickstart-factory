UV_VERSION := 0.5.24
PYTHON_VERSION := 3.11
REGISTRY := quay.io/rh-ai-quickstart
IMAGE_NAME := qs-test-quickstart

.PHONY: version build-all-images push-all-images build-push-images-needed

version:
	@echo 1.2.3

build-all-images:
	@echo "Fixture build target; does not invoke a container engine."

push-all-images:
	@echo "Fixture push target; does not access a registry."

build-push-images-needed:
	@test "$${BUILD_PUSH_IMAGES_NEEDED:-0}" = "1"
