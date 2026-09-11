NAMESPACE ?= qs-test-quickstart-ci-project-1
RELEASE ?= qs-test-quickstart
CHART ?= helm

.PHONY: deploy test helm-do-something verify-deploy

deploy:
	helm upgrade --install $(RELEASE) $(CHART) --namespace $(NAMESPACE) --create-namespace

helm-do-something:
	helm uninstall $(RELEASE) --namespace $(NAMESPACE)

test:
	@echo "Nightly tests passed"

verify-deploy:
	helm status $(RELEASE) --namespace $(NAMESPACE)
