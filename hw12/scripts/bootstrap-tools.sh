#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${ROOT_DIR}/bin"
HELM_VERSION="v3.16.2"
HELM_BIN="${BIN_DIR}/helm"
OS_NAME="$(uname | tr '[:upper:]' '[:lower:]')"
ARCH_NAME="$(uname -m)"

case "${ARCH_NAME}" in
  arm64|aarch64)
    HELM_ARCH="arm64"
    ;;
  x86_64|amd64)
    HELM_ARCH="amd64"
    ;;
  *)
    echo "Неподдерживаемая архитектура: ${ARCH_NAME}" >&2
    exit 1
    ;;
esac

mkdir -p "${BIN_DIR}"

if [[ ! -x "${HELM_BIN}" ]]; then
  echo "Скачиваю helm ${HELM_VERSION} в ${HELM_BIN}"
  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "${tmp_dir}"' EXIT
  curl -fsSL "https://get.helm.sh/helm-${HELM_VERSION}-${OS_NAME}-${HELM_ARCH}.tar.gz" -o "${tmp_dir}/helm.tgz"
  tar -xzf "${tmp_dir}/helm.tgz" -C "${tmp_dir}"
  mv "${tmp_dir}/${OS_NAME}-${HELM_ARCH}/helm" "${HELM_BIN}"
  chmod +x "${HELM_BIN}"
else
  echo "helm уже доступен: ${HELM_BIN}"
fi

echo "Готово"
