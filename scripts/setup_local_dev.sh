#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
BACKEND_DOCKERFILE="${ROOT_DIR}/Dockerfile"
FRONTEND_DOCKERFILE="${ROOT_DIR}/frontend/Dockerfile"

PYTHON_VERSION="$(sed -n 's/^FROM python:\([0-9][0-9]*\.[0-9][0-9]*\).*$/\1/p' "${BACKEND_DOCKERFILE}" | head -n1)"
NODE_VERSION="$(sed -n 's/^FROM node:\([0-9][0-9]*\).*$/\1/p' "${FRONTEND_DOCKERFILE}" | head -n1)"

print_activate_hint() {
  cat <<EOF

Next step in your current shell:
  source .venv/bin/activate
EOF
}

load_nvm() {
  export NVM_DIR="${HOME}/.nvm"
  if [[ -s "${NVM_DIR}/nvm.sh" ]]; then
    # shellcheck disable=SC1090
    . "${NVM_DIR}/nvm.sh"
    return 0
  fi
  return 1
}

log() {
  printf '\n[%s] %s\n' "setup" "$1"
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    if [[ "$1" == "npm" ]]; then
      cat <<EOF >&2
This repo's frontend Docker image uses Node ${NODE_VERSION}.x, and the local setup expects npm from that Node install.
Example install with nvm:
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
  export NVM_DIR="\$HOME/.nvm"
  [ -s "\$NVM_DIR/nvm.sh" ] && . "\$NVM_DIR/nvm.sh"
  nvm install ${NODE_VERSION}
  nvm use ${NODE_VERSION}

Then rerun:
  ./scripts/setup_local_dev.sh
EOF
    fi
    print_activate_hint >&2
    exit 1
  fi
}

ensure_node_toolchain() {
  if command -v npm >/dev/null 2>&1; then
    return 0
  fi

  if load_nvm; then
    log "npm was not found; using nvm to install/select Node ${NODE_VERSION}"
    nvm install "${NODE_VERSION}"
    nvm use "${NODE_VERSION}"
  fi
}

log "Preparing Juicy Fruit local development environment"
log "Expected Python ${PYTHON_VERSION} and Node ${NODE_VERSION}"

need_cmd bash
need_cmd python3
ensure_node_toolchain
need_cmd npm

CURRENT_PYTHON="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')"
CURRENT_PYTHON_MM="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
CURRENT_NODE="$(node -v 2>/dev/null | sed 's/^v//')"
CURRENT_NODE_MAJOR="$(node -p 'process.versions.node.split(\".\")[0]' 2>/dev/null || true)"

if [[ -z "${PYTHON_VERSION}" ]]; then
  echo "Unable to determine Python version from ${BACKEND_DOCKERFILE}" >&2
  exit 1
fi

if [[ -z "${NODE_VERSION}" ]]; then
  echo "Unable to determine Node.js version from ${FRONTEND_DOCKERFILE}" >&2
  exit 1
fi

if [[ "${CURRENT_PYTHON_MM}" != "${PYTHON_VERSION}" ]]; then
  cat <<EOF
Warning: python3 resolved to ${CURRENT_PYTHON}, but the backend Docker image uses Python ${PYTHON_VERSION}.x.
Your local venv will still be created, but pytest behavior may drift from Docker if you stay on ${CURRENT_PYTHON}.
EOF
fi

if [[ -z "${CURRENT_NODE:-}" ]]; then
  echo "Node.js is required but was not found on PATH." >&2
  exit 1
fi

if [[ "${CURRENT_NODE_MAJOR}" != "${NODE_VERSION}" ]]; then
  cat <<EOF
Warning: node resolved to ${CURRENT_NODE}, but the frontend Docker image uses Node ${NODE_VERSION}.x.
Frontend, Vite, and Playwright runs may behave differently until you switch to Node ${NODE_VERSION}.
EOF
fi

log "Creating virtual environment at ${VENV_DIR}"
python3 -m venv "${VENV_DIR}"

log "Upgrading pip tooling"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel

log "Installing backend dependencies"
"${VENV_DIR}/bin/pip" install -r "${ROOT_DIR}/requirements.txt"

log "Installing frontend dependencies with npm install"
(cd "${ROOT_DIR}/frontend" && npm install)

log "Installing Playwright browsers"
(cd "${ROOT_DIR}/frontend" && npx playwright install)

cat <<EOF

Local dev environment is ready.

The script cannot activate the virtualenv for your current terminal because it runs in a child shell.
Run this next in your current shell:
  source .venv/bin/activate

Run backend tests:
  python -m pytest

Run frontend unit tests:
  cd frontend && npm test

Run Playwright specs:
  cd frontend && npm run test:e2e
EOF
