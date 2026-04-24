.PHONY: help env-check check-uv

help:
	@echo "Available targets:"
	@echo "  env-check - Check development environment bootstrap dependencies"
	@echo "  check-uv  - Check if UV is installed"
	@echo "  help      - Show this help message"
	@echo ""
	@echo "Use 'just --list' for all development, quality, test, build, and release commands."

env-check: check-uv
	@echo "Checking development environment..."
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not found. Install from: https://docs.astral.sh/uv/"; exit 1; }
	@command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 not found"; exit 1; }
	@command -v just >/dev/null 2>&1 || { echo "❌ just not found. Install from: https://github.com/casey/just"; exit 1; }
	@command -v bun >/dev/null 2>&1 || { echo "❌ bun not found (required for commitlint). Install via 'brew install bun' or https://bun.sh/"; exit 1; }
	@echo "✅ All dependencies found"
	@python3 --version
	@uv --version
	@just --version
	@bun --version

check-uv:
	@command -v uv >/dev/null 2>&1 || { echo "UV not found. Install from: https://github.com/astral-sh/uv"; exit 1; }
