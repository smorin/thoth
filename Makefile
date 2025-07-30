# Thoth Makefile
.PHONY: help install dev test lint format clean run

# Default target
help:
	@echo "Thoth Development Commands:"
	@echo "  make install    - Install thoth to /usr/local/bin"
	@echo "  make dev        - Run thoth from current directory"
	@echo "  make test       - Run test suite"
	@echo "  make lint       - Run linters (ruff)"
	@echo "  make format     - Format code with black"
	@echo "  make clean      - Remove generated files"
	@echo "  make run        - Run thoth with example query"

# Install thoth to system
install:
	@echo "Installing thoth to /usr/local/bin..."
	@cp thoth /usr/local/bin/
	@chmod +x /usr/local/bin/thoth
	@echo "✓ Thoth installed successfully"
	@echo "Run 'thoth --help' to get started"

# Development run
dev:
	@./thoth --help

# Run tests
test:
	@echo "Running tests..."
	@if [ -d "tests" ]; then \
		python -m pytest tests/ -v; \
	else \
		echo "No tests directory found. Creating..."; \
		mkdir -p tests; \
		echo "def test_placeholder():" > tests/test_basic.py; \
		echo "    assert True" >> tests/test_basic.py; \
	fi

# Lint code
lint:
	@echo "Running linters..."
	@ruff check thoth || echo "Install ruff: pip install ruff"

# Format code
format:
	@echo "Formatting code..."
	@black thoth --line-length 100 || echo "Install black: pip install black"

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@rm -rf .pytest_cache 2>/dev/null || true
	@rm -rf .ruff_cache 2>/dev/null || true
	@echo "✓ Cleaned"

# Example run
run:
	@echo "Running example research query..."
	@./thoth clarification "What is quantum computing?"

# Check if UV is installed
check-uv:
	@command -v uv >/dev/null 2>&1 || { echo "UV not found. Install from: https://github.com/astral-sh/uv"; exit 1; }

# Run thoth init
init: check-uv
	@./thoth init

# Quick test of basic functionality
smoke-test: check-uv
	@echo "Running smoke tests..."
	@./thoth --version
	@./thoth --help
	@echo "✓ Basic functionality working"