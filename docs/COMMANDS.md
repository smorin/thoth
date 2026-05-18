# Commands reference

Full CLI surface for `doxa` / `doxa-research`. Run `doxa <command> --help`
for the authoritative per-command help.

## Main commands

| Command | Description | Example |
|---------|-------------|---------|
| (default) | Run research with prompt | `doxa "your research prompt"` |
| `ask` | Run research with an explicit subcommand | `doxa ask "your research prompt"` |
| `resume` | Resume a checkpointed operation | `doxa resume research-20260518-093412-xxx` |
| `cancel` | Cancel an in-flight background operation | `doxa cancel research-20260518-093412-xxx` |
| `init` | Setup wizard for API keys and config | `doxa init` |
| `status` | Show operation details | `doxa status research-20260518-093412-xxx` |
| `list` | Show recent operations | `doxa list` |
| `config` | Inspect and edit configuration | `doxa config get general.default_mode` |
| `modes` | List research modes | `doxa modes list` |
| `providers` | Manage providers and models | `doxa providers list` |
| `completion` | Generate shell completion scripts | `doxa completion zsh` |
| `help` | Show help information | `doxa help [COMMAND]` |

## `providers` subcommands

| Subcommand | Description | Example |
|------------|-------------|---------|
| `list` | Show available providers and status | `doxa providers list` |
| `models` | List models from providers | `doxa providers models` |
| `check` | Show API key configuration | `doxa providers check` |
| `--provider`, `-P` | Filter by specific provider | `doxa providers models -P openai` |

## See also

- [README.md](../README.md) — start here
- [docs/providers.md](providers.md) — per-provider configuration details
- [docs/json-output.md](json-output.md) — `--json` envelope contract
