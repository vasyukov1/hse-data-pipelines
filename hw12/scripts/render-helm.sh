#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HELM_BIN="${ROOT_DIR}/bin/helm"
RENDER_DIR="${ROOT_DIR}/rendered/helm"

"${ROOT_DIR}/scripts/bootstrap-tools.sh"
mkdir -p "${RENDER_DIR}"

"${HELM_BIN}" repo add argo https://argoproj.github.io/argo-helm >/dev/null 2>&1 || true
"${HELM_BIN}" repo add spark-operator https://kubeflow.github.io/spark-operator >/dev/null 2>&1 || true
"${HELM_BIN}" repo update >/dev/null

for chart_dir in \
  "${ROOT_DIR}/deploy/helm/argo-workflows" \
  "${ROOT_DIR}/deploy/helm/minio" \
  "${ROOT_DIR}/deploy/helm/postgresql" \
  "${ROOT_DIR}/deploy/helm/spark-operator"; do
  chart_name="$(basename "${chart_dir}")"
  echo "Обрабатываю ${chart_name}"
  "${HELM_BIN}" dependency build "${chart_dir}" >/dev/null
  "${HELM_BIN}" template "${chart_name}" "${chart_dir}" > "${RENDER_DIR}/${chart_name}.yaml"
done

echo "Рендер завершён: ${RENDER_DIR}"
