# Configuration Profile Pattern (CPP)

**Type:** Composition Instance — **not** a new archetype.
**Composes:** NPC (selection), BCI (overlay), FTL (cross-tier precedence), with light touches from SAM (key-level merge) and OCP (resolution ordering).
**Status:** Behavioral requirements specification.
**Personas:** Developer building a CLI tool; End User writing config files.

---

## 1. Narrative summary

A **Configuration Profile Pattern (CPP)** is a specific, opinionated way to assemble named-overlay-with-precedence behavior out of pieces already specified in the eight base archetypes. It is not a new archetype, and a library implementing it would not introduce a new code path so much as wire existing archetype primitives together along a single, well-known seam: a config file holds settings at its top level *and* one or more named profile sections, and selecting a profile causes that profile's keys to overlay onto the top-level keys.

The pattern is what users encounter under the names "profile" (AWS CLI), "context" (kubectl), "configuration" (gcloud), "workspace" (Terraform), and "stack" (Pulumi). All five share the same essential structure — a base layer of settings, a collection of named override layers, a one-of-N selection mechanism, and a precedence chain that lets a CLI invocation override either the selection or specific values within it. CPP captures that essential structure as a reusable composition.

Because CPP is a composition instance, every behavior it specifies is grounded in (or deliberately diverges from) the relevant archetype. The requirements below are written in CPP's own numbering, but each one cross-references the archetype it inherits from, so a library that already implements NPC/BCI/FTL has a clear path to compliance: most of the work is wiring, not new mechanism.

---

## 2. What CPP is and is not

### What CPP is
A *single-overlay-on-top-of-shared-base* model with a *selection precedence chain* and a *per-setting precedence chain*. Profiles are the only grouping construct; there are no nested groups, no profile-of-profiles, no inheritance.

### What CPP is not
- **Not NPC.** NPC, as a general archetype, covers any named-context switching mechanism — including kubectl-style "swap the entire context" semantics where the alternatives are mutually exclusive and there is no shared base. CPP picks one specific dialect of NPC: the AWS-style overlay-onto-shared-settings dialect.
- **Not FTL.** FTL is a tier ladder (system → user → project → ...) where lower tiers are overridden by higher ones. CPP is orthogonal: a CPP-style config can exist *at any single tier*, and CPP composes with FTL by treating each tier independently (see §10).
- **Not a profile inheritance system.** Profiles cannot extend, source, or compose with each other. AWS's `source_profile` is explicitly out of scope.
- **Not a cross-cutting design for layered config in general.** That is what the eight archetypes cover collectively. CPP is one assembly.

---

## 3. Composition lineage

| Concern | Inherited from | What CPP adds or constrains |
|---|---|---|
| Mechanism for naming and selecting one of N alternatives | **NPC** | Restricts to one-active-at-a-time; selection from a fixed precedence chain (no interactive prompt, no shell-state-driven activation). |
| Mechanism for layering one set of settings on top of another | **BCI** | Restricts to single-level overlay (profile on top-level), per-key replace (no array concatenation, no map deep-merge), no inheritance chains. |
| Behavior when the same profile name exists in multiple tiers | **FTL** | More-specific tier's profile shadows lower tiers' same-named profiles wholesale; profiles are *not* merged across tiers. |
| Per-key conflict resolution between profile and top-level | **SAM** (lightly) | Per-key replace only. SAM's full type-aware merge is out of scope. |
| Order in which CLI flag, env var, and config are consulted | **OCP** (lightly) | Two separate precedence chains (selection vs per-setting). Order is fixed by CPP; not user-configurable. |

CPP draws nothing from ADW, DFD, or DKV.

---

## 4. Real-world basis

CPP's design choices are grounded in observed behavior of mature CLIs. The dominant industry pattern for *profile selection* is **CLI flag → environment variable → in-config persisted pointer**, with two of the five major exemplars (Terraform, Pulumi) treating that order as either incomplete or inverted.

| Tool | Selection chain (high → low) | Notes |
|---|---|---|
| AWS CLI | `--profile` → `AWS_PROFILE` → `[default]` profile in config | "Command line options ... overrides settings in any other location, such as the --region, --output, and --profile parameters." [docs.aws.amazon.com/cli/v1/userguide/cli-chap-configure.html](https://docs.aws.amazon.com/cli/v1/userguide/cli-chap-configure.html) |
| kubectl | `--context` flag → `current-context` in (merged) kubeconfig | "If the --kubeconfig flag is set, use only the specified file. ... Otherwise, if the KUBECONFIG environment variable is set, use it as a list of files that should be merged. ... Otherwise, use the default kubeconfig file." [kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/) |
| gcloud | `--configuration` → `CLOUDSDK_ACTIVE_CONFIG_NAME` → persisted active configuration | "To change the active configuration for a single command invocation, you can use the --configuration flag ... To change the active configuration for all commands in your current terminal, you can set the environment variable CLOUDSDK_ACTIVE_CONFIG_NAME." [docs.cloud.google.com/sdk/docs/configurations](https://docs.cloud.google.com/sdk/docs/configurations) |
| Terraform | `TF_WORKSPACE` env → `.terraform/environment` persisted file (no per-command flag) | "Using TF_WORKSPACE allow and override workspace selection." [developer.hashicorp.com/terraform/cli/config/environment-variables](https://developer.hashicorp.com/terraform/cli/config/environment-variables) — Terraform's omission of a per-command flag is widely treated as a usability gap, not a design choice. |
| Pulumi | `PULUMI_STACK` env → `-s/--stack` flag → persisted selection | "Specifies the selected pulumi stack, overriding the stack selected with pulumi stack select STACK" [pulumi.com/docs/iac/cli/environment-variables/](https://www.pulumi.com/docs/iac/cli/environment-variables/) — the env-over-flag ordering is documented as a known wart (pulumi/pulumi#13550). |

**For per-setting overrides on top of the active profile**, all five tools converge on `flag → env → profile-applied config → built-in default`. Terraform documents this rule explicitly: "flags on the command-line take precedence over environment variables." [developer.hashicorp.com/terraform/cli/config/environment-variables](https://developer.hashicorp.com/terraform/cli/config/environment-variables). gcloud states it as "flags override properties when both are set." [docs.cloud.google.com/sdk/docs/properties](https://docs.cloud.google.com/sdk/docs/properties).

**One famous gotcha** worth designing against: AWS CLI lets individual credential env vars (`AWS_ACCESS_KEY_ID`) override a profile that was *explicitly chosen* via `--profile`. Users have filed this as a bug repeatedly (aws/aws-cli#113). The principled fix — and CPP's rule — is to keep "select the profile" and "override individual settings" as two separate, sequentially resolved chains: a per-setting env var overrides *that setting* within the chosen profile, but never silently invalidates the explicit selection.

---

## 5. Personas

### Developer (D) — building a CLI tool with this library
- D wants to expose profile-style behavior without writing the wiring themselves.
- D wants the selection precedence to match user expectations from AWS/gcloud/kubectl so users don't have to learn a new mental model.
- D wants the option to choose the env-var prefix and the in-config pointer field name, for compatibility with prior conventions.
- D wants observability: a way to ask the library "which profile is active and why was it chosen?"

### End User (U) — writing config files and invoking the CLI
- U wants to define settings once at the top level and only diverge per-profile where it actually matters.
- U wants to know, when surprised by behavior, *why* a particular value won.
- U wants the failure mode for a typo'd profile name to be loud, immediate, and obvious — not silent fallthrough.

---

## 6. Mental model

### 6.1 The two-stage resolution

CPP resolves config in two distinct stages, in order:

```
Stage 1 — Profile selection
  ┌─────────────────────────────────────────────────────────────┐
  │  (highest)                                                  │
  │     1. --profile <name>            CLI flag                 │
  │     2. <TOOL>_PROFILE              environment variable     │
  │     3. default_profile = "..."     in-config pointer        │
  │     4. (none)                      → no overlay applied     │
  │  (lowest)                                                   │
  └─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        Active profile is now bound (or explicitly absent).

Stage 2 — Per-setting resolution (for each setting independently)
  ┌─────────────────────────────────────────────────────────────┐
  │  (highest)                                                  │
  │     1. --<setting> <value>         CLI flag                 │
  │     2. <TOOL>_<SETTING>            environment variable     │
  │     3. profile-overlaid config     (see §6.2)               │
  │     4. built-in default            (compiled into the CLI)  │
  │  (lowest)                                                   │
  └─────────────────────────────────────────────────────────────┘
```

The two stages are independent. Stage 1 produces a binding (which profile, or none). Stage 2 reads that binding and resolves each setting against it.

### 6.2 Overlay semantics

When a profile is active, the *effective config* for stage 2 step 3 is computed by overlaying the profile onto the top-level settings:

```
Top-level config (always present):
  region   = "us-east-1"
  timeout  = 30
  retries  = 3

Profile [prod]:
  region   = "us-west-2"
  retries  = 5
  endpoint = "https://prod.example.com"

Effective config when profile=prod:
  region   = "us-west-2"      ← overridden by profile
  timeout  = 30               ← passes through from top-level
  retries  = 5                ← overridden by profile
  endpoint = "https://..."    ← added by profile
```

Overlay is **per-key replace**: for each key the profile defines, the profile's value replaces the top-level value wholesale. Top-level keys the profile does not mention pass through unchanged. Profile keys not present at the top level are added.

There is no merging within a key: if `region` is a string at the top level and the profile defines `region`, the profile's string replaces it. If the value is a list or map, the profile's list or map replaces it wholesale. **CPP does not deep-merge.** This is deliberate and matches BCI's "visible inheritance" guidance — the design tension nginx fell into (silent array replacement that *looked* like a merge) is avoided because CPP states the rule plainly: profiles always replace, never merge into.

### 6.3 No profile is a real state, not an alias for "defaults"

When stage 1 resolves to "no profile," the top-level config applies as-is. This is *not* a hidden default profile — it is just the absence of an overlay. Top-level settings are not labeled "default" anywhere in the file or the model; they are simply settings.

### 6.4 Cross-tier interaction (when CPP composes with FTL)

If FTL is also in use, CPP applies *within each tier independently*. Two consequences follow:

1. The active profile name is resolved once (stage 1), then *each tier searches its own profiles section* for that name.
2. If tier A and tier B both define a profile called `prod`, the more-specific tier's `prod` shadows the less-specific tier's `prod` *as a whole unit*. The two same-named profiles are **not** merged.

```
System tier config:
  log_level = "info"
  [profiles.prod]
  log_level = "warn"
  region    = "us-east-1"

User tier config (more specific):
  log_level = "debug"
  [profiles.prod]
  region    = "us-west-2"

Effective config when --profile prod, FTL favoring user tier:
  log_level = "debug"          ← user-tier top-level wins over system-tier top-level (FTL)
  region    = "us-west-2"      ← user-tier prod profile shadows system-tier prod profile wholesale
                               ← system-tier prod's log_level=warn is NOT visible
```

The shadowing is wholesale: when the user tier defines a profile named `prod`, that *is* `prod` for resolution purposes. The system tier's `prod` becomes invisible. Top-level keys in both tiers continue to compose via FTL's normal rules.

---

## 7. Design tensions

### T1 — Selection chain vs per-setting chain
A naive design fuses these into one precedence ladder ("CLI flag > env var > config"). The fusion breaks down on AWS-style edge cases where a per-setting env var silently invalidates an explicit profile choice (aws/aws-cli#113). CPP keeps the two chains separate. The cost is conceptual surface area for users; the benefit is that explicit selections are never silently overridden by ambient env state.

### T2 — Per-key replace vs deep merge
Replace is simpler to reason about, matches every major exemplar, and avoids the nginx-array-wipe class of surprise (where a user thinks they are extending and is in fact replacing). Deep merge enables more compact profile definitions but requires per-key configurability for collection types — which is BCI/SAM territory, out of scope here.

### T3 — Hard error vs silent fallthrough on missing profile
A typo in `--profile prdo` could be handled three ways: hard error, warn-and-fall-through-to-no-profile, or warn-and-fall-through-to-listed-default. AWS hard-errors. kubectl hard-errors. gcloud hard-errors. CPP follows: hard error. Silent fallthrough is dangerous because the user has *just told the tool which profile to use*; producing a different result than requested without halting is a correctness bug, not a convenience.

### T4 — In-config pointer vs no in-config pointer
Some patterns omit the in-config pointer entirely (Terraform's `.terraform/environment` is opaque state, not a user-edited field). Others (AWS's `[default]`) make the pointer implicit by special-casing a name. CPP chooses the third option: an **explicit, named field** (`default_profile = "..."`) at the top level of the config. This is more discoverable than implicit special-casing and more user-controllable than opaque state.

### T5 — `<TOOL>_PROFILE` collisions across tools
Environment variables named after profiles are global and unscoped. If both `mytool` and `othertool` use `MYTOOL_PROFILE` and `OTHERTOOL_PROFILE`, no collision; but if a user ever runs both under wrappers that re-export, prefix discipline matters. CPP requires that the prefix be tool-specific and configurable by the developer.

### T6 — When the user defines a profile with the same name as a reserved word
If a user names their profile `default_profile`, or uses a key name that collides with the in-config pointer field, the parser's discrimination of "is this the pointer or the profile?" depends on the config file format and the section structure. CPP requires that the pointer live at the top level (not inside a profile section) and that profile names avoid reserved-key collisions in the configured format.

---

## 8. Behavioral requirements

Five categories: **CORE** (the central mechanism), **VALIDATION** (constraints and errors), **EXTENSION** (developer-facing customization), **OBSERVABILITY** (introspection), **UX** (end-user experience).

### CORE

**REQ-CPP-001 — Top-level settings exist independently of profiles**
- **WHO:** End User
- **WHAT:** A config file MUST be valid and resolvable with no profiles defined at all. Settings declared at the top level of the config are simply settings; they are not labeled "default" or "defaults" by the model, the format, or the documentation.
- **WHY:** Users frequently start with a single flat config and adopt profiles later. The model must not require restructuring the file when profiles are introduced. Inherits from BCI's principle that the base layer is meaningful on its own.

**REQ-CPP-002 — Named profile sections overlay onto top-level settings**
- **WHO:** End User, Developer
- **WHAT:** A profile is a named section of the config file containing key-value settings. When a profile is active, its keys are overlaid onto the top-level keys via per-key replace (see REQ-CPP-005).
- **WHY:** This is the central behavior of the pattern. Inherits from NPC (named context) and BCI (overlay).

**REQ-CPP-003 — Profile selection precedence chain (Stage 1)**
- **WHO:** End User, Developer
- **WHAT:** The active profile MUST be resolved in this order, with the first match winning:
  1. The `--profile <name>` CLI flag (or whatever flag name the developer configured)
  2. The `<TOOL>_PROFILE` environment variable
  3. The `default_profile` field at the top level of the config
  4. None — no overlay is applied; only top-level settings are in effect
- **WHY:** Matches the AWS/kubectl/gcloud convention. Users coming from those tools should not need to learn a new model.

**REQ-CPP-004 — Per-setting precedence chain (Stage 2)**
- **WHO:** End User, Developer
- **WHAT:** After Stage 1 binds the active profile (or determines its absence), each setting's value MUST be resolved in this order:
  1. CLI flag for that specific setting (e.g., `--timeout 30`)
  2. Environment variable for that specific setting (e.g., `<TOOL>_TIMEOUT`)
  3. Profile-overlaid config value: profile's value if the profile defines this key, else top-level value if defined, else step 4
  4. Built-in default compiled into the CLI
- **WHY:** Standard CLI precedence chain, taught universally. Keeping it separate from Stage 1 prevents per-setting env vars from silently invalidating an explicit `--profile` selection (the AWS aws/aws-cli#113 wart).

**REQ-CPP-005 — Per-key replace overlay (no merge)**
- **WHO:** End User, Developer
- **WHAT:** When a profile defines a key, the profile's value replaces the top-level value for that key wholesale. There is no merging within a key, regardless of value type (scalar, list, map, nested structure). Lists are not concatenated; maps are not deep-merged.
- **WHY:** Simplest model that reasons cleanly. Matches AWS, gcloud, kubectl context behavior. Avoids the nginx-array-wipe surprise by stating the rule plainly rather than letting it emerge from implementation. Inherits from BCI's "make collection merge strategy explicit" guidance.

**REQ-CPP-006 — Profile may add keys not present at the top level**
- **WHO:** End User
- **WHAT:** A profile MAY define keys that do not appear in the top-level settings. Such keys are present in the effective config when the profile is active and absent when it is not.
- **WHY:** Common pattern — e.g., `endpoint` only matters for a non-default environment. Inheriting from BCI overlay semantics.

**REQ-CPP-007 — One profile active at a time**
- **WHO:** End User, Developer
- **WHAT:** At most one profile MAY be active for any given invocation of the CLI. Multiple profiles cannot be composed, layered, or merged.
- **WHY:** Composition of profiles is a separate, more complex pattern (closer to OCP). CPP deliberately excludes it to keep the model small. Inherits from NPC's one-of-N semantics.

**REQ-CPP-008 — No profile inheritance**
- **WHO:** End User, Developer
- **WHAT:** A profile MUST NOT extend, source, or otherwise inherit from another profile. There is no `source_profile`, `extends`, or analogous mechanism.
- **WHY:** Inheritance turns a flat selection model into a graph with resolution order, cycles, and shadowing complexity. Out of scope for CPP. (AWS's `source_profile` is a distinct feature that CPP intentionally does not include.)

### VALIDATION

**REQ-CPP-101 — Hard error on missing profile**
- **WHO:** End User, Developer
- **WHAT:** If Stage 1 resolves to a profile name (via flag, env var, or `default_profile`) that does not exist in the config, the library MUST raise an error and halt. It MUST NOT silently fall back to "no profile" or to any other profile.
- **WHY:** A user who said `--profile prdo` (typo) expects to be told. Silent fallthrough produces results different from what was asked for and is a correctness bug. Matches AWS, kubectl, gcloud behavior. See T3.

**REQ-CPP-102 — Profile name validation**
- **WHO:** Developer
- **WHAT:** The library MUST reject profile names that cannot be expressed as section names in the configured file format. For TOML, this means valid bare key syntax or quoted strings. For YAML, valid map keys. Names that collide with the `default_profile` pointer field (or other reserved top-level keys) at the same nesting level MUST be rejected.
- **WHY:** Round-trip safety: a name a user types on the command line must be writable in the config without escaping ambiguity.

**REQ-CPP-103 — `default_profile` field validation**
- **WHO:** End User, Developer
- **WHAT:** If the config defines `default_profile`, its value MUST be a string referring to a profile defined in the same config file. If the referenced profile does not exist, the library MUST raise the same hard error as REQ-CPP-101 *at config load time*, not lazily at first use.
- **WHY:** Errors at load time are far more debuggable than errors deferred until a particular code path runs.

**REQ-CPP-104 — Reserved profile names**
- **WHO:** Developer
- **WHAT:** The library MUST NOT special-case any profile name (e.g., there is no privileged `default` profile name, no `current`, no `_global`). Every profile is on equal footing.
- **WHY:** AWS's `[default]` profile is a notable source of confusion — users wonder whether `default` is a profile or a special case. CPP avoids this by treating top-level settings as the unprofiled base and giving them no name at all.

### EXTENSION

**REQ-CPP-201 — Configurable env-var prefix**
- **WHO:** Developer
- **WHAT:** The developer MUST be able to configure the env-var prefix used for both profile selection (`<PREFIX>_PROFILE`) and per-setting overrides (`<PREFIX>_<SETTING>`). The default prefix MUST be derived from the binary name uppercased.
- **WHY:** Different tools have different conventions; the library should not force `MYBIN_PROFILE` if the developer has standardized on something else (e.g., a shorter prefix, a project-style prefix).

**REQ-CPP-202 — Configurable in-config pointer field name**
- **WHO:** Developer
- **WHAT:** The developer SHOULD be able to configure the field name used for the in-config pointer. Default: `default_profile`. Reasonable alternatives a developer might choose: `active_profile`, `profile`, `current_profile`.
- **WHY:** Allows alignment with prior tool conventions or domain vocabulary. The library has an opinion (`default_profile`) but does not impose it.

**REQ-CPP-203 — Configurable CLI flag name**
- **WHO:** Developer
- **WHAT:** The developer MUST be able to configure the CLI flag name used for profile selection. Default: `--profile`. The library MUST NOT hardcode the flag name into the resolution machinery; it MUST accept the resolved profile name as input from whatever the developer's CLI parser produces.
- **WHY:** Some tools use `--context`, `-s`, `--configuration`, etc. The library provides the resolution model, not the flag-parsing layer.

**REQ-CPP-204 — Per-setting env var derivation rule is configurable**
- **WHO:** Developer
- **WHAT:** The developer SHOULD be able to override how individual setting env vars are derived from setting names (default: `<PREFIX>_<UPPER_SNAKE_SETTING_NAME>`). For example, gcloud uses `CLOUDSDK_<SECTION>_<NAME>` (two-component); a developer building a tool with a similar shape needs to express that.
- **WHY:** No single derivation rule fits all tools.

### OBSERVABILITY

**REQ-CPP-301 — Report active profile and selection source**
- **WHO:** End User, Developer
- **WHAT:** The library MUST expose, at runtime, both (a) the name of the active profile (or the explicit absence of a profile) and (b) which Stage 1 step was the source — `flag`, `env`, `config_pointer`, or `none`.
- **WHY:** When a user is surprised by behavior, the first question is "which profile am I actually running with, and why?" Equivalent to gcloud's `gcloud config configurations list` showing `IS_ACTIVE` plus the user being able to see `CLOUDSDK_ACTIVE_CONFIG_NAME`.

**REQ-CPP-302 — Report effective (overlaid) config**
- **WHO:** End User, Developer
- **WHAT:** The library MUST expose the effective config — the per-key result of Stage 2 — for inspection, including, for each key, the resolution source: `cli_flag`, `env_var`, `profile`, `top_level`, or `built_in_default`.
- **WHY:** The other half of "why did the tool do that?" — once the profile is known, users need to see which level supplied each individual value. AWS CLI partially exposes this via `aws configure list`; CPP requires it as a baseline capability.

**REQ-CPP-303 — Diagnostic on profile shadowing across tiers**
- **WHO:** End User
- **WHAT:** When CPP is composed with FTL and a profile name is defined in more than one tier, the library SHOULD be able to report which tier supplied the active profile and which tiers had same-named profiles that were shadowed.
- **WHY:** Shadowing is invisible by default and is a common confusion source. Surfacing it on demand is cheap; surfacing it always is noisy. The "SHOULD" allows a `--debug-profiles` style flag rather than mandatory chatty output.

### UX

**REQ-CPP-401 — Listing available profiles**
- **WHO:** End User
- **WHAT:** The library SHOULD support enumerating the profiles defined in the resolved config (across tiers, when composed with FTL). Each entry in the listing SHOULD indicate which tier provided it and whether it is shadowed by a more-specific tier's same-named profile.
- **WHY:** Discoverability. Users cannot select what they cannot see.

**REQ-CPP-402 — Migration: adding profiles to a profileless config**
- **WHO:** End User
- **WHAT:** Adding a profile section to a previously profileless config MUST NOT change the effective config when no profile is selected. A user with no `--profile`, no `<TOOL>_PROFILE`, and no `default_profile` MUST get exactly the same behavior before and after profiles are added to the file.
- **WHY:** A library that silently changes behavior on the addition of an unrelated section breaks user trust. Inherits from REQ-CPP-001's principle that top-level settings stand alone.

**REQ-CPP-403 — Migration: removing a profile**
- **WHO:** End User
- **WHAT:** When a profile referenced by `default_profile` is removed from the config without `default_profile` also being removed or updated, the library MUST raise REQ-CPP-103's hard error at load time, with an error message that names the dangling reference.
- **WHY:** Silent recovery here would mean the user thinks they are running with profile X but is in fact running with bare top-level settings — an outcome that may or may not be acceptable, but should never be hidden.

**REQ-CPP-404 — Error messages name the source**
- **WHO:** End User
- **WHAT:** Errors arising from CPP resolution (missing profile, dangling pointer, invalid name) MUST include in their messages the *source* of the offending value (`--profile flag`, `<TOOL>_PROFILE env var`, `default_profile in /path/to/config.toml`).
- **WHY:** Three places to set the profile means three places to typo it. Naming the source in the error reduces resolution time from minutes to seconds.

**REQ-CPP-405 — No interactive prompts during resolution**
- **WHO:** End User, Developer
- **WHAT:** Profile selection MUST NOT trigger interactive prompts during normal resolution. If no profile is selected and there is no `default_profile`, the result is "no profile" — not a prompt to choose one.
- **WHY:** Pulumi's interactive stack-selection prompt is widely treated as a non-automation-friendly behavior (pulumi/pulumi#13550). CPP-using tools should be CI-safe by default.

---

## 9. Concrete example

A hypothetical CLI `synth` with a config at `~/.config/synth/config.toml`:

```toml
# Top-level settings — apply when no profile is active and as the base for any profile overlay.
log_level = "info"
timeout   = 30
retries   = 3
endpoint  = "https://api.synth.example.com"

# Pointer: if neither --profile nor SYNTH_PROFILE is set, this is the active profile.
default_profile = "dev"

[profiles.dev]
log_level = "debug"
endpoint  = "https://dev.synth.example.com"

[profiles.staging]
endpoint  = "https://staging.synth.example.com"
retries   = 5

[profiles.prod]
endpoint  = "https://prod.synth.example.com"
retries   = 10
timeout   = 60
audit     = true   # Adds a key not present at the top level.
```

### Resolution traces

**Invocation:** `synth deploy` (no flag, no env var)
- Stage 1: `flag=∅`, `env=∅`, pointer=`"dev"` → active profile is `dev`
- Stage 2 (effective config):
  - `log_level` = `"debug"` (from profile)
  - `timeout` = `30` (passes through from top-level)
  - `retries` = `3` (passes through from top-level)
  - `endpoint` = `"https://dev.synth.example.com"` (from profile)

**Invocation:** `SYNTH_PROFILE=prod synth deploy --timeout 120`
- Stage 1: `flag=∅`, `env="prod"` → active profile is `prod` (env beats config pointer)
- Stage 2:
  - `log_level` = `"info"` (top-level; profile doesn't override)
  - `timeout` = `120` (CLI flag wins over profile's `60`)
  - `retries` = `10` (from profile)
  - `endpoint` = `"https://prod.synth.example.com"` (from profile)
  - `audit` = `true` (added by profile)

**Invocation:** `SYNTH_PROFILE=prod synth deploy --profile dev`
- Stage 1: `flag="dev"` → active profile is `dev` (flag beats env)
- Stage 2:
  - `log_level` = `"debug"` (from profile)
  - `timeout` = `30` (top-level)
  - `retries` = `3` (top-level)
  - `endpoint` = `"https://dev.synth.example.com"` (from profile)
  - `audit` = absent (not in `dev` profile, not at top level)

**Invocation:** `synth deploy --profile typo`
- Stage 1: `flag="typo"` → resolution attempts to bind, no `[profiles.typo]` exists
- **Hard error**: `"profile 'typo' not found (from --profile flag); available profiles: dev, staging, prod"`

---

## 10. Composition notes

How CPP interacts with each of the eight base archetypes.

### FTL (Fixed-Tier Override Ladder)
**Composes naturally.** CPP applies within each tier; FTL composes the per-tier resolutions. Two specific behaviors:
1. The active profile name resolved in Stage 1 is consulted independently in each tier — each tier looks for that name in its own `[profiles.*]` sections.
2. Same-named profiles in different tiers do **not** merge; the more-specific tier's profile shadows wholesale (per the user's explicit decision; see §6.4).
The `default_profile` pointer follows FTL's normal scalar-key resolution: the more-specific tier's `default_profile` wins.

### ADW (Ancestor Directory Walk)
**Light interaction.** When ADW is in use to discover configs along a directory chain, each discovered config can contribute its own `[profiles.*]` sections. The resolution model in §6.4 applies, treating each ADW-discovered config as a tier. The library should document whether an ADW-discovered config closer to `cwd` is "more specific" (it usually is) and apply CPP shadowing accordingly.

### NPC (Named Profile/Context Switching)
**Direct ancestor.** CPP is one specific dialect of NPC. A library implementing NPC in full generality will need to expose configuration knobs (overlay vs. replace-whole-context, single-active vs. multi-active, inheritance vs. flat). CPP picks one point in that configuration space. Implementations may share the underlying mechanism between CPP and full NPC; they differ in defaults and constraints.

### DFD (Drop-in Fragment Directory)
**Light interaction.** A DFD-style fragment directory can contribute additional `[profiles.*]` sections. The library must decide how same-named profiles across fragments resolve; the simplest answer (and the one consistent with CPP's "no merge" stance) is: hard error on duplicate, or last-writer-wins by lexical fragment ordering. This is a DFD design decision, not a CPP one.

### OCP (Ordered Composition Pipeline)
**Light interaction.** OCP is about ordered composition of multiple sources. CPP's two-stage resolution can be viewed as a fixed-shape OCP pipeline (Stage 1 produces a binding, Stage 2 consumes it). A library implementing both can share machinery, but CPP fixes the shape rather than letting the developer reorder.

### BCI (Block/Context Inheritance)
**Direct ancestor.** CPP's overlay semantics are a constrained BCI: single-level (no chain), per-key replace (no nested merge), no array concatenation (per the BCI guidance about making collection merge explicit and configurable — CPP's choice is "always replace"). A library that already implements BCI in full generality has CPP for free at the appropriate restriction.

### SAM (Schema-Aware Merge)
**Out of direct scope; lightly relevant.** SAM enables type-aware per-key merge strategies. CPP deliberately does not engage with merge strategies — every key replaces. A future extension to CPP that wanted profile arrays to *concatenate* with top-level arrays for some specific keys would be entering SAM territory and should be specified there, not as an extension to CPP.

### DKV (Distributed Key-Value Store with Watches)
**No interaction.** DKV is a different shape entirely (live, watched, distributed). CPP is a static-config-file pattern.

---

## 11. Out of scope

Explicitly **not** part of CPP:

- **Profile inheritance** (`source_profile`, `extends`). See REQ-CPP-008 and §10/SAM.
- **Multiple simultaneously active profiles.** See REQ-CPP-007.
- **Deep merging within a key.** See REQ-CPP-005 and §10/SAM.
- **Interactive selection prompts.** See REQ-CPP-405.
- **A privileged "default" profile name.** See REQ-CPP-104.
- **Live reload of profile selection mid-process.** Resolution happens once at startup; runtime profile switching is not specified.
- **Programmatic profile management** (creating/deleting/editing profiles via the library API). CPP specifies *resolution*; CRUD is a separate concern.
- **Credential providers, assume-role chains, or other auth-specific behaviors** that some tools layer on top of profiles. Secrets in CPP are just values; auth machinery is out of scope.

---

## 12. Glossary

- **Top-level settings** — keys defined at the root of the config file, outside any profile section. They apply when no profile is active and serve as the base layer for any profile overlay. Not labeled "default" anywhere in the model.
- **Profile** — a named section of the config file containing settings that overlay onto the top-level settings when active.
- **Active profile** — the single profile bound by Stage 1 resolution, if any. May be explicitly absent.
- **Effective config** — the per-key result of Stage 2 resolution; the values the CLI actually uses.
- **Overlay** — the per-key replace operation that produces the profile-applied view of the config (Stage 2 step 3).
- **`default_profile`** — the field name (at the top level of the config) that points to the profile to be used when neither `--profile` nor `<TOOL>_PROFILE` is set. Configurable per REQ-CPP-202.
- **Selection precedence chain (Stage 1)** — `--profile` flag → `<TOOL>_PROFILE` env → `default_profile` in config → none.
- **Per-setting precedence chain (Stage 2)** — `--<setting>` flag → `<TOOL>_<SETTING>` env → profile-overlaid config → built-in default.
- **Shadowing** — when CPP is composed with FTL and the same profile name exists in multiple tiers, the more-specific tier's profile replaces the less-specific tier's profile wholesale (no merge).

---

## 13. References

- AWS CLI configuration precedence: [docs.aws.amazon.com/cli/v1/userguide/cli-chap-configure.html](https://docs.aws.amazon.com/cli/v1/userguide/cli-chap-configure.html)
- AWS CLI command-line options: [docs.aws.amazon.com/cli/v1/userguide/cli-configure-options.html](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-options.html)
- AWS CLI env vars: [docs.aws.amazon.com/cli/v1/userguide/cli-configure-envvars.html](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-envvars.html)
- AWS CLI variable precedence (incl. profile env interaction): [docs.aws.amazon.com/cli/latest/topic/config-vars.html](https://docs.aws.amazon.com/cli/latest/topic/config-vars.html)
- AWS aws/aws-cli#113 (env vars overriding explicit `--profile`): [github.com/aws/aws-cli/issues/113](https://github.com/aws/aws-cli/issues/113)
- AWS aws/aws-cli#5016 (flag vs env precedence): [github.com/aws/aws-cli/issues/5016](https://github.com/aws/aws-cli/issues/5016)
- kubectl kubeconfig resolution: [kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)
- kubectl multi-cluster access: [kubernetes.io/docs/tasks/access-application-cluster/configure-access-multiple-clusters/](https://kubernetes.io/docs/tasks/access-application-cluster/configure-access-multiple-clusters/)
- gcloud configurations: [docs.cloud.google.com/sdk/docs/configurations](https://docs.cloud.google.com/sdk/docs/configurations)
- gcloud properties (flag-vs-property precedence): [docs.cloud.google.com/sdk/docs/properties](https://docs.cloud.google.com/sdk/docs/properties)
- Terraform CLI environment variables (incl. `TF_WORKSPACE`, flag-vs-env rule): [developer.hashicorp.com/terraform/cli/config/environment-variables](https://developer.hashicorp.com/terraform/cli/config/environment-variables)
- Pulumi CLI environment variables (incl. `PULUMI_STACK`): [pulumi.com/docs/iac/cli/environment-variables/](https://www.pulumi.com/docs/iac/cli/environment-variables/)
- Pulumi pulumi/pulumi#13550 (env-over-flag wart): [github.com/pulumi/pulumi/issues/13550](https://github.com/pulumi/pulumi/issues/13550)
