#!/bin/bash

# Devsy Setup Script Example
#
# Copy this file to .devsy/setup.sh in your repository and uncomment the sections
# relevant to your project. This script runs after Python environment setup
# but before Claude Code execution to ensure dependencies are available.
#
# Usage in your workflow:
#   - uses: DevsyAI/devsy-action@main
#     with:
#       setup_script: '.devsy/setup.sh'

echo "🔧 Running Devsy setup..."

# ============================================================================
# PYTHON PROJECTS
# ============================================================================

# Install Python dependencies using UV
echo "📦 Installing Python dependencies with pip..."
pip install -r requirements.txt

# Make scripts executable
echo "🔐 Making scripts executable..."
chmod +x thoth thoth_test 2>/dev/null || true

# Run basic checks
echo "✔️  Running basic checks..."
make check-uv || echo "⚠️  UV not found - install with: curl -LsSf https://astral.sh/uv/install.sh | sh"

echo "✅ Devsy setup completed!"
