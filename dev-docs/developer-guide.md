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

## 1–5. Architecture

Moved to [`architecture.md`](architecture.md): gates, handoff, model pins, guard hook, analyzer.

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
