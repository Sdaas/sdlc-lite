# Sample trust receipt

An illustrative example of the **per-agent trust receipt** — the headline section of an
`/implement-feature` run report (`analyzer/report.py::render_receipt`). It attests to the two
guarantees: **(a) isolation** and **(b) bounded model/effort**. Paths and token counts here are
made up; the *shape* is exactly what the analyzer emits.

> These samples are hand-written illustrations kept in sync with the renderer. The live receipt is
> produced by `python -m analyzer.analyze_run --workdir .implement-feature/<run>/` at Gate 11.

---

## 1. What it looks like today (the #31 schema skeleton)

In the skeleton state the columns that need a *requested* value (model / effort → **#22**) or
content-level detection (files seen → **#30**) render `❔ UNKNOWN` — a deliberately honest verdict,
never a silent PASS. The columns whose raw data already exists are filled: the **actual** model +
effort (from the session transcript) and the guard's **grant/deny** counts (from the run-log). The
effort spread below is the #28 dev-time configuration (`code-reviewer` high, `test-reviewer` low,
the rest medium).

## Per-agent trust receipt

The receipt for the two guarantees — **(a) isolation** and **(b) bounded model/effort**. `❔ UNKNOWN` is a valid, honest verdict: the columns below are filled by their capability legs — **requested model/effort + match verdict by #22**, **files-content-seen by #30**. A blind/absent transcript degrades the *actual* columns to UNKNOWN too — never a silent PASS.

| Agent | Model (req → actual) | Effort (req → actual) | Files seen | Grants / Denies |
|---|---|---|---|---|
| conductor | ❔ UNKNOWN → claude-sonnet-5 | ❔ UNKNOWN → medium | ❔ UNKNOWN | 118 / 0 |
| code-reviewer | ❔ UNKNOWN → claude-opus-4-8 | ❔ UNKNOWN → high | ❔ UNKNOWN | 22 / 0 |
| implementer | ❔ UNKNOWN → claude-sonnet-5 | ❔ UNKNOWN → medium | ❔ UNKNOWN | 41 / 1 |
| test-reviewer | ❔ UNKNOWN → claude-opus-4-8 | ❔ UNKNOWN → low | ❔ UNKNOWN | 17 / 0 |
| test-writer | ❔ UNKNOWN → claude-sonnet-5 | ❔ UNKNOWN → medium | ❔ UNKNOWN | 29 / 0 |
| verifier | ❔ UNKNOWN → claude-sonnet-5 | ❔ UNKNOWN → medium | ❔ UNKNOWN | 13 / 0 |

_Legend: ✅ matches pin · ⚠️ effort deviates (either direction) · ❌ model mismatch · ❔ unknown (not yet filled, or transcript blind). Grants / Denies is the guard's own decision per call; `(?N)` = N legacy calls with no recorded decision._

### Sources (for manual cross-check)

The exact evidence this receipt was derived from — open these to verify any cell by hand:

- Run-log (grants/denies): `~/.claude/…/.implement-feature/07-add-retry-202609141530/handoff/run-log.jsonl`
- Transcripts (actual model/effort), per agent:
    - conductor: `~/.claude/projects/-Users-me-dev-myrepo/4667b56e-….jsonl`
    - code-reviewer: `~/.claude/projects/-Users-me-dev-myrepo/4667b56e-…/subagents/agent-1a2b.jsonl`
    - implementer: `~/.claude/projects/-Users-me-dev-myrepo/4667b56e-…/subagents/agent-3c4d.jsonl`
    - test-reviewer: `~/.claude/projects/-Users-me-dev-myrepo/4667b56e-…/subagents/agent-5e6f.jsonl`
    - test-writer: `~/.claude/projects/-Users-me-dev-myrepo/4667b56e-…/subagents/agent-7a8b.jsonl`
    - verifier: `~/.claude/projects/-Users-me-dev-myrepo/4667b56e-…/subagents/agent-9c0d.jsonl`

The `implementer`'s `41 / 1` shows one **denied** call the guard blocked (e.g. an attempt to edit a
test file). A denied call has no transcript effect, so the run-log is the only place it appears.

---

## 2. What it will look like once the legs land (illustrative preview)

Once **#22** supplies the requested model/effort + match verdicts and **#30** supplies
files-content-seen, the same run reads as a fully-adjudicated receipt. Note the ✅ verdicts, and how
the `test-reviewer`'s `low` effort — a deliberate *deviation* from a `medium` pin — surfaces as a
`⚠️` (the widened policy flags any deviation in either direction, but effort is the cost knob, so it
is a WARN, never trust-voiding):

| Agent | Model (req → actual) | Effort (req → actual) | Files seen | Grants / Denies |
|---|---|---|---|---|
| conductor | ✅ sonnet → claude-sonnet-5 | ✅ medium → medium | ✅ 6 files | 118 / 0 |
| code-reviewer | ✅ opus → claude-opus-4-8 | ✅ high → high | ✅ 4 files | 22 / 0 |
| implementer | ✅ sonnet → claude-sonnet-5 | ✅ medium → medium | ✅ 5 files | 41 / 1 |
| test-reviewer | ✅ opus → claude-opus-4-8 | ⚠️ medium → low | ✅ 3 files | 17 / 0 |
| test-writer | ✅ sonnet → claude-sonnet-5 | ✅ medium → medium | ✅ 4 files | 29 / 0 |
| verifier | ✅ sonnet → claude-sonnet-5 | ✅ medium → medium | ✅ 5 files | 13 / 0 |

And an **adversarial** run — the real proof — flips a cell to a trust-voiding verdict, e.g. a
wrong-model launch (`❌ opus → claude-sonnet-5`) or a leaked-content read surfacing in `Files seen`.
See `plan.md` → *v1 acceptance* for the injected-violation cases.
