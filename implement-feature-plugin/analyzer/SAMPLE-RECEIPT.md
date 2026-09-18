# Sample trust receipt

An illustrative example of the **per-agent trust receipt** — the headline section of an
`/implement-feature` run report (`analyzer/report.py::render_receipt`). It attests to the two
guarantees: **(a) isolation** and **(b) bounded model/effort**. Paths and token counts here are
made up; the *shape* is exactly what the analyzer emits.

> These samples are hand-written illustrations kept in sync with the renderer. The live receipt is
> produced by `python -m analyzer.analyze_run --workdir .implement-feature/<run>/` at Gate 11.

---

## 1. A clean run — fully adjudicated

Both capability legs have landed: **#22** fills the *requested* model/effort from the agent-def
pins and verdicts them against the transcript *actual*; **#30** fills *Files seen* from the content
auditor. In a clean run every scanned gate reads ✅. The effort spread below is the #28 dev-time
configuration (`code-reviewer` high, `test-reviewer` low, the rest medium) — and since the pin *is*
the spread, actual == pin, so effort reads ✅ too. The **conductor** has no agent-def pin (the plugin
cannot pin the session model), so its requested side is an honest `❔ UNKNOWN` — never a silent PASS.

## Per-agent trust receipt

The receipt for the two guarantees — **(a) isolation** and **(b) bounded model/effort**. Each row compares the **requested** pin (agent-def frontmatter) against the **actual** value (transcript): a model mismatch is trust-voiding (❌), an effort deviation is a ⚠️ (the cost knob, not trust). `❔ UNKNOWN` is a valid, honest verdict — a blind/absent transcript degrades the *actual* columns, and the conductor has no agent-def pin to check; never a silent PASS.

| Agent | Model (req → actual) | Effort (req → actual) | Files seen | Grants / Denies |
|---|---|---|---|---|
| conductor | ❔ UNKNOWN → claude-sonnet-5 | ❔ UNKNOWN → medium | ❔ UNKNOWN | 118 / 0 |
| code-reviewer | ✅ claude-opus-4-8 → claude-opus-4-8 | ✅ high → high | ✅ none | 22 / 0 |
| implementer | ✅ sonnet → claude-sonnet-5 | ✅ medium → medium | ✅ none | 41 / 1 |
| test-reviewer | ✅ claude-opus-4-8 → claude-opus-4-8 | ✅ low → low | ✅ none | 17 / 0 |
| test-writer | ✅ sonnet → claude-sonnet-5 | ✅ medium → medium | ✅ none | 29 / 0 |
| verifier | ✅ sonnet → claude-sonnet-5 | ✅ medium → medium | ✅ none | 13 / 0 |

_Legend: ✅ matches pin / no forbidden content · ⚠️ effort deviates (either direction) · ❌ model mismatch or content leak (run untrusted) · ❔ unknown (no pin, or transcript blind). Model match is alias/dated-aware: an alias pin (`sonnet`) accepts any same-family tier, a dated pin (`claude-opus-4-8`) demands an exact id. Grants / Denies is the guard's own decision per call; `(?N)` = N legacy calls with no recorded decision._

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

Notes on reading the receipt:
- The `implementer`'s `41 / 1` shows one **denied** call the guard blocked (e.g. an attempt to edit a
  test file). A denied call has no transcript effect, so the run-log is the only place it appears.
- The producers' `sonnet` (an **alias**) matches the transcript's resolved `claude-sonnet-5` because
  the match is family-aware for aliases; the reviewers' **dated** `claude-opus-4-8` must match the
  actual id **exactly** (a silent opus-tier drift would read ❌).
- The clean reviewer rows above (`✅ claude-opus-4-8 → claude-opus-4-8`) hold because pinned gates are
  **dispatched bare** (#36): the dated frontmatter pin is honored, not overridden by an alias-only
  inline model. (#22 once forced an inline model via a deny-if-unnamed hook, which broke exactly these
  dated pins → `claude-opus-5`; that leg was reverted in
  [#36](https://github.com/Sdaas/sdlc-lite/issues/36).) See `design/model-pinning-findings.md` §7.

---

## 2. An adversarial run — the real proof

A trust product shown only passing hasn't demonstrated the thing that makes it trustworthy. The
**caught violation** is the proof. Deliberately injecting the plan's acceptance violations flips the
offending cells to a trust-voiding verdict (the rest of the row still reports honestly):

| Agent | Model (req → actual) | Effort (req → actual) | Files seen | Grants / Denies |
|---|---|---|---|---|
| code-reviewer | ❌ claude-opus-4-8 → claude-sonnet-5 | ✅ high → high | ✅ none | 22 / 0 |
| test-writer | ✅ sonnet → claude-sonnet-5 | ✅ medium → medium | ❌ LEAK: 03-design-internal.md | 29 / 1 |

- **`❌ claude-opus-4-8 → claude-sonnet-5`** — a wrong-model launch: the reviewer ran on Sonnet, not
  its pinned Opus. The receipt is the backstop that catches it — and the receipt is the *real*
  guarantee. (#22 once tried to *enforce* the model at dispatch via a deny-if-unnamed hook; that leg
  rested on a false premise and broke the dated pins, so it was reverted in
  [#36](https://github.com/Sdaas/sdlc-lite/issues/36). The receipt/audit leg is authoritative and
  unaffected.)
- **`❌ LEAK: 03-design-internal.md`** — the content auditor found the internal design's text in the
  algorithm-blind test-writer's tool output (e.g. via a `cat handoff/*.md` glob the run-log's
  command-string view can't resolve). This **voids trust** for the run — #30 / ADR-11.

See `plan.md` → *v1 acceptance* for driving these injected-violation cases end-to-end.
