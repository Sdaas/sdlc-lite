# Developer Guide — architecture, decisions, and how to work on the plugin

This guide is for someone improving `implement-feature`. It covers the architecture, the real code
(the guard hook and the analyzer), the decisions behind them (ADRs), the design principles, and the
testing method. To *run* the plugin, read the [README](../README.md). For the underlying concepts,
start with the [Tutorial](tutorial.md). For versioning, issue triage, and releases, see
[`RELEASING.md`](RELEASING.md).

---

## 0. Recommended reading order

Read §1 and §2 first. Read §6 (ADRs) before you propose a structural change. Read §8, §9 and §10
(this repo's own slash commands) when you are ready to make a change. The other sections are
reference.

---

## 1. The core idea: a declarative workflow, no orchestration code

The product has no hand-written driver that calls "phase 1, phase 2." It is declared in four parts:

- a **skill** (`skills/implement-feature/SKILL.md`) is the conductor's *score* — an ordered English
  script of gates, loops, and stop conditions;
- **agent-definition files** (`agents/*.md`) pin each isolated gate's model, effort, and tools;
- a **hook** (`hooks/hooks.json` → `hooks/scripts/guard.py`) enforces isolation on every tool call;
- an **analyzer** (`analyzer/`) measures, after the run, what actually happened.

The agent is the runtime: it reads the score and executes it. **The behavior lives in Markdown.** The
only real code is `guard.py` + `policy.py` (enforcement) and `analyzer/` + `agentdefs.py`
(measurement). Code is allowed only when it enforces or measures, never when it orchestrates (ADR-5).

### Repository layout of the product

```
sdlc-lite-plugin/
├── .claude-plugin/plugin.json          # identity metadata
├── commands/
│   └── analyze-run.md                  # standalone re-analysis command
│                                       # (NO implement-feature.md — it would shadow the
│                                       #  skill below; see ADR-14)
├── skills/implement-feature/
│   ├── SKILL.md                        # the conductor's score (all gates) AND the
│   │                                   # /implement-feature entry point itself
│   └── references/
│       ├── quality-standards.md        # single source of truth for "green" + thresholds
│       ├── requirements-template.md
│       ├── design-interface-template.md
│       ├── design-internal-template.md
│       └── test-plan-template.md
├── agents/                             # one file per isolated gate; pins model/effort/tools
│   ├── test-writer.md  test-reviewer.md  implementer.md  verifier.md  code-reviewer.md
├── hooks/
│   ├── hooks.json                      # registers the PreToolUse guard
│   ├── scripts/guard.py                # the enforcement code (calls policy.py)
│   └── tests/test_guard.py
├── policy.py                           # the allow/deny rules — SSOT for guard + analyzer
├── agentdefs.py                        # reads agents/*.md model/effort pins for the receipt
├── analyzer/                           # deterministic after-the-fact reporter
│   ├── analyze_run.py runlog.py auditor.py transcript.py receipt.py report.py _util.py
│   └── tests/
├── tests/                              # policy, agentdefs, entry-point structure
├── evals/                              # `claude plugin eval` suite (T1)
└── toolchain/requirements-dev.txt      # pinned dev tools
```

---

## 2. Architecture: conductor + isolated gates

The system is a **conductor [C]** plus **isolated subagents [I]**.

- **Conductor [C]** — the interactive session running the skill. It holds the through-line, talks to
  the human, and walks the gates in order. Human-facing gates (interview, design, review) run here.
- **Isolated subagents [I]** — bias-sensitive gates run as separate agents: fresh context, a pinned
  model/effort, and a curated file-only inbox. The conductor spawns them with the Agent tool and the
  **plugin-namespaced** `subagent_type` — `sdlc-lite:test-writer`, never the bare name.

**Why isolate?** Bias is two problems:

1. **Anchoring** — a reviewer who watched the code get written shares the author's blind spots. A
   **fresh context** per critic fixes this.
2. **Model monoculture** — one model's blind spot recurs at every gate. **Model diversity** fixes
   this: reviews run on a stronger model than implementation.

The human is the continuity thread that integrates the independent specialists.

### The two trees: product vs process

- **Product** — the source and tests that ship. They live in the repo's own layout (`<code_root>`,
  `<tests_root>`), detected and confirmed at Gate 0. Code is written in place; a **git branch**
  isolates one feature from the next.
- **Process artifacts** — handoff files and audit logs. They live in a per-run, **gitignored**
  directory, never mixed with shippable code:

```
.implement-feature/                       # gitignored artifact root
  .active-run                             # pointer + single-run lock (Gate 0 → Gate 10)
  <NN-slug-YYYYMMDDHHMM>/                 # one dir per run
    handoff/
      draft/                              # unapproved drafts; never read by a subagent
      01-requirements.md … 08-code-review-findings.md
      run-log.jsonl                       # conductor's per-gate orchestration log
    run-report.md                         # written by Gate 11
```

### The handoff contract

Every gate reads a **curated inbox** and writes a **defined outbox**, both as files. A gate never
sees a prior gate's raw transcript. Handoff files are numbered in reading order, so browsing
`handoff/` top to bottom replays the run. A loop overwrites its file, so numbers stay stable.

| Gate | Reads (inbox) | Writes (outbox) |
|---|---|---|
| WRITE-TESTS [I] | `01-requirements` + `02-design-interface` + `04-test-plan` (**never** `03-design-internal`) | tests + `05-test-intent` |
| TEST-REVIEW [I] | `01` + full design + tests + `05-test-intent` | `06-test-review-findings` |
| IMPLEMENT [I] | `01-requirements` + tests + full design | `<code_root>/…` |
| VERIFY [I] | `01-requirements` (ACs + boundary inventory) + `<code_root>/` | `07-verify-report` |
| CODE-REVIEW [I] | `01` + full design + whole diff | `08-code-review-findings` |

The **interface/internal design split** keeps the test-writer algorithm-blind: it gets
`02-design-interface.md` (the public contract) but never `03-design-internal.md` (the algorithm).
The critics do see the internal design. Blind the producer, inform the critic (ADR-3).

### The twelve gates

| # | Gate | Runs as | Model / effort | Approver |
|---|---|---|---|---|
| 0 | CLASSIFY + model plan + preflight | [C] | session | human |
| 1 | INTERVIEW | [C] | session (wants Opus) | human |
| 2 | DESIGN / SPEC | [C] | session (wants Opus) | human |
| 3 | WRITE-TESTS | [I] `test-writer` | `sonnet` / medium | machine (suite red) |
| 4 | TEST-REVIEW | [I] `test-reviewer` | `claude-opus-4-8` (pinned) / medium | machine (verdict) |
| 5 | IMPLEMENT | [I] `implementer` | `sonnet` / medium | machine (green) |
| 6 | VERIFY | [I] `verifier` | `sonnet` / medium | machine (observed pass) |
| 7 | CODE-REVIEW | [I] `code-reviewer` | `claude-opus-4-8` (pinned) / medium | machine (verdict) |
| 8 | REVIEW-GUIDE | [C] | session (Sonnet/Haiku ok) | — |
| 9 | HUMAN REVIEW | [C] | session | **human (ship)** |
| 10 | COMMIT | [C] | session (Sonnet/Haiku ok) | — |
| 11 | REPORT | [C] | session | — |

Human gates bookend the run (0–2, 9); machine-condition gates run the middle (3–7) unattended. The
loops — TEST-REVIEW ↔ WRITE-TESTS, and VERIFY/CODE-REVIEW ↔ IMPLEMENT — are **bounded**: after N
rounds with no progress they stop and surface to the human. CODE-REVIEW tags each finding
`→IMPLEMENT` (code defect) or `→TESTS` (weak test), because the two repairs go to different gates.

This section is the map. `SKILL.md` is the territory: it is the authoritative description of every
gate.

---

## 3. Model & effort pinning (agent-definition files)

Each isolated gate is a named agent type defined in `agents/<role>.md`. Its YAML frontmatter pins the
role's static identity; the spawn brief passes the per-run specifics (paths, inbox).

```yaml
---
name: code-reviewer
model: claude-opus-4-8       # dated pin — see ADR-2
effort: medium
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit  # read-only critic
---
```

Verified facts:

- **Model** can be set in frontmatter or inline at spawn. Highest wins: inline param → frontmatter
  `model:` → `CLAUDE_CODE_SUBAGENT_MODEL` env → session → account.
- **Effort** can be set **only** in frontmatter. If unset, the subagent inherits the parent's effort.
- **Tools** allow/deny lists are hard restrictions, enforced per tool call.
- A plugin **cannot pin the conductor's model**. The conductor runs on whatever the session was
  launched with, so Gate 0 warns if it is below design-grade.

The invariant: **design and every review use a higher model than implementation.** The two
reviewers pin the dated `claude-opus-4-8` for reproducibility (ADR-2). The producers (`test-writer`,
`implementer`, `verifier`) pin the floating `sonnet` alias. Effort is `medium` on every gate;
real-world config differentiates on model, not effort (#28, #35).

The conductor dispatches pinned gates **bare** (no inline `model`), so the frontmatter pin is
honored. [`agentdefs.py`](../sdlc-lite-plugin/agentdefs.py) reads the pins and hands them to the
analyzer's receipt, which checks the actual model and effort against them. Why bare dispatch, and
why nothing enforces the pin at dispatch time: ADR-12.

---

## 4. The guard hook — isolation is enforced, not requested

`hooks/hooks.json` registers a **PreToolUse** hook (`hooks/scripts/guard.py`) that fires for the
conductor **and every subagent**, on every
`Read`/`Bash`/`Grep`/`Glob`/`Edit`/`Write`/`NotebookEdit`/`Task`/`Agent`/`Skill` call. It keys on the
`agent_type` (namespaced, e.g. `sdlc-lite:test-writer`) and `agent_id` carried on stdin. The allow/deny
rules live in [`policy.py`](../sdlc-lite-plugin/policy.py); `guard.py` calls it. Seven jobs:

1. **Audit** — appends `{ts, agent_type, agent_id, tool, target}` per tool call: a per-agent record
   of what each agent touched. Timestamps are UTC, to line up with the transcript's `Z` stamps (the
   analyzer correlates the two by time window).
2. **Secrets guardrail** — denies reading `.env` / keys / credentials / `~/.ssh/` for **any** agent.
   Matching is by path component and split by tool (ADR-10), so a Bash command containing
   `os.environ` is not falsely denied.
3. **Algorithm-blind** — denies the **test-writer** reading `03-design-internal.md`, via Read *and*
   Bash.
4. **Draft-confinement** — denies **any subagent** reading under `handoff/draft/`.
5. **Test-integrity** — denies the **implementer** editing or writing any test file.
6. **Write-confinement** — the **test-reviewer**, **verifier** and **code-reviewer** may write only to
   their outbox + a scratch dir.
7. **Explicit-entry** — denies any `Skill` call to this plugin's own skills (ADR-14).

A `deny` decision + exit code 2 blocks the call. Each rule is defense-in-depth: the agent's own role
instructions say the same thing, and the hook is the backstop.

**How per-run config reaches the hook.** A hook is a separate process and does not inherit the
conductor's environment. The conductor writes a fixed-path pointer, `.implement-feature/.active-run`,
naming the current run's artifact dir; the hook reads it to find the run-log. The same file is the
single-run lock. Before the pointer exists (Gate 0 preflight) or after it is removed (Gate 11), the
hook writes to `if-runlog.jsonl` at the repo root, which Gate 0 also gitignores.

**Why a *plugin* hook, not project settings.** A PreToolUse hook in project `.claude/settings.json`
did not fire in headless (`claude -p`) runs. The plugin-shipped hook fires for the conductor and every
subagent.

### Bash enforcement is best-effort — and the transcript auditor closes it (#30)

The guard inspects strings; it is not an OS sandbox. `Read`, `Write`, `Glob` and `Grep` name one
target, so the rules are precise there. For `Bash` they are best-effort: a shell string does not tell
you every file a `python -c …`, an `xargs` pipeline, or a `cd handoff && cat *` will touch. The guard
does resolve `>`/`>>`/`tee` redirects and the `sed -i`/`cp`/`mv` write forms, and it bans an
algorithm-blind agent's wildcard read over `handoff/`. An indirect read can still slip past it.

The analyzer's transcript auditor closes that gap by checking the *effect* instead of the command.
Both legs import the same `policy.py`, so they cannot disagree on what is forbidden. Mechanism and
rationale: ADR-11 and §5.

---

## 5. The analyzer — measurement, never orchestration

`analyzer/` is a deterministic Python reporter for a finished run. It reads the evidence a run leaves
behind and prints a Markdown report. It **never** calls a model, makes a decision, or drives a gate
(ADR-5).

**Why it exists.** `/implement-feature` makes two promises: **(a)** every gate is *isolated* — a
subagent reads only the files curated for its role — and **(b)** every gate runs at its *pinned
model/effort*. The guard prevents isolation violations in real time, best-effort for Bash. The
analyzer is the detective half: it reads the session transcript after the run and turns both promises
into per-run, checkable facts. The transcript's resolved `message.model` and per-turn `effort` field
are ground truth for the conductor and every subagent. Which field proves which claim is recorded in
[`findings/audit-observability-findings.md`](findings/audit-observability-findings.md).

**What the receipt is not.** It is observability plus best-effort prevention, **not a hard cost cap**.
Neither model nor effort can be enforced at dispatch (ADR-12), and Bash prevention is best-effort
(ADR-11). What the receipt gives is a per-run record of what the barriers and pins actually did, and
an **untrusted** mark on any violation.

The modules:

- **`runlog.py`** — **load-bearing**. Parses `handoff/run-log.jsonl` (or the `if-runlog.jsonl`
  fallback) into per-agent activity and the *intent-level* isolation verdicts: forbidden attempts the
  guard logged and blocked. Imports `policy.py`. Knows nothing of the transcript, so a transcript
  format change cannot break it.
- **`auditor.py`** — the **authoritative isolation leg** (#30). Fingerprints each content-protected
  artifact (e.g. `03-design-internal.md`) and scans each subagent transcript's *tool output* for it.
  A hit voids trust: the report prints `THIS RUN IS UNTRUSTED` and the receipt shows `❌ LEAK`.
- **`transcript.py`** — **best-effort**. Parses the session transcript for per-model tokens (main
  thread + each subagent under `<uuid>/subagents/*.jsonl`, attributed via the sibling `.meta.json`).
  The format is internal and unstable, so this reader sits behind one `try/except` boundary in
  `analyze_run.py` and fails two distinct ways: **absent** (a soft "skipped" note) or **drifted**
  (a loud "format changed, update the parser" alarm). With no transcript, the auditor reports
  **UNKNOWN**, never PASS.
- **`receipt.py`** — the **headline**: one row per agent attesting both promises. It takes the
  *requested* model/effort from the agent-def pins ([`agentdefs.py`](../sdlc-lite-plugin/agentdefs.py))
  and the *actual* from the transcript. A model mismatch is **FAIL** (trust-voiding); an effort
  deviation is **WARN** (a cost knob, not trust). An alias pin (`sonnet`) accepts any same-family id;
  a dated pin (`claude-opus-4-8`) demands an exact id.
- **`report.py`** renders Markdown; **`_util.py`** parses UTC timestamps tolerantly.

The run-log and transcript readers share no code. They are joined only by a value: the run-log's
`[min ts, max ts]` window, padded ±5 min, selects the overlapping transcript file.

**When it runs.** A fast intent-level pass (`--no-transcript`) runs just before Gate 9, so the human
sees any breach before shipping. The full pass, including the auditor, runs at Gate 11. Any past run
can be re-analyzed with `/sdlc-lite:analyze-run`.

The verdict list, CLI options, and failure handling are in
[`analyzer/README.md`](../sdlc-lite-plugin/analyzer/README.md). On-disk transcript record shapes are in
[`analyzer/TRANSCRIPT-FORMAT.md`](../sdlc-lite-plugin/analyzer/TRANSCRIPT-FORMAT.md).

---

## 6. Architecture decision records (ADRs)

Moved to [`adr/`](adr/README.md): one file per ADR, with a one-line index.

---

## 7. Design principles (distilled)

The load-bearing principles for anyone changing the plugin.

**Skills & workflow**
- **Trigger-oriented descriptions.** A skill's `description` decides when it activates. Write it about
  situations and phrasings, not just what the skill is.
- **One name, one surface; explicit entry (ADR-14).** A command never shares a skill's name, and this
  plugin's skills run only when a human types the slash command.
- **Driverless workflow.** The skill body is an ordered English script; numbered gates, machine
  conditions and "repeat until" loops replace orchestration code.
- **Gate = approval checkpoint.** The approver is a human (STOP-until-APPROVED, worded imperatively) or
  a machine-checkable condition ("until all tests pass"). Choose per phase.
- **Bound every automated loop** and surface to the human on no progress.

**Subagents & handoff**
- **Context-as-files handoff.** Each gate reads a defined inbox and writes a defined outbox as files.
  Files are durable, and they let you choose what an agent sees.
- **Asymmetric inboxes** — blind the producer (test-writer), inform the critic (test-reviewer).
- **Standards live in one file, not in each brief.** Briefs load `quality-standards.md`; to raise the
  bar, edit that file. Per-feature numbers (coverage/mutation) live in the test plan; universal
  commands and the definition of "green" live in `quality-standards.md`.
- **Anchored defaults beat free choice.** Ship a documented anchor (mutation kill-rate 80%) and require
  a justification to deviate, surfaced at approval. An agent given a metric with no anchor drifts.

**Quality gating**
- **Split checks by speed.** Fast checks (`ruff` + `mypy` + `pytest`) define the implementer's
  inner-loop "green"; slow checks (`pytest-cov` + `mutmut`) gate CODE-REVIEW.
- **Situational checks are boundary-driven.** Concurrency testing is required only when the boundary
  inventory shows the feature is concurrent/async; otherwise it is skipped with a stated reason.
- **VERIFY ≠ green tests.** Drive the real feature on each AC and exercise every boundary un-mocked; a
  mocked test only proves the mock. Unit-green is the inner loop (IMPLEMENT); observed behavior is the
  outer loop (VERIFY, a fresh read-only agent).
- **Mutation grades tests after the fact.** A surviving mutant is an injected bug no test caught, so
  mutation at CODE-REVIEW scores the test-writer and test-reviewer.
- **A critic may probe, never implement.** A reviewer may write tiny throwaway probes but must not
  build a reference implementation. Empirical mutation belongs at CODE-REVIEW, against the real code.
- **Don't let the producer grade its own homework.** When an agent's acceptance criteria live in
  files it could edit (the implementer and the tests), deny it write access to them by role.

**Enforcement & observability**
- **Defense-in-depth** — role instruction *and* hook.
- **Ship reliability-critical config with the plugin**, not project settings (headless-fire).
- **Verify runtime behavior; don't trust docs or config.** Model, tool blocks, hook firing and agent
  naming were all confirmed empirically. The docs were wrong on plugin-agent naming (it is namespaced,
  `plugin:agent`) and unsure on headless hooks.
- **Attribute every tool call** via `agent_type`/`agent_id`, for per-agent rules and a trustworthy
  audit.

---

## 8. Testing & dry-run methodology

**The plugin is never installed into the developer's global `~/.claude`.** It runs inside a **dev
container** with its own `~/.claude` and the pinned Python toolchain. The container limits the blast
radius (the product writes and commits code) and is where Gate 0's preflight passes. Topic owners —
this section links to them rather than restating them:

- **[`DEVCONTAINER.md`](DEVCONTAINER.md)** — container lifecycle, fresh setup, auth (`.env`), the two
  Claude profiles, and how the plugin loads in the container.
- **[`verification-ladder.md`](verification-ladder.md)** — the test tiers (T1 evals, T2 pytest, T3
  dry run) and the `release-verify.sh` clean-room gate.
- **[`RELEASING.md`](RELEASING.md)** — channels and release mechanics.

Two harnesses:

- **Unit tests (T2)** — `guard.py`, `policy.py`, `agentdefs.py` and `analyzer/` have unit tests
  (synthetic stdin, run-logs and transcripts, including both degradation modes):
  `python3 -m pytest sdlc-lite-plugin -q`, on the host or in the container.
- **End-to-end dry runs (T3)** — a human drives a real `/implement-feature` run in a container
  terminal (it needs a TTY), usually against a standard fixture (below), then runs the analyzer over
  the logs and fixes the fallout.

**A dry run is a bug-finding machine.** The first full run (`parse_duration`) validated the core
design and surfaced ~13 concrete improvements. Later runs (`slugify`, and the async `CachedFetcher`
with fault injection) confirmed the fixes and the invariants: reviews ran on Opus and producers on
Sonnet (transcript-proven), the test-writer stayed algorithm-blind, the implementer never touched a
test file, and the pipeline committed.

### Fault injection (the un-mocked resiliency check)

For a feature with a network boundary, VERIFY and the resiliency review must be exercised against
real faults, not just asserted. The async `CachedFetcher` run used **`httpx.MockTransport`** through
the feature's transport-injection seam — deterministic, no network, no extra process — to inject:

- transport-level faults (a handler that *raises* `ReadTimeout`/`ConnectTimeout` before any response
  exists — a different code path from `raise_for_status()`);
- response-level faults (a handler returning a 5xx `Response`);
- both under `asyncio.gather(...)`, to exercise request coalescing under fault.

The feature held up: timeouts and 5xx raise the right exception and are **not cached**; a coalesced
wave issues one request and every caller sees the same fault; a fresh call afterwards recovers. No bug
— but the pass exposed a methodology trap:

> **Transport-level faults ≠ response-level faults.** The run's test plan and resiliency review
> listed only *response-level* faults (non-2xx status, malformed body). They confused "no
> *configurable* timeout" (a correct scope decision) with "no need to *test* timeouts" (a coverage
> gap). Timeouts and connection failures are a real fault path, separate from status errors. So the
> plugin now requires: **for any feature whose boundary inventory includes a network boundary, at
> least one transport-level fault test** — a timeout or connection failure raised before a response —
> asserting it *propagates* and is *not cached*. (Applied to `quality-standards.md`,
> `test-plan-template.md`, `test-writer.md`, and `code-reviewer.md`.)

### Standard fixtures — `test-fixtures/python-starter/`

**Why a committed template, not a generator script.** An empty-folder dry run lets the conductor
invent the layout, which says nothing about fitting into a real codebase. A fixture is therefore a
small, **non-empty** package with its own module and tests, so the run shows whether the implementer
places new code correctly beside existing code. Generating that content per run (via `uv init` or
similar) would add a confound — "what did the generator do today" — so each fixture is **committed
and byte-identical** across runs. A script only copies it.

**Layout, per fixture** (`test-fixtures/python-starter/<slug>/`):
- `pyproject.toml` — src-layout, package name derived from the slug (`roman-numeral` →
  `src/roman_numeral/`).
- `src/<pkg>/greet.py` + `tests/test_greet.py` — the **shared pre-existing module**, identical in
  every fixture: `greet(name) -> f"Hello, {name}!"`, raising `ValueError` on empty/whitespace input.
  It is deliberately boring, so the only thing that varies between fixtures is the feature under test.
- `BRIEF.md` — the literal one-line `/implement-feature` prompt, stored verbatim so the invocation is
  identical run to run. If a receipt differs, that should mean the workflow changed, not the wording.

**Fixtures today:** `roman-numeral` (int ↔ Roman numeral, both directions, rejects malformed input).
`parse-duration` and `async-cached-json-fetcher`, used in the earliest dry runs, are planned next.

**Running one.** On the Mac:
```bash
test-fixtures/setup-fixture.sh roman-numeral
```
Inside the container, the script refuses if `/workspaces/<slug>-run` already exists (remove a stale
one by hand — it is never silently wiped). It then copies the template to `/workspaces/<slug>-run/`,
`git init`s it on `main` and commits the baseline (so the never-commit-on-default rule forces the run
onto a feature branch), and runs `pip install -e .` so Gate 0's import check passes. Then:
```bash
devcontainer exec --workspace-folder . bash -c "cd /workspaces/roman-numeral-run && claude --model opus"
```
and in that session, type `/implement-feature` followed by `BRIEF.md`'s content.

The script only creates the scratch repo. **#21** (rebuild the container fresh per run, `1.0.0`) will
wrap it; **#34** (an agent driving the gates unattended, judged by the receipt, backlog) will use
`BRIEF.md` as its prompt.

**Reading handoff files mid-run, from the Mac.** A fixture run's `.implement-feature/` lives in
`/workspaces/<slug>-run/`, outside the bind mount, so it is not on the Mac's filesystem. Three ways
to read a gate's file at a STOP:
1. **`devcontainer exec` + `cat`**: `devcontainer exec --workspace-folder . cat
   /workspaces/<slug>-run/.implement-feature/<run>/handoff/draft/<file>.md`.
2. **VS Code attached to the container** — Command Palette → **"Dev Containers: Attach to Running
   Container"** → open `/workspaces/<slug>-run`. ("Reopen in Container" shows only the bind-mounted
   `sdlc-lite` folder.)
3. **`docker cp`**: `docker cp
   sdlc-lite-test:/workspaces/<slug>-run/.implement-feature/<run>/handoff/draft/<file>.md ./review.md`.

---

## 9. When you edit the product

- **Behavior lives in Markdown** — `SKILL.md`, `agents/*.md`, `references/*`, `hooks.json`. Editing the
  workflow means editing these, not writing code.
- **Change a gate's model/effort/tools** → edit the matching `agents/*.md` frontmatter (effort is
  frontmatter-only).
- **Change what an agent may read/write** → update *both* the agent's prose inbox **and** `policy.py`
  (defense-in-depth). `guard.py` and the analyzer both import it, so there is nothing to mirror.
- **Change "green" or a threshold policy** → edit `references/quality-standards.md` (the single source
  of truth), not individual briefs.
- **Verify before you rely on runtime behavior** — do a container dry run; the transcript and the
  guard's audit log are your ground truth.

---

## 10. Repo-local skills (for working on this repo)

This repo carries its own slash commands in `.claude/skills/`. They are **not** part of the shipped
plugin — they load only when you run Claude Code from this repo's root, and only a human can start
them (type the command; the model never invokes them). All share one process,
[`.claude/sdlc/gates.md`](../.claude/sdlc/gates.md); why this repo needs its own rather than using
`sdlc-lite` on itself: [`verification-ladder.md`](verification-ladder.md) §6.

| Command | What it does | Status |
|---|---|---|
| `/issue` | Files one GitHub issue per [`issue-template.md`](issue-template.md), after you approve the draft | available |
| `/feature` | Implements an issue through gates 0–8 with 4 approval STOPs | planned — #52 |
| `/fix` | `/feature` plus REPRODUCE and DEPOSIT gates for bugs | planned — #53 |
| `/regression` | Runs the whole eval suite, 3 runs per case | planned — #64 |
