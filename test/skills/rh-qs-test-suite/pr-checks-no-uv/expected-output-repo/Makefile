PYTHON_VERSION ?= 3.11

.PHONY: check-requirements deps-all lint test-all helm-export-validate-demo

check-requirements:
	@test -f requirements.txt
	@test -f requirements-dev.txt

deps-all:
	python -m pip install -r requirements.txt -r requirements-dev.txt

lint:
	python -m ruff check .

test-all:
	python -m pytest

helm-export-validate-demo:
	helm template qs-test-quickstart helm > /tmp/qs-test-quickstart.yaml
	kubeconform -strict -summary /tmp/qs-test-quickstart.yaml
