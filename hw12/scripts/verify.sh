#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${ROOT_DIR}"

echo "== go test =="
go test ./...

echo "== Проверка Python =="
python3 -m py_compile apps/spark/orders_daily/src/job.py

echo "== Генерация workflow =="
./scripts/generate-workflows.sh

echo "== Рендер Kustomize =="
kubectl kustomize deploy/kustomize/showcase/overlays/dev >/dev/null
kubectl kustomize deploy/kustomize/showcase/overlays/prod >/dev/null

echo "== Рендер Helm =="
./scripts/render-helm.sh >/dev/null

echo "Проверка завершена успешно"
