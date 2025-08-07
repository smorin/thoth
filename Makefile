# Thoth Makefile

# Color definitions
NC := \033[0m
BLACK := \033[30m
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
MAGENTA := \033[35m
CYAN := \033[36m
WHITE := \033[37m
GRAY := \033[90m

# Text styles
BOLD := \033[1m
DIM := \033[2m
ITALIC := \033[3m
UNDERLINE := \033[4m

.PHONY: help install dev test lint format typecheck check fix clean run test-lint test-format test-typecheck test-check test-fix lint-all format-all check-all fix-all install-uv install-uv-force set-path check-uv init smoke-test

# Default target
help: ## Show this help message
	@echo ""
	@echo "$(BOLD)Thoth Development Commands$(NC)"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "$(UNDERLINE)Targets:$(NC)"
	@grep -h -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "$(CYAN)%-30s$(NC) %s\n", $$1, $$2}' | sort
	@echo ""
	@echo "$(DIM)Grouped by category:$(NC)"
	@echo ""
	@echo "$(YELLOW)General:$(NC)"
	@grep -h -E '^(install|dev|test|clean|run|init|smoke-test):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-28s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Main Executable (thoth):$(NC)"
	@grep -h -E '^(lint|format|typecheck|check|fix):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-28s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Test Suite (thoth_test):$(NC)"
	@grep -h -E '^test-(lint|format|typecheck|check|fix):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-28s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Combined Operations:$(NC)"
	@grep -h -E '^(lint-all|format-all|check-all|fix-all):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-28s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)UV Installation:$(NC)"
	@grep -h -E '^(install-uv|install-uv-force|set-path):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-28s$(NC) %s\n", $$1, $$2}'
	@echo ""

# Install thoth to system
install: ## Install thoth to /usr/local/bin
	@echo "Installing thoth to /usr/local/bin..."
	@cp thoth /usr/local/bin/
	@chmod +x /usr/local/bin/thoth
	@echo "✓ Thoth installed successfully"
	@echo "Run 'thoth --help' to get started"

# Development run
dev: ## Show thoth help (development mode)
	@./thoth --help

# Run tests
test: ## Run test suite
	@echo "Running tests..."
	@if [ -d "tests" ]; then \
		python -m pytest tests/ -v; \
	else \
		echo "No tests directory found. Creating..."; \
		mkdir -p tests; \
		echo "def test_placeholder():" > tests/test_basic.py; \
		echo "    assert True" >> tests/test_basic.py; \
	fi

# Lint main executable
lint: ## Lint thoth executable
	@echo "Linting thoth executable..."
	@uv tool run ruff check thoth

# Format main executable
format: ## Format thoth executable
	@echo "Formatting thoth executable..."
	@uv tool run ruff format thoth

# Type check main executable
typecheck: ## Type check thoth executable
	@echo "Type checking thoth executable..."
	@uv tool run ty check thoth

# Check main executable
check: lint typecheck ## Run all checks on thoth executable
	@echo "✓ Thoth executable checks passed"

# Fix main executable
fix: ## Auto-fix and format thoth executable
	@echo "Auto-fixing thoth executable..."
	@uv tool run ruff check --fix thoth
	@echo "Formatting thoth executable..."
	@uv tool run ruff format thoth
	@echo "✓ Thoth executable fixed and formatted"

# TEST SUITE TARGETS

# Lint test suite
test-lint: ## Lint test suite
	@echo "Linting test suite..."
	@uv tool run ruff check thoth_test

# Format test suite
test-format: ## Format test suite
	@echo "Formatting test suite..."
	@uv tool run ruff format thoth_test

# Type check test suite
test-typecheck: ## Type check test suite
	@echo "Type checking test suite..."
	@uv tool run ty check thoth_test

# Check test suite
test-check: test-lint test-typecheck ## Run all checks on test suite
	@echo "✓ Test suite checks passed"

# Fix test suite
test-fix: ## Auto-fix and format test suite
	@echo "Auto-fixing test suite..."
	@uv tool run ruff check --fix thoth_test
	@echo "Formatting test suite..."
	@uv tool run ruff format thoth_test
	@echo "✓ Test suite fixed and formatted"

# COMBINED TARGETS

# Lint everything
lint-all: lint test-lint ## Lint both thoth and test suite
	@echo "✓ All linting complete"

# Format everything
format-all: format test-format ## Format both thoth and test suite
	@echo "✓ All formatting complete"

# Check everything
check-all: check test-check ## Run all checks on entire codebase
	@echo "✓ All checks passed"

# Fix everything
fix-all: fix test-fix ## Auto-fix and format entire codebase
	@echo "✓ All code fixed and formatted"

# Clean generated files
clean: ## Remove generated files and caches
	@echo "Cleaning generated files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@rm -rf .pytest_cache 2>/dev/null || true
	@rm -rf .ruff_cache 2>/dev/null || true
	@echo "✓ Cleaned"

# Example run
run: ## Run example research prompt
	@echo "Running example research prompt..."
	@./thoth clarification "What is quantum computing?"

# Check if UV is installed
check-uv: ## Check if UV is installed
	@command -v uv >/dev/null 2>&1 || { echo "UV not found. Install from: https://github.com/astral-sh/uv"; exit 1; }

# Run thoth init
init: check-uv ## Initialize thoth configuration
	@./thoth init

# Quick test of basic functionality
smoke-test: check-uv ## Run basic functionality tests
	@echo "Running smoke tests..."
	@./thoth --version
	@./thoth --help
	@echo "✓ Basic functionality working"

# UV INSTALLATION TARGETS

# Install UV - print command
install-uv: ## Print UV installation command
	@echo ""
	@echo "$(BOLD)UV Installation$(NC)"
	@echo ""
	@echo "To install UV, run:"
	@echo ""
	@echo "  $(CYAN)curl -LsSf https://astral.sh/uv/install.sh | sh$(NC)"
	@echo ""
	@echo "Or use:"
	@echo ""
	@echo "  $(CYAN)make install-uv-force$(NC)"
	@echo ""
	@echo "For other installation options, see:"
	@echo "  $(DIM)https://docs.astral.sh/uv/getting-started/installation/$(NC)"
	@echo ""
	@echo "After installation, you may need to update your PATH:"
	@echo "  $(YELLOW)make set-path$(NC)"
	@echo ""

# Install UV automatically
install-uv-force: ## Install UV automatically
	@echo "$(BOLD)Installing UV...$(NC)"
	@curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo ""
	@echo "$(GREEN)✓ UV installed successfully$(NC)"
	@echo ""
	@echo "You may need to update your PATH. Run:"
	@echo "  $(YELLOW)make set-path$(NC)"
	@echo ""

# Set PATH for UV
set-path: ## Add UV to PATH in shell config
	@echo ""
	@echo "$(BOLD)Setting up UV in PATH$(NC)"
	@echo ""
	@echo "Add the following to your shell configuration file:"
	@echo ""
	@if [ -n "$$ZSH_VERSION" ]; then \
		echo "For Zsh (~/.zshrc):"; \
		echo "  $(CYAN)export PATH=\"$$HOME/.local/bin:\$$PATH\"$(NC)"; \
	elif [ -n "$$BASH_VERSION" ]; then \
		echo "For Bash (~/.bashrc or ~/.bash_profile):"; \
		echo "  $(CYAN)export PATH=\"$$HOME/.local/bin:\$$PATH\"$(NC)"; \
	else \
		echo "For your shell configuration:"; \
		echo "  $(CYAN)export PATH=\"$$HOME/.local/bin:\$$PATH\"$(NC)"; \
	fi
	@echo ""
	@echo "Then reload your shell configuration:"
	@echo "  $(CYAN)source ~/.zshrc$(NC)  # or ~/.bashrc"
	@echo ""