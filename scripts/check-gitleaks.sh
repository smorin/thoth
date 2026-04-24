#!/usr/bin/env bash
set -euo pipefail

# Pre-commit wrapper: fails with an actionable install hint when gitleaks is
# missing, otherwise runs the staged-secret scan against .gitleaks.toml.

if ! command -v gitleaks >/dev/null 2>&1; then
    cat >&2 <<'EOF'
❌ gitleaks not installed — required for the pre-commit secret scan.
   Install it with one of:
     just install-gitleaks           # cross-platform (brew or GitHub release)
     brew install gitleaks           # macOS / Linuxbrew
     https://github.com/gitleaks/gitleaks/releases
EOF
    exit 1
fi

exec gitleaks git --staged --redact --verbose --config .gitleaks.toml
