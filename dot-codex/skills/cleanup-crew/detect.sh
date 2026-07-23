#!/bin/bash
# Cleanup Crew - Detection Phase (Read-Only)
set -e

PROJECT_ROOT=$(pwd)
mkdir -p .cleanup

echo "=== Cleanup Crew: Detection Phase ==="
echo "Project: $PROJECT_ROOT"
echo ""

# Detect project type
HAS_PACKAGE_JSON=false
HAS_PYPROJECT=false

if [ -f "package.json" ]; then
  HAS_PACKAGE_JSON=true
fi

if [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
  HAS_PYPROJECT=true
fi

# 1. Dead Code Detection
echo "1. Detecting dead code..."
if [ "$HAS_PACKAGE_JSON" = true ]; then
  echo "   - Running Knip (JavaScript/TypeScript)..."
  bunx knip --reporter json > .cleanup/knip-report.json 2>&1 || echo "   (No issues or Knip not applicable)"
fi

if [ "$HAS_PYPROJECT" = true ] && [ -d "src" ]; then
  echo "   - Running Ruff (Python unused imports)..."
  uv run ruff check --select F401,F841 src/ > .cleanup/ruff-unused.txt 2>&1 || echo "   (No unused imports)"
fi

# 2. Dependency Analysis
echo ""
echo "2. Checking dependencies..."
if [ "$HAS_PACKAGE_JSON" = true ]; then
  echo "   - Checking outdated npm packages..."
  bunx npm-check-updates --format json > .cleanup/outdated.json 2>&1 || echo "   (All up to date)"
fi

if [ "$HAS_PYPROJECT" = true ]; then
  echo "   - Checking outdated Python packages..."
  uv pip list --outdated > .cleanup/outdated-python.txt 2>&1 || echo "   (All up to date)"
fi

# 3. Stale Documentation
echo ""
echo "3. Finding stale documentation..."
if [ -d ".codex/docs" ]; then
  find .codex/docs -name "*.md" -mtime +90 > .cleanup/stale-docs.txt 2>&1
  STALE_COUNT=$(wc -l < .cleanup/stale-docs.txt)
  echo "   - Found $STALE_COUNT docs >90 days old"
fi

if [ -d ".codex/plans" ]; then
  find .codex/plans -name "*.md" -mtime +180 > .cleanup/stale-plans.txt 2>&1
  STALE_PLANS=$(wc -l < .cleanup/stale-plans.txt)
  echo "   - Found $STALE_PLANS plans >180 days old"
fi

# 4. Build Artifacts
echo ""
echo "4. Finding removable build artifacts..."
{
  find . -type d -name "__pycache__" 2>/dev/null
  find . -type f -name "*.pyc" 2>/dev/null
  find . -type f -name ".DS_Store" 2>/dev/null
  find . -name "*.swp" 2>/dev/null
} > .cleanup/build-artifacts.txt
ARTIFACT_COUNT=$(wc -l < .cleanup/build-artifacts.txt)
echo "   - Found $ARTIFACT_COUNT removable artifacts"

# 5. Test Inventory
echo ""
echo "5. Checking test status..."
if [ "$HAS_PACKAGE_JSON" = true ]; then
  echo "   - Running tests for baseline..."
  bun test --reporter=json > .cleanup/test-baseline.json 2>&1 || echo "   (Tests not configured)"
fi

if [ "$HAS_PYPROJECT" = true ]; then
  echo "   - Collecting Python tests..."
  uv run pytest --collect-only > .cleanup/test-inventory.txt 2>&1 || echo "   (Tests not configured)"
fi

# Summary
echo ""
echo "=== Detection Complete ==="
echo "Reports generated in .cleanup/"
echo ""
echo "Review reports before running cleanup:"
echo "  - .cleanup/knip-report.json (dead code)"
echo "  - .cleanup/stale-docs.txt (old docs)"
echo "  - .cleanup/build-artifacts.txt (removable artifacts)"
echo ""
echo "Next step: Review reports, then run cleanup.sh"
