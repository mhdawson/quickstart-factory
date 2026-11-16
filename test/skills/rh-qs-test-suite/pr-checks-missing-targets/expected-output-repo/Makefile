.PHONY: check-deps deps-all lint test-all helm-export-validate-demo

NAMESPACE ?= default

check-deps:
	@test -f requirements.txt
	@test -f requirements-dev.txt

deps-all: check-deps
	python -m pip install -r requirements.txt -r requirements-dev.txt

lint:
	python -m ruff check .

test-all:
	python -m pytest

helm-export-validate-demo:
	helm template qs-test-quickstart ./helm --namespace "$(NAMESPACE)" | kubeconform -strict
