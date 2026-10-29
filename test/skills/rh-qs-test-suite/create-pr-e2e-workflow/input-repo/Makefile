NAMESPACE ?= test
REGISTRY ?= localhost:5001
MODEL_ID ?=
MODEL_URL ?=
MODEL_API_KEY ?=
UV_VERSION := 0.5.24
PYTHON_VERSION := 3.12

.PHONY: check-model-config check-uv-version helm-depend build-all-images push-all-images \
  helm-install-test test-short-e2e sync-evaluations test-short-eval helm-uninstall

check-model-config:
	@test -n "$(MODEL_ID)" || (echo "MODEL_ID must be set"; exit 1)
	@test -n "$(MODEL_URL)" || (echo "MODEL_URL must be set"; exit 1)
	@test -n "$(MODEL_API_KEY)" || (echo "MODEL_API_KEY must be set"; exit 1)

check-uv-version:
	@uv --version | grep -q "$(UV_VERSION)"

helm-depend:
	@echo "Fixture Helm dependencies prepared"

build-all-images:
	@echo "Fixture images built for $(REGISTRY)"

push-all-images:
	@echo "Fixture images pushed to $(REGISTRY)"

helm-install-test: helm-depend check-model-config
	@echo "Fixture Helm test install in $(NAMESPACE)"

test-short-e2e: check-model-config
	@echo "Fixture short E2E tests passed"

sync-evaluations:
	@echo "Fixture evaluation dependencies prepared"

test-short-eval: check-model-config
	@mkdir -p evaluations/results
	@printf '%s\n' '{"status":"passed"}' > evaluations/results/summary.json

helm-uninstall:
	@echo "Fixture Helm test release uninstalled from $(NAMESPACE)"
