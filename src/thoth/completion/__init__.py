"""Shell-completion package.

Per spec §5.2 of docs/superpowers/specs/2026-04-26-p16-pr3-design.md, this
package owns:
  - `script.py`   — generate `eval`-able shell init scripts
  - `install.py`  — write fenced blocks to user rc files
  - `sources.py`  — pure data functions for `shell_complete=` callbacks

The Click `completion` subcommand lives at
`src/thoth/cli_subcommands/completion.py` and imports from this package.
"""
