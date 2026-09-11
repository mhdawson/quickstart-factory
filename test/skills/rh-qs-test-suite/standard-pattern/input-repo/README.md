# Nightly CI Demo

A minimal Helm-deployed service for demonstrating a Quickstart deployment workflow.

## Prerequisites

- Access to an OpenShift cluster
- A model deployment ID, API URL, and API key
- `uv` version `0.5.24` to run the Python test harness used by `make test`

## Deploy

Set the target namespace:

```bash
export NAMESPACE=your-namespace
export MODEL_ID=granite-3.1-8b-instruct
export MODEL_URL=https://model.example.com/v1
export MODEL_API_KEY=your-model-api-key
```

Deploy the chart:

```bash
make deploy NAMESPACE=$NAMESPACE MODEL_ID=$MODEL_ID MODEL_URL=$MODEL_URL MODEL_API_KEY=$MODEL_API_KEY
```

Check the release:

```bash
make verify-deploy NAMESPACE=$NAMESPACE
```

## Test

```bash
make test MODEL_ID=$MODEL_ID MODEL_URL=$MODEL_URL MODEL_API_KEY=$MODEL_API_KEY
```

## Remove

```bash
make undeploy NAMESPACE=$NAMESPACE
```
