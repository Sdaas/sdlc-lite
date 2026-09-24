# Authoring and running evals for `sdlc-lite`

How to write a `claude plugin eval` case, choose graders, run the suite, and read the result.

This is the **how**. For *how much* verification a given change owes — which tier, which budget —
see **[`verification-ladder.md`](verification-ladder.md)**; T1 on that ladder is this tool.

> `claude plugin eval` has **no public documentation page**. Everything here was read out of the
> reference that ships compressed inside the `claude` binary (`references/plugin-eval-quickref.md`
> and `references/plugin-eval.md`). If something below disagrees with your build, the binary wins —
> `claude plugin eval --help` is the other check.

---

## 1. Where evals run, and why

**Evals run in the dev container** ([`DEVCONTAINER.md`](DEVCONTAINER.md)), like everything else that
tests this plugin. The Mac host can run *some* cases and is useful for fast iteration, but it is a
convenience, not the harness. This section explains why — the reason is specific and worth
understanding, because it also tells you something about what a T1 case should be.

### First: `plugin eval` is early access, and gated **off** by default

It prints `` `plugin eval` is currently in early access `` and exits 1. The command exists — it is
not missing, and `claude update` alone does not turn it on.

```bash
export CLAUDE_CODE_WALNUT_SPIRE=1
```

It must be set in the **shell / CI environment**, in `~/.claude/settings.json` under `env`, or in
managed settings. **A value in this repo's `.claude/settings.json` does not work** — project
settings only apply pre-trusted, allowlisted variables, and this one is not allowlisted. Never
commit it there.

**Self-test**, in an empty directory:

```bash
cd "$(mktemp -d)" && claude plugin eval
#  "... early access"      -> still gated off
#  "No eval cases found"   -> enabled
```

### Why the container: a "Bash-granting" case cannot run on the Mac host

#### What "Bash-granting" means

A case is **Bash-granting** when the run ends up with the `Bash` tool available *in any form*. Two
things must line up, and the second is easy to forget:

```markdown
---
# the case ASKS, in prompt.md
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
```

```bash
# the operator GRANTS, on the command line
claude plugin eval sdlc-lite-plugin --allow-tools Bash
```

Read-only tools (`Read`, `Glob`, `Grep`, `Skill`, `TodoWrite`, `Agent`) are granted automatically.
`Bash`, `Write`, `Edit`, `WebFetch`, `WebSearch` and `mcp__*` are not.

Narrowing the grant does **not** exempt you — a command-prefix grant is still a Bash grant:

| Grant | Bash-granting? |
|---|---|
| `--allow-tools Bash` | yes |
| `--allow-tools "Bash(pytest:*)"` | yes — still Bash |
| `--allow-tools "Bash(printf:*)"` | yes — even `printf` |
| `--allow-tools Write Edit` | no |
| nothing (a read-only case) | no |

#### What granting Bash switches on

When `Bash` is granted, every command the agent runs is wrapped in **Claude Code's own OS-level
sandbox** — seatbelt on macOS, bubblewrap + `socat` on Linux. Its contract:

- **writes** only inside the run's throwaway `home/` and `tmp/`
- **reads** limited to the sandbox, the plugin under test and any `add_dirs` — and explicitly *not*
  your real home, your real `~/.claude`, or **any credential store**
- **network** only to domains an explicit `WebFetch(domain:…)` grant names

That policy is expressed as **filesystem path rules**, and the harness is deliberately
**fail-closed**: if it cannot construct a *reliable* exclusion for a credential store, it refuses to
run the evaluation rather than running your agent unconfined.

#### Why `~/.docker` is what trips it

`~/.docker` is on the must-exclude list because it is a **credential store** — on this machine
`~/.docker/config.json` carries `auths` (registry credentials) and `credsStore` (a pointer to the
Keychain helper). None of this involves the Docker *daemon*, or our dev container; it is only about
a directory full of secrets that the sandbox is required to hide.

And Docker Desktop fills that directory with symlinks, because it keeps its binaries inside the app
bundle and links them into your home so `docker compose` works:

```
~/.docker/cli-plugins/docker-buildx -> /Applications/Docker.app/Contents/Resources/cli-plugins/docker-buildx
~/.docker/cli-plugins/docker-pass   -> /Applications/Docker.app/Contents/Library/SecretsEngine/docker-pass.app/…/docker-pass
```

All 14 entries are links like these — `docker-pass` is literally the credential helper.

**Path rules and symlinks do not compose.** A deny rule on `~/.docker` covers that *name*. A symlink
gives the same bytes a second name, and the links can point either way — out of the store, or into
it from somewhere allowed. The policy language cannot express "deny everything that resolves here,
under any name", so the harness refuses:

```
error: the Docker (~/.docker, DOCKER_CONFIG) credential store on this machine holds a symbolic
link inside it, so the Bash sandbox cannot reliably exclude it — a Bash-granting evaluation
cannot run here
```

Nothing is misconfigured on either side: Docker Desktop's layout is its standard install, and a
fail-closed sandbox refusing an exclusion it cannot prove is correct behavior.

**`DOCKER_CONFIG` does not rescue it.** That variable only tells the docker CLI where to look; it
does not move or unpublish `~/.docker`, so the credentials are still there and the harness still
checks it. Tested — don't spend an afternoon rediscovering it. Deleting the symlinks would break
Docker Desktop, which recreates them anyway.

#### What follows

- **Run evals in the dev container.** It has `bwrap` + `socat`, no Docker Desktop and no
  `~/.docker`. It is also already this repo's test harness, so nothing new is being introduced.
  **One prerequisite, easy to miss:** the container must run with
  `--security-opt seccomp=unconfined` and `--security-opt systempaths=unconfined` (set in
  `devcontainer.json`). Docker's defaults stop `bwrap` from creating a user namespace and mounting
  `/proc`, and then *every* sandboxed Bash call fails with
  `bwrap: No permissions to create a new namespace` — the agent reports "Bash is non-functional"
  and the case scores low for a reason that has nothing to do with the plugin. Why the flags are
  safe enough: [`DEVCONTAINER.md`](DEVCONTAINER.md) → *Two loosened Docker defaults*.
- **The host is for fast iteration on read-only cases.** The routing and guard cases never need
  Bash, and running them on the Mac while you get the graders right is quicker than a container
  round trip. Just don't mistake a green host run for a suite run.
- **Grant `Bash` when the workflow itself needs it, and grade the trace rather than shell output.**
  Every case that types `/implement-feature` is Bash-granting, because Gate 0's preflight, lock
  check and branch detection are shell commands. A case that wants a real `pytest` or `mutmut` to
  *finish* is a different thing — close to what the ladder calls **T3**, where the container and a
  human already are. Prefer `tool_used` on the trace and produced files over shell output.

### The sandbox is emptier than you expect

Each run gets a throwaway `HOME` and `CLAUDE_CONFIG_DIR`, runs under `--setting-sources user`, and
loads **only the plugin under test**. No `CLAUDE.md` (disabled outright), no project or user
settings, no hooks of your own, no other plugins, no MCP servers, no memory. The Artifact tool is
unavailable in-run. See `verification-ladder.md` § 5 — a bug that needs project config is not
reproducible here at all.

---

## 2. Anatomy of a case

A case is a directory under `sdlc-lite-plugin/evals/`. Minimum: a `prompt.md`.

```
sdlc-lite-plugin/evals/
  <case-name>/
    prompt.md            frontmatter -> case fields; body -> the prompt
    graders/
      <grader>.md        frontmatter -> grader fields; body -> pattern or rubric
    case.yaml            optional — ONLY for fields prompt.md cannot carry
```

Cases run in lexicographic order. A directory that is not a case (shared fixtures, a grouping
folder) is skipped and searched beneath.

### `prompt.md`

```markdown
---
name: routing-feature-request
description: A plain feature request must NOT auto-start the workflow
tags: [routing, entry-point]
plugins: ["../.."]
runs: 3
max_turns: 12
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

Add a --json flag to the exporter in this repo.
```

Frontmatter keys are exact and snake_case: `schema_version`, `name`, `description`, `tags`,
`plugins`, `runs`, `expected_outcome`, `model`, `max_turns`, `timeout_seconds`, `allowed_tools`,
`append_system_prompt`, `env`. Any other key is an error. Defaults: `runs: 3`, `max_turns: 10`,
`timeout_seconds: 300`.

Two that matter for this plugin specifically:

- **`plugins: ["../.."]`** — the path from the case directory to `sdlc-lite-plugin/`. Set it
  explicitly; auto-detection is not guaranteed for every layout, and without a resolved plugin the
  baseline arm compares nothing to nothing.
- **`allowed_tools`** — read-only tools (`Read`, `Glob`, `Grep`, `Skill`, `TodoWrite`, `Agent`, …)
  are granted automatically. **`Bash`, `Write`, `Edit`, `WebFetch`, `WebSearch` and `mcp__*` also
  need the operator to pass `--allow-tools`** on the command line. A case that asks for one without
  the grant is reported as not granted.

`env` keys must match `EVAL_[A-Z0-9_]*`; anything else fails the run.

### `case.yaml` — only when you need `context.*`

`prompt.md` cannot express `context.scaffold_script`, `context.history_file` or `context.add_dirs`.
Those need a `case.yaml` beside it, which must then also carry `schema_version: "1.1"` and `name`.
`case.yaml` is the base document; `prompt.md` frontmatter overrides it, and its body is the prompt.

---

## 3. Writing a case that is worth running

Six rules. They are what separate a case that catches a real prose regression from one that passes
forever regardless.

**1. Phrase it the way a user would type it, and never name the skill.** The case is meant to prove
the prose routes correctly, not that a named invocation works. `"Add a --json flag to the
exporter"` — not `"run /implement-feature"`.

**2. Write the case before the prose it verifies.** Run it first; it should fail, or pass for the
wrong reason. That is this repo's "red" (`verification-ladder.md` § 6). A case written afterwards
tends to encode what you already did rather than what you meant.

**3. Never leak the answer into the prompt.** `"Check that the gate refuses to commit without
approval"` tells the agent what to do; it grades nothing. Set the situation up and let the graders
assert the outcome.

**4. Two graders per case: one on the result, one on the mechanism.** The result grader looks at the
final message or a produced file; the mechanism grader (`tool_used` / `tool_order`) looks at the
trace. A case with only a result grader passes when the agent gets there the wrong way.

**5. At least one should-not-fire case in the suite.** This plugin's skills are **explicit-entry
only** — the model must never start the workflow on its own. That is asserted with:

```markdown
---
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?implement-feature"'
min: 0
max: 0
arm: both
---
```

`min: 0, max: 0` is the "must not call" idiom — `max: 0` alone can never pass, because `min` stays
1. **`arm: both` is required here**: under `--ablation with-without`, `tool_used` graders on `Skill`
are otherwise dropped from the baseline arm and excluded from the score, which would silently
un-score the one case whose whole point is a negative.

**6. Prefer free graders over `llm` ones, especially on long output.** Judges get noisy above a few
thousand characters (the harness itself warns past ~8000). A `regex` over `{source: file}` scans the
whole file exactly and costs nothing.

---

## 4. Graders

Every grader has `type`, a name (the filename in prose layout), `weight` (default 1) and optional
`arm`. Structural graders are free; `llm` and `baseline` call a judge model three times each.

| Type | Key fields | Passes when |
|---|---|---|
| `regex` | `pattern`, `flags`, `match: contains \| not_contains \| count:N`, `target` | The pattern is (or is not) found; `count:N` requires exactly N |
| `tool_used` | `tool`, `input_match`, `min` (default 1), `max` | The number of matching calls falls within `min..max` |
| `tool_order` | `before`, `after` (a tool name, or `{tool, input_match}`) | The first matching `before` call precedes the first matching `after` |
| `file_exists` | `path` (glob), `exists` | A file **created during the run** matches |
| `llm` | `criteria`, `focus` | A judge votes PASS at least 2 of 3 |
| `baseline` | `baseline_file`, `criteria` | The new trajectory is judged no worse than a recorded one |

**What a grader can look at** — `target` for `regex`, `focus` for `llm`:

| Value | Content |
|---|---|
| `last_message` (default) | The agent's final assistant text |
| `trace` | The whole session, one JSON message per line — **quotes are JSON-escaped, so match `\"`, not `"`** |
| `files` | The list of file **paths** created during the run — not contents, and not files that merely changed |
| `{source: file, path: <p>}` | The **contents** of one file in the sandbox workspace after the run |
| `mock_calls` | Calls made to mocked MCP tools |

Two idioms this repo uses constantly:

```markdown
---
# did the skill fire at all?
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?implement-feature"'
min: 1
---
```

```markdown
---
# did it reach Gate 0 and stop there, rather than improvising?
type: regex
pattern: 'Preflight passed'
target: last_message
---
```

`file_exists` only sees files **created** during the run — not ones a scaffold made, and not ones
that were edited. To assert an edit, grade the file's contents with `regex` over
`{source: file, path: …}`.

---

## 5. Testing a gate in the middle of the workflow

`/implement-feature` has 12 gates. Driving a case through all of them to reach gate 7 would be slow,
expensive and flaky — and most of the run would be testing gates you did not change.

`context.history_file` solves it: replay a known-good transcript up to turn N−1, and the case's
prompt becomes turn N.

```yaml
# case.yaml
schema_version: "1.1"
name: gate-7-mutmut-threshold
context:
  history_file: history/through-gate-6.jsonl
execution:
  prompt: looks good, continue
```

Record the transcript once from a real session, trim it to the turn before the gate you care about,
and commit it beside the case. Re-record it when the gates before it change shape — a stale history
file tests a workflow that no longer exists.

Two consequences to expect:

- **Δ is ~0 by construction.** The recorded transcript carries the expanded skill text, so the
  *without* arm still has the skill in context. Judge a history-seeded case on its *with* score;
  its Δ carries no signal.
- **Each run writes a transcript beside the history file.** Replay resumes the session, which
  saves itself as `history/<session-uuid>.jsonl`. `evals/.gitignore` excludes that pattern — never
  commit one.

---

## 6. Running the suite

**In the dev container** — the suite's home (§ 1):

```bash
# the every-change loop: no baseline arm, filtered to what you touched
claude plugin eval sdlc-lite-plugin --ablation none --tag gate-0 \
  --scaffold --no-publish --allow-tools Bash Write Edit

# the milestone gate — both arms, pinned models, a threshold
claude plugin eval sdlc-lite-plugin \
  --ablation with-without --model <pinned> --judge-model <pinned> \
  --threshold <t> --json results.json --no-publish \
  --scaffold --allow-tools Bash Write Edit
```

**On the Mac host** — fast iteration while you are still getting a read-only case's graders right:

```bash
claude plugin eval sdlc-lite-plugin --case 'routing-*' --runs 1 --scaffold
```

A green host run is not a suite run: re-run in the container before calling the change verified, and
remember that a Bash-granting case is refused there outright (§ 1).

Put the target **before** `--tag`, `--allow-tools` and `--json`. Pilot new cases with `--runs 1`;
raise it once the graders are right, because a single run of a non-deterministic agent is noise.

**Tags used by this suite:**

| Tag | Meaning |
|---|---|
| `gate-0` … `gate-11` | The gate the case exercises |
| `routing` | Whether the workflow starts (or correctly does not) |
| `entry-point` | The explicit-entry contract — slash spellings, no auto-invocation |
| `guard` | Guard-hook behavior |

**Outputs.** A summary table on stdout, and per run
`sdlc-lite-plugin/evals/results/<timestamp>/aggregate-result.json` plus `report.html`. `--json`
prints the same document and makes the run quiet — debug without it. Exit codes: **0** all cases at
or above the threshold (default **1.0**), **1** below threshold / load error / no cases / gated off,
**2** partial (cost ceiling, or auth rejected), **130** interrupted.

Note that the default threshold is 1.0 — everything must pass. Set `--threshold` deliberately for
CI rather than inheriting that.

---

## 7. The ablation delta, and how to misread it

`--ablation with-without` runs every case twice: once with the plugin, once with no plugin at all.
The delta answers "is this plugin earning its tokens?" — a different question from "did I break it".

Three traps:

- **`Skill` graders are excluded from the score in both arms.** A `tool_used` grader on `Skill` with
  no explicit `arm` cannot mean anything in a run with no plugin, so it is dropped from the baseline
  arm and unscored in both, appearing as an indicator (`withOnly: true`, `scored: false`). Set
  `arm: both` to opt one back in — which you want for a negative case (§ 3, rule 5).
- **A suite scores differently under `--ablation none`.** Nothing is excluded there, so the same
  `Skill` grader *is* scored. The two numbers are not comparable; don't chart them together.
- **`tool_used: Skill` passing while the delta is negative means suspect the judge, not the plugin.**
  The skill fired; the judge is scoring the outcome badly. Re-read the rubric before "fixing"
  anything.

Also: **pin `--model`** so a model rollout is not misread as a plugin regression, and **leave
`partial: true` runs out of any trend** you keep.

---

## 8. Troubleshooting

| Symptom | Cause → fix |
|---|---|
| `` `plugin eval` is currently in early access `` | Gated off — `export CLAUDE_CODE_WALNUT_SPIRE=1` in the shell, not in repo settings (§ 1) |
| `a Bash-granting evaluation cannot run here` | You are on the Mac host; Bash cases only run in the dev container (§ 1) |
| `No eval cases found` | No `<case>/prompt.md` under `sdlc-lite-plugin/evals/`, or `--case` / `--tag` filtered everything out |
| A grader over `trace` never matches | The trace is JSON per line — escape your quotes: match `\"`, not `"` |
| `file_exists` fails on a file you can see | It only counts files **created** during the run; grade contents with `regex` over `{source: file}` instead |
| The case "asked for" a tool but never used it | `Bash`/`Write`/`Edit`/`WebFetch`/`mcp__*` need the operator's `--allow-tools`, not just `allowed_tools` |
| Everything passes but nothing is being tested | The prompt names the skill or states the expected outcome — rewrite it as a user would type it (§ 3) |
