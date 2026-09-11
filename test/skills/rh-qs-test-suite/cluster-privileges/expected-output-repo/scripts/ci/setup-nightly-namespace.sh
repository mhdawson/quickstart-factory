#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-qs-test-quickstart-ci-project-1}"
SA_NAME="${SA_NAME:-qs-test-quickstart-ci-1}"
TOKEN_DURATION="${TOKEN_DURATION:-8760h}"

oc create namespace "$NAMESPACE"
oc create sa "$SA_NAME" -n "$NAMESPACE"
oc adm policy add-role-to-user admin \
  "system:serviceaccount:${NAMESPACE}:${SA_NAME}" \
  -n "$NAMESPACE"

echo
echo "PROD_SERVER: $(oc whoami --show-server)"
echo "PROD_TOKEN:"
oc create token "$SA_NAME" -n "$NAMESPACE" --duration="$TOKEN_DURATION"

echo
echo "Set the two values above as repository secrets PROD_SERVER and PROD_TOKEN"
echo "(Settings -> Secrets and variables -> Actions) before enabling the nightly workflows."
