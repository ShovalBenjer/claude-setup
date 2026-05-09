#!/usr/bin/env bash
# CI: install runtime + dev deps from pyproject.toml lockfile so test imports
# match the deployed image. Avoids "tests pass locally, fail in CI" caused by
# skewed dep versions.
set -euo pipefail

python3 -m pip install --upgrade pip uv

# Runtime deps from pyproject (best-effort; ignore if compile path fails)
uv pip install --system -r <(uv pip compile pyproject.toml --no-deps 2>/dev/null || echo "")

# Dev + runtime deps (must match what the image needs at import time)
# httpx[http2] is mandatory — _http_client.py uses http2=True, which raises
# ImportError ("Using http2=True requires the 'h2' package") without it.
# Build 11992 surfaced this as ~70 cascading test failures with KeyError on
# response payloads — the wrapper had short-circuited every HTTP call with
# upstream_error envelopes.
uv pip install --system \
  pytest pytest-cov pytest-asyncio ruff mypy \
  openpyxl pandas pyyaml 'httpx[http2]' respx hypothesis \
  'mcp>=1.0' 'fastapi>=0.115' 'pydantic>=2.8' 'PyJWT>=2.8' \
  'azure-identity>=1.16' 'azure-keyvault-secrets>=4.8' \
  'python-multipart>=0.0.9' 'uvicorn[standard]>=0.30'
