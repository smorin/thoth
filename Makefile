.PHONY: check help clean check-uv

help:
	@echo "Available targets:"
	@echo "  check    - Check development environment"
	@echo "  check-uv - Check if UV is installed"
	@echo "  clean    - Remove build artifacts"
	@echo "  help     - Show this help message"
	@echo ""
	@echo "For all other commands, use 'just' (the primary task runner):"
	@echo "  just --list"

check: check-uv
	@echo "Checking development environment..."
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not found. Install from: https://docs.astral.sh/uv/"; exit 1; }
	@command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 not found"; exit 1; }
	@command -v just >/dev/null 2>&1 || { echo "❌ just not found. Install from: https://github.com/casey/just"; exit 1; }
	@echo "✅ All dependencies found"
	@python3 --version
	@uv --version
	@just --version

check-uv:
	@command -v uv >/dev/null 2>&1 || { echo "UV not found. Install from: https://github.com/astral-sh/uv"; exit 1; }

clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache/ .ruff_cache/
	rm -rf htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
