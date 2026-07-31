#!/bin/bash
# Cleanup Crew - Cleanup Phase (Destructive, requires verification)
set -e

PROJECT_ROOT=$(pwd)
DELETION_LOG=".cleanup/deletion-log-$(date +%Y%m%d-%H%M%S).md"

echo "=== Cleanup Crew: Cleanup Phase ==="
echo "CAUTION: This will DELETE files. Ctrl+C to abort."
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 1
fi

# Initialize deletion log
cat > "$DELETION_LOG" <<EOF
# Cleanup Session $(date +"%Y-%m-%d %H:%M")

## Summary
- Session started: $(date)
- Project: $PROJECT_ROOT

EOF

# Cleanup Phase 1: Build Artifacts (Safe)
echo ""
echo "Phase 1: Removing build artifacts..."
if [ -f ".cleanup/build-artifacts.txt" ]; then
  ARTIFACT_COUNT=$(wc -l < .cleanup/build-artifacts.txt)
  echo "   - Removing $ARTIFACT_COUNT build artifacts..."

  echo "" >> "$DELETION_LOG"
  echo "## Build Artifacts Removed" >> "$DELETION_LOG"

  while IFS= read -r FILE; do
    if [ -e "$FILE" ]; then
      echo "- $FILE" >> "$DELETION_LOG"
      rm -rf "$FILE"
    fi
  done < .cleanup/build-artifacts.txt

  echo "   Done."
fi

# Cleanup Phase 2: Stale Documentation (Archive, not delete)
echo ""
echo "Phase 2: Archiving stale documentation..."
if [ -f ".cleanup/stale-docs.txt" ] && [ -s ".cleanup/stale-docs.txt" ]; then
  STALE_COUNT=$(wc -l < .cleanup/stale-docs.txt)
  echo "   - Archiving $STALE_COUNT stale docs..."

  mkdir -p .codex/archive/sessions
  mkdir -p .codex/archive/audits

  echo "" >> "$DELETION_LOG"
  echo "## Documentation Archived" >> "$DELETION_LOG"

  while IFS= read -r DOC; do
    if [ -f "$DOC" ]; then
      BASENAME=$(basename "$DOC")
      # Determine archive location
      if [[ "$BASENAME" == *"session"* ]] || [[ "$BASENAME" == *"sprint"* ]]; then
        DEST=".codex/archive/sessions/$BASENAME"
      elif [[ "$BASENAME" == *"AUDIT"* ]]; then
        DEST=".codex/archive/audits/$BASENAME"
      else
        DEST=".codex/archive/$BASENAME"
      fi

      echo "- $DOC -> $DEST" >> "$DELETION_LOG"
      mv "$DOC" "$DEST"
    fi
  done < .cleanup/stale-docs.txt

  echo "   Done."
fi

# Cleanup Phase 3: Stale Plans (Archive)
if [ -f ".cleanup/stale-plans.txt" ] && [ -s ".cleanup/stale-plans.txt" ]; then
  STALE_PLANS=$(wc -l < .cleanup/stale-plans.txt)
  echo "   - Archiving $STALE_PLANS stale plans..."

  mkdir -p .codex/archive/plans

  echo "" >> "$DELETION_LOG"
  echo "## Plans Archived" >> "$DELETION_LOG"

  while IFS= read -r PLAN; do
    if [ -f "$PLAN" ]; then
      BASENAME=$(basename "$PLAN")
      DEST=".codex/archive/plans/$BASENAME"
      echo "- $PLAN -> $DEST" >> "$DELETION_LOG"
      mv "$PLAN" "$DEST"
    fi
  done < .cleanup/stale-plans.txt

  echo "   Done."
fi

# Verification
echo ""
echo "=== Verification ==="
echo "Running tests to ensure cleanup didn't break anything..."

HAS_PACKAGE_JSON=false
HAS_PYPROJECT=false

if [ -f "package.json" ]; then
  HAS_PACKAGE_JSON=true
fi

if [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
  HAS_PYPROJECT=true
fi

TESTS_PASSED=true

if [ "$HAS_PACKAGE_JSON" = true ]; then
  if bun test 2>&1 | tee .cleanup/test-post-cleanup.log; then
    echo "   - JavaScript tests: PASS"
  else
    echo "   - JavaScript tests: FAIL"
    TESTS_PASSED=false
  fi
fi

if [ "$HAS_PYPROJECT" = true ]; then
  if uv run pytest tests/ 2>&1 | tee .cleanup/pytest-post-cleanup.log; then
    echo "   - Python tests: PASS"
  else
    echo "   - Python tests: FAIL"
    TESTS_PASSED=false
  fi
fi

# Write verification to log
echo "" >> "$DELETION_LOG"
echo "## Verification" >> "$DELETION_LOG"
if [ "$TESTS_PASSED" = true ]; then
  echo "- Tests: PASS" >> "$DELETION_LOG"
  echo "- Git status: $(git status --porcelain | wc -l) files changed" >> "$DELETION_LOG"
else
  echo "- Tests: FAIL" >> "$DELETION_LOG"
  echo "- **ROLLBACK REQUIRED**" >> "$DELETION_LOG"
fi

echo ""
echo "=== Cleanup Complete ==="
echo "Deletion log: $DELETION_LOG"
echo ""

if [ "$TESTS_PASSED" = false ]; then
  echo "ERROR: Tests failed after cleanup. Rollback required."
  echo "Run: git checkout ."
  exit 1
fi

echo "Proceed to commit phase: ./commit.sh"
