#!/usr/bin/env bash
# setup-security.sh — One-time setup for local security scanning tools
set -euo pipefail

echo "🔧 Installing security scanning tools..."

# Detect OS
OS="$(uname -s)"

install_tool() {
  local name="$1"
  local install_cmd="$2"
  if command -v "$name" &>/dev/null; then
    echo "  ✅ $name already installed ($(command -v "$name"))"
  else
    echo "  📦 Installing $name..."
    eval "$install_cmd"
  fi
}

# Core scanners
install_tool "semgrep"    "pip install semgrep"
install_tool "trufflehog" "brew install trufflehog 2>/dev/null || curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh -s -- -b /usr/local/bin"
install_tool "gitleaks"   "brew install gitleaks 2>/dev/null || go install github.com/gitleaks/gitleaks/v8@latest"
install_tool "trivy"      "brew install trivy 2>/dev/null || curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin"
install_tool "grype"      "brew install grype 2>/dev/null || curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin"
install_tool "checkov"    "pip install checkov"
install_tool "pip-audit"  "pip install pip-audit"

# Pre-commit framework
install_tool "pre-commit" "pip install pre-commit"

# Install hooks
if [ -f ".pre-commit-config.yaml" ]; then
  echo "  🪝 Installing pre-commit hooks..."
  pre-commit install
  pre-commit install --hook-type pre-push
fi

echo ""
echo "✅ All tools installed. Quick test commands:"
echo "   semgrep scan --config p/owasp-top-ten ."
echo "   trufflehog git file://. --since-commit HEAD"
echo "   gitleaks detect --source ."
echo "   trivy fs --scanners vuln,secret,misconfig ."
echo "   checkov -d ."
echo ""
echo "Run full scan: bash .security/scan-all.sh"
echo "Run quick pre-commit: git commit (hooks auto-run)"
