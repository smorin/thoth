# Thoth Makefile
.PHONY: help install dev test lint format typecheck check fix clean run

# Default target
help:
	@echo "Thoth Development Commands:"
	@echo "  make install    - Install thoth to /usr/local/bin"
	@echo "  make dev        - Run thoth from current directory"
	@echo "  make test       - Run test suite"
	@echo "  make lint       - Run linters (ruff via uv)"
	@echo "  make format     - Format code (ruff via uv)"
	@echo "  make typecheck  - Run type checker (ty via uv)"
	@echo "  make check      - Run all checks (lint + typecheck)"
	@echo "  make fix        - Auto-fix lint issues and format code"
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
	@uv tool run ruff check thoth

# Format code
format:
	@echo "Formatting code..."
	@uv tool run ruff format thoth

# Run type checker
typecheck:
	@echo "Running type checker..."
	@uv tool run ty check thoth

# Run all checks
check: lint typecheck
	@echo "✓ All checks passed"

# Auto-fix issues
fix:
	@echo "Auto-fixing lint issues..."
	@uv tool run ruff check --fix thoth
	@echo "Formatting code..."
	@uv tool run ruff format thoth
	@echo "✓ Code fixed and formatted"

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