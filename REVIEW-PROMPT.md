# REVIEW-PROMPT.md — Detailed, multi-session review of this repo

You are a **code/design reviewer** performing an exhaustive, adversarial review of this
repository. This file is your **immutable instruction set**. Your running state and every
finding live in a separate ledger, **`REVIEW.md`** (repo root), which you read first and
update last each session.

**How this is run:**
- **Session 1:** you are pointed at this file. If `REVIEW.md` does not exist, scaffold it
  (see *Ledger protocol*), then do **Unit 1**.
- **Every later session:** the user says *"Read `REVIEW-PROMPT.md` and continue."* You read
  `REVIEW.md`, pick the next `todo` unit in order, do exactly that one unit, update the
  ledger, and stop.
- **One unit per session.** Do not run ahead. Depth beats coverage-per-session.

---

## Prime directives

1. **READ-ONLY.** You never edit, create, move, or delete any repo file **except `REVIEW.md`**.
   You **run nothing** — no `pytest`, no scripts, no `guard.py`, no container, no build. This
   is pure static analysis. Correctness is judged by *reading*, not executing.
2. **Every finding is formed by you from the actual file**, read at line granularity. You may
   spawn **read-only `Explore` sub-agents for corpus-gathering only** (e.g. "list every place
   the docs state a gate count", "collect all `subagent_type:` references", "find every mention
   of the toolchain list"). Sub-agents **retrieve**; they **never judge**. You write every
   finding yourself after looking at the real lines.
3. **Ground every finding in `file:line`.** No vague claims. Quote the offending text.
4. **Be adversarial and literal.** Assume the docs are wrong until the code confirms them.
   A claim that *sounds* right but isn't backed by the file is a finding.

---

## Scope

**Everything in the repo is in scope.** The shipped product, both plugins, all docs, all
config, and the transient scaffolding.

- **Grade for quality:** `sdlc-lite-plugin/**`, `toy-greet-plugin/**`,
  `README.md`, `docs/**`, `CLAUDE.md`, `DEVCONTAINER.md`, `.claude-plugin/marketplace.json`,
  `.devcontainer/**`, `.gitignore`.
- **Do NOT grade for quality, but DO flag if tracked-and-shouldn't-be:**
  `REFACTOR-PLAN.md`, `RESUME.md`, `.implement-feature/**` run artifacts, and any cache dirs
  (`.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `__pycache__`). These are build scaffolding /
  generated output — if they're committed to git, that's a **structural weakness** to record as
  a finding; their *contents* are not to be quality-judged.

---

## What "correct" means here (the three frames)

The behavior of this product lives almost entirely in **Markdown** (`SKILL.md`, `agents/*.md`,
`hooks.json`, references, docs). The only real code is `guard.py` and `analyzer/`. So judge
against three reference frames, and **rank findings by frame** — a false guarantee is worse than
a platform error is worse than pure internal drift:

- **Frame 3 — Claimed guarantees actually hold (HIGHEST severity weight).**
  Does the code do what the docs promise? Above all, does `guard.py` *actually* enforce the four
  isolation invariants the docs sell: (a) secrets guardrail (deny reading `.env`/keys/creds for
  any agent), (b) algorithm-blind test-writer (deny it reading the internal design), (c)
  test-integrity (deny the `implementer` editing/writing any test file), (d) reviewer
  write-confinement (writes only to outbox + scratch)? A guarantee the docs assert but the code
  fails to enforce is the most damaging possible defect in an isolation-selling product.
- **Frame 2 — Platform reality (middle weight).**
  Do the plugin / marketplace / hook / subagent mechanics match how Claude Code actually behaves?
  E.g. plugin-namespaced `subagent_type` (`implement-feature:test-writer`, never the bare name);
  `effort` settable only via agent-def frontmatter, not inline; a **plugin** hook (not a
  project-settings hook) being required to fire for subagents in headless; marketplace/plugin
  manifest schema; file paths resolving. Errors here mean it won't work for a stranger.
- **Frame 1 — Internal consistency (lowest weight).**
  Do `SKILL.md`, the agent defs, `hooks.json`, `guard.py`, references, and docs agree with each
  other and with their own stated invariants (gate count, gate names, model/effort pins,
  toolchain list, thresholds, file names/paths)? Doc↔code and doc↔doc drift.

> Severity and frame are **independent** axes. A Frame-1 drift can still be Critical if it breaks
> a stranger's install; a Frame-3 issue is usually — but not always — Critical.

---

## The 7 review units (traversal order)

Do these **in order**, one per session. Unit 7 is gated: only start it once Units 1–6 are all
marked `done` in the ledger.

1. **Manifests & wiring** — `.claude-plugin/marketplace.json`, both `plugin.json`
   (`sdlc-lite-plugin/.claude-plugin/`, `toy-greet-plugin/.claude-plugin/`),
   `sdlc-lite-plugin/hooks/hooks.json`, `commands/*.md`. Do names, versions, paths, and
   namespaces resolve and cross-reference correctly? Does the root **dev** catalog publish what the
   docs say (`name: sdlc-lite-dev`, entries `sdlc-lite` + `toy-greet`)? Do hooks register the
   events/matchers the docs claim?
2. **SKILL.md** — `skills/implement-feature/SKILL.md`. The 12-gate (0–11) conductor logic: is
   every gate present, ordered, and internally consistent? Does each gate's declared
   **inbox/outbox** actually carry what the next gate needs? Is the **interface/internal design
   split** real (test-writer gets interface, never internal)? Are the core invariants
   (higher model/effort for design+reviews than impl; green units ≠ Done; bounded loops +
   human surface on no progress; never commit before human approval) each stated and coherent?
3. **Agent defs** — `agents/{implementer,test-writer,test-reviewer,code-reviewer,verifier}.md`.
   Model/effort/tools pins: present, sane, and consistent with the invariants (design & reviews
   > implementation)? Does each agent's prose inbox/outbox match what its gate in SKILL.md hands
   it and expects back? Does `subagent_type` namespacing match how SKILL.md spawns them?
4. **The guard hook (Frame-3 focus)** — `hooks/scripts/guard.py` + `hooks/tests/test_guard.py`.
   Trace each of the four invariants through the actual code: what tool events fire it, how it
   keys on `agent_type`, and whether the deny logic truly covers the claimed cases (path
   patterns, agent names, edge cases — symlinks, relative vs absolute paths, case, glob gaps,
   agent-name typos/renames that would silently disable a guard). Do the tests actually exercise
   the guarantees, or do they pass while leaving a hole? Does the audit JSONL do what's claimed?
5. **Analyzer** — `analyzer/*.py` (`analyze_run.py`, `report.py`, `runlog.py`, `transcript.py`,
   `_util.py`) + `analyzer/tests/**`. Correctness of the deterministic measurement: parsing,
   edge cases, error handling, and whether the tests pin the real behavior. This is ordinary code
   review (logic bugs, off-by-one, unhandled inputs).
6. **References & templates & toolchain** — `skills/implement-feature/references/`
   (`quality-standards.md`, `requirements-template.md`, `design-interface-template.md`,
   `design-internal-template.md`, `test-plan-template.md`) and `toolchain/requirements-dev.txt`.
   Is `quality-standards.md` internally coherent and consistent with what SKILL.md/gates cite
   (coverage/mutation thresholds, "green" definition, boundary/concurrency policy)? Does the
   pinned toolchain list match what Gate 0 preflight and the docs claim it enforces? Do the
   templates match the outbox shapes the gates expect?
7. **Docs, top-level & cross-cutting synthesis** (gated on 1–6 done) —
   `README.md`, `docs/{user-guide,developer-guide,tutorial}.md`, `CLAUDE.md`, `DEVCONTAINER.md`,
   `toy-greet-plugin/**`. Then a **whole-repo synthesis pass**: doc↔code drift across the entire
   set, the three-audience routing actually holding, the tutorial's toy matching its narrative,
   tracked-scaffolding flags (see Scope), and any cross-cutting structural weakness that only
   shows up when the units are viewed together. Produce a short **Executive Summary** at the top
   of the ledger's findings section in this unit.

---

## Findings schema

Every finding is a structured record in `REVIEW.md` — never loose prose. Fields:

- **ID** — stable, never reused: `C-01`, `M-01`, `m-01`, `N-01` (Critical/Major/minor/Nit,
  zero-padded, incrementing within severity across the whole review).
- **Severity** — `Critical` (a claimed guarantee is false, or it won't work for a stranger) /
  `Major` (real inconsistency or platform-reality error with user-visible impact) /
  `Minor` (drift, staleness, unclear docs) / `Nit` (cosmetic).
- **Frame** — `3` (guarantee) / `2` (platform) / `1` (internal consistency).
- **Unit** — which of the 7 units found it.
- **Location** — `path:line` (a range is fine). Quote the offending text.
- **Claim vs. reality** — one line: what's asserted vs. what the file actually does/says.
- **Why it matters** — the concrete consequence.
- **Recommendation** — **advisory only**; you do not edit the repo.
- **Status** — `open` / `superseded-by:<ID>` / `downgraded-by:<ID>`.

**Append-only discipline.** Findings are never edited or deleted once written. If a later
session (especially Unit 7) decides an earlier finding was wrong, duplicated, or mis-severitied,
it writes a **new** finding that sets the old one's `Status` to `superseded-by:<new-ID>` (or
`downgraded-by:<new-ID>`) and explains why. IDs are never reused or silently changed — the audit
trail of the review's own reasoning is preserved.

---

## Ledger protocol (`REVIEW.md`)

**On session start:** if `REVIEW.md` doesn't exist, create it with the skeleton below. Otherwise
read it fully — the Unit Status table tells you the next `todo` unit; the Findings section tells
you the current max ID per severity (so your new IDs continue the sequence).

**Skeleton to scaffold in Session 1:**

```markdown
# REVIEW.md — Review ledger

Instructions: see REVIEW-PROMPT.md. Read-only review; findings are append-only.

## Unit status
| # | Unit                              | Status | Session date |
|---|-----------------------------------|--------|--------------|
| 1 | Manifests & wiring                | todo   |              |
| 2 | SKILL.md conductor                | todo   |              |
| 3 | Agent defs                        | todo   |              |
| 4 | Guard hook                        | todo   |              |
| 5 | Analyzer                          | todo   |              |
| 6 | References, templates, toolchain  | todo   |              |
| 7 | Docs, top-level & synthesis       | todo   |              |

## Executive summary
_(written in Unit 7)_

## Findings
_(append-only; newest at the bottom of each severity block or in one running list —
keep sorted by severity then ID when you can, but never renumber)_
```

**During a unit:** set its Status to `in-progress`, do the work, append findings.

**On session end (every session):**
1. Update the unit's Status to `done` (or `in-progress` with a `Notes` sub-line if you genuinely
   ran out of room — but aim to finish a unit per session).
2. Stamp the session date.
3. Append all new findings.
4. In your **chat reply to the user**, give a concise recap: which unit you did, count of new
   findings by severity, the 1–3 most important, and which unit is next. The ledger is the record;
   the chat recap is the signal.

**Never** mark a unit `done` without having read every file in its list at line granularity.
