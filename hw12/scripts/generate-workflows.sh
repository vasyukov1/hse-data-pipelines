#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${ROOT_DIR}"

go run ./cmd/workflowgen \
  -config argo/workflows/templates/orders-daily-dev.values.yaml \
  -template argo/workflows/templates/orders-daily-workflow.tpl.yaml \
  -output argo/workflows/generated/dev/orders-daily.yaml

go run ./cmd/workflowgen \
  -config argo/workflows/templates/orders-daily-prod.values.yaml \
  -template argo/workflows/templates/orders-daily-workflow.tpl.yaml \
  -output argo/workflows/generated/prod/orders-daily.yaml
