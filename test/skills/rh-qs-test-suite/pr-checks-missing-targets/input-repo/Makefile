.PHONY: check-deps lint test-all

check-deps:
	@test -f requirements.txt
	@test -f requirements-dev.txt

lint:
	python -m ruff check .

test-all:
	python -m pytest
