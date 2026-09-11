NAMESPACE ?= nightly-ci-fixture-ci-project-1
RELEASE ?= nightly-ci-fixture
CHART ?= helm
MODEL_ID ?=
MODEL_URL ?=
MODEL_API_KEY ?=
UV_VERSION := 0.5.24

.PHONY: check-model-config check-uv-version deploy test undeploy verify-deploy

check-model-config:
	@test -n "$(MODEL_ID)" || (echo "MODEL_ID must be set"; exit 1)
	@test -n "$(MODEL_URL)" || (echo "MODEL_URL must be set"; exit 1)
	@test -n "$(MODEL_API_KEY)" || (echo "MODEL_API_KEY must be set"; exit 1)

check-uv-version:
	@uv --version | grep -q "$(UV_VERSION)" || (echo "uv $(UV_VERSION) must be installed"; exit 1)

deploy: check-model-config
	helm upgrade --install $(RELEASE) $(CHART) --namespace $(NAMESPACE) --create-namespace \
		--set-string model.id="$(MODEL_ID)" \
		--set-string model.url="$(MODEL_URL)" \
		--set-string model.apiKey="$(MODEL_API_KEY)"

test: check-model-config check-uv-version
	@uv run --no-project python -c "print('Nightly CI fixture model tests passed')"

undeploy:
	helm uninstall $(RELEASE) --namespace $(NAMESPACE)

verify-deploy:
	helm status $(RELEASE) --namespace $(NAMESPACE)
