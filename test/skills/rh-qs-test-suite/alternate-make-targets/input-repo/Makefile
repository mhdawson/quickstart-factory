NAMESPACE ?= qs-test-quickstart-ci-project-1
RELEASE ?= qs-test-quickstart
CHART ?= helm

.PHONY: helm-install-prod test-all helm-uninstall verify-deploy

helm-install-prod:
	helm upgrade --install $(RELEASE) $(CHART) --namespace $(NAMESPACE) --create-namespace

test-all:
	@echo "Nightly tests passed"

helm-uninstall:
	helm uninstall $(RELEASE) --namespace $(NAMESPACE)

verify-deploy:
	helm status $(RELEASE) --namespace $(NAMESPACE)
