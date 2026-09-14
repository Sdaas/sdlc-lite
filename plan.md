# Execution Plan — Trust Claim (v1) → Capability Expansion (v2)

_Last updated: 2026-09-14. Derived from a grilling session over issues #28, #30, #22, #31, #32, #18, #21._

---

## How to use this plan (read first)

This is the **single source of truth** for the roadmap. Work happens **one issue per fresh session**:
open a new session, point it at this file, and say "execute issue #NN per plan.md." The plan tells
you *what order* and *why*; the **GitHub issue is the detailed spec** (each relevant issue now carries
a 2026-09-14 decision comment that overrides any stale prose in the issue body).

**Per-session workflow for any issue:**
1. Read this plan's section for the issue **and** the full GitHub issue + its 2026-09-14 comment
   (`gh issue view NN --comments`).
2. **If the goal, methodology, or instructions are unclear or ambiguous — stop and ask.** Do not
   proceed on a guess. State your understanding of Goal / Constraints / Instructions and get
   confirmation before writing anything.
3. Plan → get approval → phased execution. **Commit per logical unit; keep git history.**
4. The behavior lives in **Markdown** (`SKILL.md`, `agents/*.md`, `references/*`, `hooks.json`) — the
   only real code is `guard.py` and `analyzer/`. Changing a gate's model/effort/tools = edit the
   matching `agents/*.md` frontmatter. Changing what an agent may read/write = update **both** the
   agent's prose inbox **and** `guard.py` (defense-in-depth).
5. **"Done" ≠ "the change exists."** Done = a **green end-to-end dry run in the dev container**
   (see `DEVCONTAINER.md`). Host unit tests: `python3 -m pytest implement-feature-plugin -q`.
6. **Never commit before human approval.**
7. When an issue is complete, update this plan's **Status ledger** (below) and close the issue.

**Order is load-bearing** for the v1 cluster (schema before the legs that fill it). Do not reorder
without revisiting the dependency reasoning in "The through-line."

**Branching strategy (solo dev — branch per release stream, commit per issue):**
- The **entire v1 audit cluster** (#28 → #31 → #30 → #22 → #31-close → #35) lands on **one branch,
  `v1-trust-claim`**. Each issue lands as its own commit(s) — keep "commit per logical unit" and
  granular history — but the branch merges to `main` **once**, as the coherent v1 release. Every v1
  session commits onto this same branch; do **not** cut a new branch per issue.
- **v2 issues are independent** — each gets its own branch (e.g. `feat-32-plan-feature`,
  `feat-34-regression-harness`), since they share no code with the cluster.
- Rationale: matches "ship v1 as one coherent release"; avoids throwaway per-issue PRs for tightly
  coupled changes; lets the whole cluster be reviewed as one diff before touching `main`. Accepted
  cost: `main` goes stale while v1 accumulates (fine for a single developer).

## Status ledger

| Issue | Stream | State | Notes |
|---|---|---|---|
| #28 | v1 · step 1 | **DONE** | effort reconcile + dev-spread test-design; dev-spread = code-review `high` / test-review `low` / rest `medium` |
| #31 (skeleton) | v1 · step 2 | **DONE** | receipt schema (`analyzer/receipt.py`) rendered always, all-`UNKNOWN` verdicts; R3 effort-extraction + R4 `guard_decision` plumbing landed; effort policy widened to WARN-both-directions; Sources block + `SAMPLE-RECEIPT.md`. Issue **stays open** for the close phase (step 5) |
| #30a (enforcer) | v1 · step 3a | **DONE** | policy SSOT (`policy.py`) + guard rewired onto it (R1 enforcer side, R2) + Bash write-forms (sed -i/cp/mv) + full-length run-log (R3 intent half) + R6 wildcard-ban + #29 (verifier/code-reviewer write-confinement). Commits: R1 `9c96c8e`, R2 `b2a7184`, R6 `518c5aa` |
| #30b (auditor) | v1 · step 3b | **NEXT** | **Resume #30 here.** See the split note in the #30 section. Two parts: (B) `analyzer/runlog.py` dedup — import `policy`, delete its duplicate predicates (finishes R1's "KEEP IN SYNC" fix); then (R3/R4) the transcript-based auditor + Gate-11 FAIL + receipt `Files seen` column + DG/ADR + R5 auditor-layer tests |
| #22 | v1 · step 4 | pending | model-enforce (Witt) + effort-audit; **un-deferred** |
| #31 (close) | v1 · step 5 | pending | framing + docs; v1 acceptance dry runs |
| #35 | v1 · release | pending | flip all effort pins → `medium`; **blocked by #31** (must observe the dev-spread first) |
| #32 | v2 | pending | `/plan-feature`; first task = falsification run |
| #34 | v2 (indep.) | pending | agent-driven regression harness; supersedes #18 D5c, needs #21 |
| #18 | support | partial | D1–D4 stand; **D5c superseded by #34** |
| #21 | support | pending | clean-container-per-run; #34 depends on it |

## The through-line

The repo's **headline value proposition is the trust claim**, not the code generation:
_a provably-isolated, cost-bounded, test-first SDLC that hands you a per-run receipt proving
the information barriers and reasoning budget actually held._ Lots of tools generate code from a
prompt; almost none prove isolation + bounded model/effort per run. **If the trust claim doesn't
hold, nothing else — including new capability — matters.**

Consequence for sequencing:
- **v1 = harden the trust claim** (the audit cluster: #28 → #31 → #30 → #22 → #31).
- **v2 = expand capability** (`/plan-feature` #32) on a stable, proven base.

The three "themes" collapse into **one dependency tree + one independent capability**:
- `#31` is the **umbrella** — owns the audit phase, the framing, and the per-subagent
  receipt **schema**. It delegates two capabilities to sub-issues:
  - `#30` — isolation (which file *content* each agent actually saw; intent vs effect).
  - `#22` — model/effort integrity (requested vs actual).
- `#28` is the **static half** of effort integrity (what the pinned effort *is*) — a prerequisite
  of the audit's effort leg.
- `#32` (`/plan-feature`) is **orthogonal** — shares no code with the cluster.

---

## v1 — the trust-claim cluster

Ship as **one coherent release**. Order is load-bearing (schema before the legs that fill it).

### 1. #28 — Reconcile effort (also: a test-design for the audit)
- **Decision:** effort pins differ *during development* precisely so the audit can be *proven* to
  observe them:
  - `code-reviewer` (Gate 7) → `effort: high`
  - `test-reviewer` (Gate 4) → `effort: low`
  - implementer + verifier (+ test-writer) → `effort: medium`
- Prove the transcript reflects exactly that spread (the audit distinguishes high/low/medium).
- **Then flip everything → `medium` just before release** (real-world config differentiates on
  **model**, not effort). ⟶ tracked as **#35** (v1 · release, blocked by #31 — do not flip until the
  audit has observed the dev-spread end-to-end).
- Fix the 4 false `SKILL.md` "/high" prose sites + the 2 blank reviewer-effort cells in the
  model-plan table so every site agrees with the agent-def frontmatter.

### 2. #31 (skeleton) — the receipt schema, everything `UNKNOWN`
- Land the per-subagent audit-record **schema first** so #30 and #22 each just "fill their column"
  instead of inventing partial shapes reconciled at the end.
- Every intermediate commit yields an **honest, runnable report** — `UNKNOWN` is a valid verdict.
- Widen the effort deviation policy: **WARN on any deviation from the pin, both directions**
  (an *upgrade* is flagged too, not only a downgrade).

### 3. #30 — isolation column: policy SSOT + transcript auditor
- One declarative per-agent policy (`agent_type → {readable, writable}`, deny-by-default) imported
  by **both** the in-hook enforcer (prevention, best-effort for Bash) and the analyzer
  (detection, authoritative, transcript-based). Settles the "KEEP IN SYNC" drift.
- Fix the 300-char run-log truncation (data-loss bug).
- A detected violation flips Gate 11's isolation verdict to **FAIL** and marks the run
  **untrusted**. Subsumes #27 and #29.

**⟶ SPLIT ACROSS SESSIONS (2026-09-14).** #30 was split at ~15% context into an enforcer half
(shipped) and an auditor half (next). No issue-body change; this note is the SSOT for the split.

- **#30a — enforcer (DONE).** Shipped on `v1-trust-claim`:
  - `implement-feature-plugin/policy.py` — the SSOT: shared predicates (`looks_secret`,
    `is_test_path`, design-internal/draft tests, write-confinement, Bash command parsing) + a
    per-agent rule table (`POLICY`) + the one authority `decide(agent_type, access, path, handoff_dir)`.
  - `guard.py` rewired onto it (deleted its duplicate predicates); Bash write-forms extended to
    `sed -i`/`cp`/`mv`; run-log now logs full-length command strings (R3's *intent* half); R6
    wildcard-ban (algorithm-blind agent can't glob-read over `handoff/`); #29 generalization
    (verifier + code-reviewer write-confined like the test-reviewer). All host tests green (119).
  - **Design note (deny-by-default):** a literal restrictive *read* allow-list is impossible for
    the producer roles (implementer/verifier read the whole repo + stdlib), so `readable` = "everything
    minus a deny set"; deny-by-default is honored structurally in `decide()` (reads can be tightened
    per role later) but today only the deny set bites. Documented in `policy.py`'s docstring.

- **#30b — auditor (NEXT — resume here).** Two parts, in order:
  1. **(B) `analyzer/runlog.py` dedup** — finish R1's detective side: `import policy`, delete
     `runlog.py`'s duplicated `looks_secret`/`is_test_path`/`reviewer_write_denied`/heredoc/bash-parse
     copies, and route its isolation checks through `policy.decide()`. ⚠️ `runlog.py`'s
     `reviewer_write_denied` currently uses a loose substring (`"/handoff/"`, `"scratchpad"`); the
     policy version is **anchored** (real handoff dir / temp-root prefix). Unifying may shift a
     detective verdict — read `analyzer/tests/test_runlog.py` first and refactor carefully.
  2. **(R3/R4) transcript-based auditor** — the authoritative *effect* leg. **Agreed design
     (2026-09-14):** the auditor uses **two signals**, roles fixed —
     - **content-fingerprint = authoritative / trust-voiding.** Read the protected artifacts (e.g.
       `handoff/03-design-internal.md`) from the run's workdir, fingerprint them, and scan each
       subagent's transcript `tool_result` output for that content. This is the ONLY signal that
       catches the `cat handoff/*.md` glob leak (a glob exposes no resolved path in `tool_use`, only
       the command — same blind spot as the run-log) and is **method-agnostic** (python/xargs/indirect
       reads all land as output). A hit **voids trust**.
     - **path extraction + best-effort "unglob" = precise, corroborating.** Explicit `file_path` from
       Read/Edit/Write `tool_use` is exact; the user's unglob idea (resolve a literal glob against the
       filesystem) is kept as a "name which file leaked / catch writes" helper — supporting detail,
       NOT the trust authority (it shares the command-string blind spot and drifts at audit time).
     - Then wire R4: a detected violation flips **Gate 11**'s isolation verdict to **FAIL** / run
       **untrusted**, and fills the receipt's `Files seen` column (currently UNKNOWN in `receipt.py`).
     - Docs: `developer-guide.md` §4 "Known limitation — Bash enforcement is best-effort" describes the
       *current* (enforcer-only) state; update it to the shipped enforcer + auditor whole, and write the
       ADR (intent-vs-effect split, policy-as-seam, best-effort-Bash boundary, content-fingerprint authority).
     - R5 tests: the `cat handoff/*.md` read-leak and `sed -i … tests/…` at the **auditor** layer
       (the enforcer layer is already covered by the #30a tests).

### 4. #22 — model/effort column + enforcement (un-deferred)
- **Same problem statement as the Thomas-Witt article** (subagents silently launched on the wrong
  model → cost/usage surprises). Adopt his technique.
- **Model = enforced:** a `PreToolUse` hook on the `Task`/`Agent` dispatch reads the agent-def
  `model:` pin; if the dispatch carries no explicit model, **deny (exit 2) → forced re-dispatch
  with the model named explicitly**, promoting the pin from rank 2 (frontmatter, silently
  droppable) → rank 1 (per-invocation). Wrong-model launch becomes impossible; a
  transcript/pin mismatch is a **FAIL** (on the tool). Fail-open on unparseable payloads.
  Integrate into `guard.py` (add a Task/Agent branch), not a separate script.
- **Effort = audit-only (documented asymmetry):** `effort` has **no rank-1 slot**
  (`effort` is frontmatter-only per this repo's platform rule). So effort can only be **proven**,
  never forced. The receipt says two structurally different things, and that honesty is itself a
  credibility signal.
  - ⚠️ **VERIFY FIRST before banking on this.** The "effort is frontmatter-only / no inline slot"
    premise is written in *this repo's* `CLAUDE.md` and may be **stale relative to the current
    Claude Code platform**. It is cheap to check and expensive to be wrong about. **Before designing
    #22's effort leg as audit-only, confirm on the current platform whether the Agent/Task dispatch
    exposes any effort lever** (dispatch a sub-agent to check the live tool surface). If an effort
    lever now exists, effort becomes *enforceable* too and the asymmetry disappears — re-open this
    decision. If it holds, ship the honest two-tier receipt.
- Conductor **stops writing guessed `model` fields** into the run-log for `[I]` gates; the
  transcript-derived model is the single source of truth. No guesses anywhere human-facing.

### 5. #31 (close) — framing + docs
- DG + README state the audit's purpose: the **receipt** proving guarantees (a) isolation and
  (b) bounded model/effort — **observability with best-effort prevention, not enforcement of cost.**

### v1 acceptance — driven **manually**, once, for the release
- **Clean run** → all-PASS receipt (isolation held; model == pin; effort spread == configured;
  committed).
- **Adversarial run** → deliberately inject a violation and prove the receipt flips to
  **FAIL / "untrusted — investigate"**:
  - test-writer read-leak of the internal design (`cat handoff/*.md`),
  - implementer Bash test-write (`sed -i … tests/…`),
  - a wrong-model launch.
- A trust product shown only passing hasn't demonstrated the thing that makes it trustworthy. The
  **caught violation is the real proof.**
- The human drives #28/#22/#30/#31 by hand — automation is not a v1 blocker.

---

## v2 — capability expansion

### #32 — `/plan-feature`
- **First task is a falsification run, not the skill.** The "large features break
  `/implement-feature`" failure is *confident-but-unobserved*. Drive a deliberately-large,
  deliberately-decomposable feature through the **existing** `/implement-feature` and capture the
  real failure signature (attention-splitting? bad decomposition? context exhaustion?). Pin the
  `/plan-feature` design to *that* signature, not an imagined one.
- Then build per the issue: conductor skill (Opus 4.8 high), FR+NFR elicitation, system-design doc +
  requirement→test matrix, structured-contract child issues + terminal `Z` issue, the GitHub
  sub-issue DAG with dependency edges, the decomposition red-team reviewer (isolated), depth-cap
  refuse at depth > 1.

### New issue — agent-driven automated regression harness
- **Option (b):** supersedes #18's D5c (an **agent-driver** replaces pre-scripted stdin — state this
  in both issues so the pre-scripted approach isn't built by mistake); depends on **#21**
  (clean-container-per-run) as its deterministic setup layer.
- **Driver advances, receipt adjudicates.** The driver (this Claude driving the inner Claude in the
  dev container) may answer gate prompts dynamically — that's its power over brittle scripted stdin
  — but the **pass/fail oracle is 100% the deterministic receipt**: analyzer output + the
  implementation report (all tests pass, coverage, mutation-kill), never the driver's judgment. This
  is what keeps an LLM-driven harness a valid regression test.
- **Independent stream.** Firmly v2; *may* be pulled into v1 just before release, but does **not**
  gate v1. Building it soon after v1 (before #32 churn) makes re-proving the v1 receipt cheap.

---

## Standardized test suite (from #18-D4 — still uncommitted)

Deliverable `test-fixtures/python-starter/` + feature briefs is **unbuilt**; the decisions exist.

| Case | Fixture | Exercises | When it runs |
|---|---|---|---|
| pure function | `parse_duration` ("1h30m" → seconds) | fast smoke | **standard pair** |
| async / I/O | `async-cached-json-fetcher` (REST call + cache) | concurrency mandate + un-mocked VERIFY boundary | **standard pair** |
| stateful class | invariants / mutation | mutation-invariant testing | pipeline-change runs only |
| _(future)_ multi-class interaction | TBD | multiple components interacting | later — **doubles as the #32 falsification fixture** |

**Known blind spot:** the standard pair does not exercise mutation-invariant testing; a regression
in that region only surfaces on pipeline-change runs. Accepted trade-off for run cost (each full
run = 6 subagents incl. Opus reviewers).

---

## Issue write-backs (done 2026-09-14)

1. **#28** — ✅ decision comment posted (dev-spread → release-medium + acceptance).
2. **#22** — ✅ comment: un-deferred, after #30; model-enforce / effort-audit asymmetry + WARN-both.
3. **#31** — ✅ comment: schema-first; effort deviation both directions; adversarial acceptance.
4. **#32** — ✅ comment: v2; first task = falsification run.
5. **#34** — ✅ **created**: "Agent-driven automated regression harness for /implement-feature
   (supersedes #18 D5c)". #18 annotated (D5c superseded); depends on #21.
