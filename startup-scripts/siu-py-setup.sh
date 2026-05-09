#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_PATH="$ROOT_DIR/.venv"
PY="$VENV_PATH/bin/python"
PIP="$VENV_PATH/bin/python -m pip"

usage() {
  echo "Usage: $0 <bootstrap|install|sync|env>"
  exit 2
}

cmd="${1:-bootstrap}"

ensure_venv() {
  if [ ! -x "$VENV_PATH/bin/python" ]; then
    echo "Creating virtualenv at $VENV_PATH"
    python3 -m venv "$VENV_PATH"
    "$PY" -m pip install --upgrade pip setuptools wheel
  fi
}

bootstrap() {
  ensure_venv
  echo "Installing uv into venv..."
  "$PY" -m pip install --upgrade uv
  echo "Running uv install to ensure pinned deps are present"
  "$PY" -m uv install || true
  echo "Bootstrap complete."
}

install() {
  ensure_venv
  echo "Install: prefer 'uv sync' if a lockfile exists, otherwise use requirements.txt or uv sync as fallback"
  if [ -f "$ROOT_DIR/uv.lock" ] || [ -f "$ROOT_DIR/poetry.lock" ] || [ -f "$ROOT_DIR/pipfile.lock" ]; then
    echo "Lockfile found — running 'python -m uv sync --all-extras' (includes dev dependencies)"
    "$PY" -m uv sync --all-extras
    return
  fi

  if [ -f "$ROOT_DIR/requirements.txt" ]; then
    echo "No lockfile found — running 'python -m uv pip install -r requirements.txt'"
    "$PY" -m uv pip install -r "$ROOT_DIR/requirements.txt"
    return
  fi

  echo "No requirements.txt or lockfile found — running 'python -m uv sync --all-extras' as fallback"
  "$PY" -m uv sync --all-extras
}

sync() {
  ensure_venv
  echo "Running 'python -m uv sync --all-extras' (includes dev dependencies)"
  "$PY" -m uv sync --all-extras
}

env_cmd() {
  echo "Creating virtualenv (env) and installing minimal tooling"
  python3 -m venv "$VENV_PATH"
  "$PY" -m pip install --upgrade pip setuptools wheel uv
}

case "$cmd" in
  bootstrap) bootstrap ;;
  install) install ;;
  sync) sync ;;
  env) env_cmd ;;
  *) usage ;;
esac
