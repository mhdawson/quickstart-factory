PYTHON_VERSION ?= 3.11
UV_VERSION ?= 0.12.11
BASE_VERSION := 0.1.0

.PHONY: check-uv-version check-lockfiles deps-all lint test-all helm-export-validate-demo version

check-uv-version:
	@uv --version | grep -q "$(UV_VERSION)"

check-lockfiles:
	uv lock --check

deps-all:
	uv sync --python $(PYTHON_VERSION) --all-groups --frozen

lint:
	uv run --frozen ruff check .

test-all:
	uv run --frozen pytest

helm-export-validate-demo:
	helm template qs-test-quickstart helm > /tmp/qs-test-quickstart.yaml
	kubeconform -strict -summary /tmp/qs-test-quickstart.yaml

version:
	@echo $(BASE_VERSION)
