#!/bin/bash
# Kilo installation script

set -e

echo "🚀 Installing Kilo Orchestration System..."

# Check Python 3.10+
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3.10+ required but not found"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python $PYTHON_VERSION found"

# Create directories
mkdir -p .kilocode/{orchestrator,agents,hooks,rules,logs,scan_results,reviews}

# Make scripts executable
chmod +x .kilocode/orchestrator/kilo_orchestrate.py
chmod +x .kilocode/kilo.py

# Create symlink (optional)
if [ -w /usr/local/bin ]; then
    ln -sf "$(pwd)/.kilocode/kilo.py" /usr/local/bin/kilo
    echo "✓ Kilo installed to /usr/local/bin/kilo"
else
    echo "⚠️  Cannot create symlink. Add to PATH manually:"
    echo "   export PATH=\"\$PATH:$(pwd)/.kilocode\""
fi

# Verify installation
echo ""
echo "✓ Installation complete!"
echo ""
echo "Quick Start:"
echo "  kilo orchestrate --parallel \"Add user authentication\""
echo "  kilo orchestrate --list-branches"
echo "  kilo orchestrate --review <branch>"
echo "  kilo orchestrate --merge <branch>"
echo ""
echo "Documentation: .kilocode/README.md"
