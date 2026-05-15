#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Использование: $0 <dev|prod>" >&2
  exit 1
fi

ENV_NAME="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HELM_BIN="${ROOT_DIR}/bin/helm"

"${ROOT_DIR}/scripts/bootstrap-tools.sh"
kubectl apply -f "${ROOT_DIR}/deploy/core/00-namespaces.yaml"
kubectl apply -f "${ROOT_DIR}/deploy/core/01-spark-rbac.yaml"

"${HELM_BIN}" repo add argo https://argoproj.github.io/argo-helm >/dev/null 2>&1 || true
"${HELM_BIN}" repo add spark-operator https://kubeflow.github.io/spark-operator >/dev/null 2>&1 || true
"${HELM_BIN}" repo update >/dev/null

for chart_dir in \
  "${ROOT_DIR}/deploy/helm/argo-workflows" \
  "${ROOT_DIR}/deploy/helm/minio" \
  "${ROOT_DIR}/deploy/helm/postgresql" \
  "${ROOT_DIR}/deploy/helm/spark-operator"; do
  chart_name="$(basename "${chart_dir}")"
  "${HELM_BIN}" dependency build "${chart_dir}" >/dev/null
  "${HELM_BIN}" upgrade --install "${chart_name}" "${chart_dir}" --namespace "${chart_name}" --create-namespace
done

kubectl apply -n argo -f "${ROOT_DIR}/argo/templates/common/report-template.yaml"
kubectl apply -n argo -f "${ROOT_DIR}/argo/templates/spark/spark-submit-template.yaml"
kubectl apply -n argo -f "${ROOT_DIR}/argo/templates/spark/spark-wait-template.yaml"
kubectl apply -k "${ROOT_DIR}/deploy/kustomize/showcase/overlays/${ENV_NAME}"
