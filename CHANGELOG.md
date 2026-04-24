# Changelog

All notable changes to Thoth are documented here.

## [2.6.0](https://github.com/smorin/thoth/compare/v2.5.0...v2.6.0) (2026-04-24)


### Features

* add --skip-interactive flag to thoth_test, use in CI ([ff1761f](https://github.com/smorin/thoth/commit/ff1761f21767e44ef37450bb234598abd4e2a670))
* add best practices from thothspinner (BP-001 through BP-018) ([a7bc511](https://github.com/smorin/thoth/commit/a7bc5112a006ae871a8ca5e3f35cc5ed53224d39))
* **cli:** cooperative SIGINT handling and atomic result writes ([fc31797](https://github.com/smorin/thoth/commit/fc317979b6262ac92e43e83ceb3ae4472f0402a0))
* **cli:** print next-step hints after status/run completion ([118601a](https://github.com/smorin/thoth/commit/118601af53917cd68b6900e82a1f0fe48887fc4f))
* **config:** add config_command dispatcher with get op ([44fc105](https://github.com/smorin/thoth/commit/44fc105676be8edd8fa11ea5b52091f54b6f5068))
* **config:** add edit and help ops ([945ad3a](https://github.com/smorin/thoth/commit/945ad3a02efd17b1e8cd984e5b87ff34d62bcadf))
* **config:** add list and path ops ([4660718](https://github.com/smorin/thoth/commit/46607186854d7e42c15b66c959bb045d1c823d6e))
* **config:** add set op with tomlkit round-trip ([a9eb646](https://github.com/smorin/thoth/commit/a9eb646aaa5a5dbbf80161ec4c9a5d9c8fe8c121))
* **config:** add unset op with empty-table pruning ([7b7774f](https://github.com/smorin/thoth/commit/7b7774f19983c92f21ea148fac212b056db7fd1b))
* **config:** mask api_key values by default with --show-secrets opt-in ([50bbcd8](https://github.com/smorin/thoth/commit/50bbcd84d7fdb085cdbfe7367d52dd98c6908f2b))
* Configure Devsy setup for Python/UV project ([66845b2](https://github.com/smorin/thoth/commit/66845b2127d158d9637446ded6e31a7125e7d335))
* **config:** wire config subcommand into CLI dispatch and help system ([c836524](https://github.com/smorin/thoth/commit/c83652451879f852925836617ccd57e00011245a))
* **p06:** hybrid transient/permanent error handling with resumable recovery ([11202e2](https://github.com/smorin/thoth/commit/11202e248429222a39bfc47c333182c0064b3ea4))
* **paths:** add XDG path helpers ([e107aa5](https://github.com/smorin/thoth/commit/e107aa57499a8374c4520afedc02b8d2facb998a))
* **release:** harden release process and fix version management ([d28b9e7](https://github.com/smorin/thoth/commit/d28b9e77007ff82451ac27ac556a24437573079d))
* **test:** add pytest and vcrpy dev dependencies for VCR cassette tests ([cd4f684](https://github.com/smorin/thoth/commit/cd4f684a3429f4339cbcd433f836c6575da298cf))
* **test:** add test-vcr justfile recipe and track P05 in PROJECTS.md ([0371c5f](https://github.com/smorin/thoth/commit/0371c5f22f72d8d895465c8c6dfee18f61b53454))
* **test:** add VCR cassette replay tests for OpenAIProvider ([bb7b034](https://github.com/smorin/thoth/commit/bb7b034a2ca5da47ba9ad962247a0aa7a93061a5))
* **thoth_test:** print rerun commands for each failed test ([ac53c18](https://github.com/smorin/thoth/commit/ac53c1830f7ebf00de3c6d9601b33c1e21427916))


### Bug Fixes

* add setup-uv to yamllint CI job to fix uvx not found ([8885efe](https://github.com/smorin/thoth/commit/8885efe6d022c3bfd3f19137dc5ab2a2c31213f9))
* **ci:** add missing setup-uv step and pin devsy action ([d92c6e0](https://github.com/smorin/thoth/commit/d92c6e0c2cf42fdde0df4045cfaf3426be5bae5a))
* implement BUG-02 citation parsing and output schema fixes ([707141b](https://github.com/smorin/thoth/commit/707141bd3186e61e97ba4db2f634d75cff7c010f))
* **openai:** add container field to code_interpreter tool ([1ce0ea9](https://github.com/smorin/thoth/commit/1ce0ea92c57cd5c9b06025d880e1845af5005e5e))
* **release:** harden release script and fix documentation bugs ([273f610](https://github.com/smorin/thoth/commit/273f6101434abe7ec7b4558ecb819047ddacd672))
* resolve all ty typecheck errors in src and test suite ([9263558](https://github.com/smorin/thoth/commit/92635582e4c6b7c854d5241f9f8a318c0836385f))
* use astral-sh/setup-uv@v8.0.0 — v8 has no floating major tag ([add0bff](https://github.com/smorin/thoth/commit/add0bffd42ad2827a5683c9d16e37dfbe6ec6634))
* wrap long codespell run command to satisfy yamllint line-length ([8c7051d](https://github.com/smorin/thoth/commit/8c7051d0c81f5b19f3be18bd97992e0ee61252bd))


### Refactoring

* **auth:** unify API key resolution via resolve_api_key (CLI &gt; env &gt; config) ([6a6f099](https://github.com/smorin/thoth/commit/6a6f099a4df85c72eceb1ff92580beeaacbbec07))
* **cli:** extract next-step hint printing to thoth.hints ([7ea0b95](https://github.com/smorin/thoth/commit/7ea0b95d8ce5fc1e6fec1bea78a6e6469a0958c4))
* **config:** remove legacy Config shim; use ConfigManager directly ([fdd794e](https://github.com/smorin/thoth/commit/fdd794e479b03f1a151657e9b1bb2879c2dde585))
* **di:** thread AppContext through run loop; migrate console + signal globals ([8780e49](https://github.com/smorin/thoth/commit/8780e4961a008c2ee1014e3a7c1ef935f3f7619a))
* **hooks:** move full-project checks from pre-commit to pre-push ([c9b04a1](https://github.com/smorin/thoth/commit/c9b04a1cb364523005a69d3cf8cb33571bf12e9b))
* **openai:** map SDK exceptions to ThothError types; wire tenacity to SDK-wrapped transient errors ([b809db6](https://github.com/smorin/thoth/commit/b809db67755aa439263c8eee0a223743df9a34a6))
* **paths:** migrate all callsites from platformdirs to XDG helpers ([6c82ec5](https://github.com/smorin/thoth/commit/6c82ec5b04e9cded38dd59e74263bb1e281dc7ce))
* **providers:** split into package + collapse factories into PROVIDERS dict ([9fa295c](https://github.com/smorin/thoth/commit/9fa295c83b7bcd6de0f4460a01cdb693a1facd0e))
* **structure:** extract errors/utils/models/config modules ([5cc38e5](https://github.com/smorin/thoth/commit/5cc38e58898b3a90062713aea489d471174901c0))
* **structure:** extract run/commands/help/interactive/cli; __main__ is now a shim ([efe4ead](https://github.com/smorin/thoth/commit/efe4eaddd5e0b136e6cd85786a4a3a1857aac7b2))
* **structure:** extract signals/checkpoint/output modules ([df696cb](https://github.com/smorin/thoth/commit/df696cb619f110c5dcfaadb86bb4a3efec846b0e))


### Documentation

* add RELEASE.md adapted from thothspinner ([ce9de5a](https://github.com/smorin/thoth/commit/ce9de5a7165a22647b8162358e483c9d9b4fd949))
* **claude:** add fast-iteration-loop guidance ([3a8044d](https://github.com/smorin/thoth/commit/3a8044d79288cdbbc89648cfa26aa17f557e20f7))
* **config:** design and implementation plan for config subcommand + XDG layout ([e88bc40](https://github.com/smorin/thoth/commit/e88bc403ca3bd63389d646ac363b36af79b39d9c))
* mark P05 VCR Cassette Replay Tests complete ([b8f3b27](https://github.com/smorin/thoth/commit/b8f3b27f593b2b7c5459be5619b40120140adef0))
* **planning:** add P06/P07 plans, skipped-tests fix plan, inconsistencies notes ([9c74e62](https://github.com/smorin/thoth/commit/9c74e620ea04bb765e578dd8d42b7bfdf49f84d7))
* **projects:** add P11 modes discovery command brief ([7349a0b](https://github.com/smorin/thoth/commit/7349a0bd2c2c46a83027e2b9b85fffe35da8108d))
* **projects:** mark P10 config subcommand + XDG layout complete ([9d87fd2](https://github.com/smorin/thoth/commit/9d87fd2aaf99e5b51569abac5acc128f4c68b034))
* update README with multi-provider failures and new make targets ([6d2b931](https://github.com/smorin/thoth/commit/6d2b931f2847f2782a00ed9d34f2e74aff900105))


### CI/CD

* add editorconfig, codespell, bandit, and file-hygiene checks ([9809970](https://github.com/smorin/thoth/commit/980997052aad251557b4981ef9a774b07797bd89))
* **release:** migrate to release-please + commitlint workflow ([33cbee1](https://github.com/smorin/thoth/commit/33cbee15d9449b7e44ff45be51b1a9a96291548e))
* **security:** add trufflehog verified-secret scan ([6d51b62](https://github.com/smorin/thoth/commit/6d51b627884137eba2e0f930916bf429d550d639))


### Testing

* fix audit findings from wave 1-3 migration ([a0672d0](https://github.com/smorin/thoth/commit/a0672d0389c730d8371e4d78eff136eb69495f90))
* **fixtures:** pin UV_CACHE_DIR to real cache in run_thoth ([4a4de0a](https://github.com/smorin/thoth/commit/4a4de0a54ed754f54fb6a293a786c90670280f10))
* **imports:** pin public surface of thoth.__main__ ahead of decomposition ([98aa98d](https://github.com/smorin/thoth/commit/98aa98dbb5b55d73952b9aba08c2652ececd3e42))
* **migration:** wave 1 — migrate 27 fixture tests to pytest with xdist ([6ff352f](https://github.com/smorin/thoth/commit/6ff352f62f83211573b92bbe3bead4d3082b0aa7))
* **migration:** wave 2 — migrate 5 FS-isolated fixture tests ([e5dbe93](https://github.com/smorin/thoth/commit/e5dbe9359fbb7dfebae411d88b946761e181474e))
* **provider_config:** replace bare next() with default-None lookup ([f2933dd](https://github.com/smorin/thoth/commit/f2933dd31f399d76807bc1bbfe406bd880ac8220))
* **vcr:** add OpenAI cassette recording and supporting docs ([ae300d5](https://github.com/smorin/thoth/commit/ae300d583662ff1bb08482ce1cfba361cb93b4fc))
* **vcr:** strip org/project/request-id headers from cassette ([0295eb4](https://github.com/smorin/thoth/commit/0295eb4748fed586e06073c81aa269310808a209))
* **wave3:** migrate BUG-03 and P07-M3 fixture tests to pytest ([137c905](https://github.com/smorin/thoth/commit/137c905c66770e5d75b6b975ce0b21982ae6694f))


### Miscellaneous

* **deps:** add tomlkit for config writes ([df6bcd8](https://github.com/smorin/thoth/commit/df6bcd8fa9e83fb20b660bc10682d169fde60ae8))
* finalize P09 cleanup and update PROJECTS.md ([0a7ed5a](https://github.com/smorin/thoth/commit/0a7ed5a687fc34f83d479381b6ff3c310e9e0fd3))
* **gitignore:** ignore Claude Code local state ([c5cbb38](https://github.com/smorin/thoth/commit/c5cbb384e0b33a0d34602994af62ec118cb572e7))
* rename research reference files and update gitignore ([5c713e6](https://github.com/smorin/thoth/commit/5c713e67fb602ef8383120f731828d0fd90f24d1))
* **security:** add gitleaks pre-commit secret scan ([380218c](https://github.com/smorin/thoth/commit/380218cb2f6645b0252378e51988e168474427df))
* **security:** narrow gitleaks stopwords + extract hook wrapper ([d26c456](https://github.com/smorin/thoth/commit/d26c456bb73a0ad5e0e211a4408fdbd9b0da97c9))
* **tooling:** reduce make to bootstrap, promote just as primary task runner ([86077a0](https://github.com/smorin/thoth/commit/86077a0d1bcef6a4cc980250f5c306d9336d7201))
* update GitHub Actions to latest versions ([93937f6](https://github.com/smorin/thoth/commit/93937f6a765cf33fe066f0e4a420d018103815de))

## [Unreleased]

## [2.6.0] — In Development

### Added
- Clarification mode in interactive session (Shift+Tab toggle)
- `--clarify` flag for starting in Clarification Mode
- Virtual environment management in Makefile (`make venv`, `make venv-install`, `make venv-sync`, `make venv-clean`)
- UV export for dependency extraction

## [2.5.0]

### Added
- Operation lifecycle state machine with full checkpoint recovery
- Interactive mode with Clarification Mode support
- Enhanced signal handling for graceful shutdown with checkpoint save

## [2.2.0]

### Added
- Provider discovery (`thoth providers -- --list`, `--models`, `--keys`)
- Provider-specific API key flags (`--api-key-openai`, `--api-key-perplexity`, `--api-key-mock`)
- Enhanced metadata headers in output files (model, operation_id, created_at)

## [2.1.0]

### Added
- `providers` command for listing available providers
- Dynamic model listing from provider APIs

## [2.0.0]

### Added
- Mode chaining (clarification → exploration → deep_research with `--auto`)
- Checkpoint/resume for async operations (`thoth --resume <operation-id>`)
- Operation management (`thoth list`, `thoth status <id>`)
- Project-based output organization (`--project`)
- Async submit-and-exit mode (`--async`)

## [1.5.0]

### Added
- Core research functionality with multiple modes: `default`, `deep_research`, `clarification`, `exploration`, `thinking`
- OpenAI and Perplexity provider support
- Mock provider for testing
- Rich terminal UI with progress indicators
- Interactive prompt mode with slash commands and tab completion
- Combined report generation (`--combined`)
- Config file support (`~/.thoth/config.toml`)
