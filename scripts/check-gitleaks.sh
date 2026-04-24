#!/usr/bin/env bash
set -euo pipefail

# Git-hook wrapper: fails with an actionable install hint when gitleaks is
# missing, otherwise scans for secrets against .gitleaks.toml.
#
# Usage: check-gitleaks.sh [staged|full]
#   staged (default) — scan the staged diff only (pre-commit)
#   full             — scan commits ahead of upstream, falling back to full
#                      history if no upstream is configured (pre-push)

if ! command -v gitleaks >/dev/null 2>&1; then
    cat >&2 <<'EOF'
❌ gitleaks not installed — required for the secret scan.
   Install it with one of:
     just install-gitleaks           # cross-platform (brew or GitHub release)
     brew install gitleaks           # macOS / Linuxbrew
     https://github.com/gitleaks/gitleaks/releases
EOF
    exit 1
fi

mode="${1:-staged}"
case "$mode" in
    staged)
        exec gitleaks git --staged --redact --verbose --config .gitleaks.toml
        ;;
    full)
        if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
            exec gitleaks git --log-opts='@{u}..HEAD' --redact --verbose --config .gitleaks.toml
        else
            echo "gitleaks: no upstream configured — scanning full history" >&2
            exec gitleaks git --redact --verbose --config .gitleaks.toml
        fi
        ;;
    *)
        echo "gitleaks: unknown mode '$mode' (expected 'staged' or 'full')" >&2
        exit 1
        ;;
esac
