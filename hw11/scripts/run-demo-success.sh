#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

NAMESPACE="${NAMESPACE:-argo}"
PROJECT_URL="${PROJECT_URL:-http://coursework-demo-server.${NAMESPACE}.svc.cluster.local:8000/coursework-ok.zip}"

ensure_argo

argo submit -n "${NAMESPACE}" --watch "${HW11_ROOT}/workflows/coursework-check-workflow.yaml" \
  -p project-url="${PROJECT_URL}" \
  -p archive-filename=coursework-ok.zip \
  -p project-name=AntiPlagiarism \
  -p student-name="Alexander Vasyukov" \
  -p required-paths="README.md,go.mod,cmd"

echo
echo "Latest workflow details:"
argo get -n "${NAMESPACE}" @latest
echo
echo "Latest workflow logs:"
argo logs -n "${NAMESPACE}" @latest
