#!/usr/bin/env bash
# Install Python deps for unit/E2E test runs OR pack them into the deploy zip.
#
# Usage: bin/install-deps.sh [unit|e2e|package]
#
# Modes:
#   unit     - install runtime + pytest into the agent env (for unit tests)
#   e2e      - install runtime + pytest-json-report into the agent env
#   package  - install runtime into <workdir>/.python_packages/lib/site-packages
#              so ArchiveFiles ships the deps INSIDE the deploy zip. Required
#              because the Function App runs with WEBSITE_RUN_FROM_PACKAGE=1
#              (read-only mount, no remote pip install).
set -euo pipefail

mode="${1:-unit}"
cd "${WORKING_DIRECTORY:-src/api}"

pip install --upgrade pip

case "$mode" in
  unit)
    pip install -r requirements.txt
    pip install pytest pytest-cov httpx
    ;;
  e2e)
    pip install -r requirements.txt
    pip install pytest pytest-json-report httpx
    ;;
  package)
    rm -rf .python_packages
    pip install \
      --target=".python_packages/lib/site-packages" \
      --no-compile \
      --only-binary=:all: \
      --platform=manylinux2014_x86_64 \
      --python-version=3.11 \
      --implementation=cp \
      --abi=cp311 \
      -r requirements.txt
    ;;
  *)
    echo "unknown mode: $mode" >&2
    exit 2
    ;;
esac
