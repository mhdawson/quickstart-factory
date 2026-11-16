REGISTRY ?= quay.io/rh-ai-quickstart
VERSION ?=
IMAGE_NAME := qs-test-quickstart

.PHONY: image-version build-images publish-images test-all

image-version:
	@echo 2.4.1

build-images:
	@echo "Build all quickstart images with VERSION=$(VERSION) and REGISTRY=$(REGISTRY)"

publish-images:
	@echo "Publish all quickstart images with VERSION=$(VERSION) and REGISTRY=$(REGISTRY)"

test-all:
	@echo "Tests passed"
