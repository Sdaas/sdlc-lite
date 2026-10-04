# #63 — move all gate pins to the latest dated models

Branch `63-latest-model-pins` from `main` · Tier **T1 + T2 + T3** · cap `--max-cost-usd 2` per invocation.

## Locked decisions (STOP ① 2026-10-04)
- Reviewers (`test-reviewer`, `code-reviewer`) → `claude-opus-5-5`; producers (`test-writer`,
  `implementer`, `verifier`) → `claude-sonnet-5-5`. All five dated: the `sonnet` alias still
  resolves to `claude-sonnet-5` on container CLI 2.1.288.
- ADR-2 rewritten: every isolated gate pins a dated id; every bump is deliberate + T3-verified.
- `claude-opus-4-8` swept from product prose, current docs, proposals, docstrings, sample docs and
  test fixtures (drift partner stays `claude-opus-5`; alias-matching tests stay).
- `dev-docs/findings/*` untouched (historical evidence). `.claude/sdlc/*` out (alias-only slot).
- Container `modelSettings` re-keyed to `claude-sonnet-5-5`. Issue retitled; release-plan title copy refreshed.
- Frontmatter is the single source of truth for pins (no separate config).
- Conductor-model verification → separate issue (human runs `/issue`).

## Design (STOP ② 2026-10-04)
Files: `agents/*.md` (5), `SKILL.md` (§36, model table + paragraph, Gate 0 render line),
`agentdefs.py` / `analyzer/receipt.py` / `analyzer/report.py` docstrings + legend,
`analyzer/SAMPLE-RECEIPT.md`, `TRANSCRIPT-FORMAT.md`, `tests/test_agentdefs.py`, analyzer test
fixtures, ADR-02, `adr/README.md`, `architecture.md`, `jumpstart.md`, 3 `proposals/*`,
`release-plan.md:68`, `.devcontainer/claude/settings.json`.

Verification, in run order:
1. T1 `gate-0-model-plan-pins` — regex: both new ids, no `claude-opus-4-8`; no `Agent` before confirm.
2. T2 `test_agentdefs.py` with the new `EXPECTED` (red first); full `pytest`.
3. Free: `git grep claude-opus-4-8 -- ':!dev-docs/findings' ':!sdlc-lite-plugin/evals'` is empty (the evals hold the intended "never 4-8" assertion and the recorded gate-1 history).
4. T3 `roman-numeral` — Gate 0 render shows both ids; receipt shows all five gates ✅ on the exact dated ids.
5. Gate 8: smoke cases, then `gate-0`-tagged.

## Design revision (STOP ② again, 2026-10-04) — from Gate 8
Gate 8 found `gate-3-raises-match` red 3/5 (test-writer on sonnet-5-5 skips the grep self-check)
and `gate-7-reads-test-plan` red 1/1 (grader false negative: code-reviewer reads `handoff/*.md` by glob).
- D1 `agents/test-writer.md` step 2: paste the `grep -n` output under `## Self-check` in `05-test-intent.md`.
  New grader `gate-3-raises-match/graders/self-check-recorded.md`.
- D2 `gate-7-reads-test-plan/graders/read-test-plan.md`: also accept a glob read of `handoff/*`.
- D3 README row for `gate-3-raises-match`.
Run: confirm red (D1 prose stashed) → implement → gate-3 ×3 green → gate-7 ×1 green. `--keep-temp` always.

## Tracker
- [x] 0 CLASSIFY · [x] 1 INTERVIEW (①) · [x] 2 DESIGN (②)
- [x] 3 WRITE-EVALS · [x] 4 EVAL-REVIEW (③, 2026-10-04) · [x] 5 IMPLEMENT · [x] 6 CODE-REVIEW
- [x] 7 VERIFY (T1 ✓ $0.17, T2 271 ✓, T3 roman-numeral receipt all five ✓) · [x] 8 REGRESSION (after D1–D3 all ✓) · [x] 9 REVIEW-GUIDE · [x] 10 HUMAN REVIEW (④ + T3 attested) · [ ] 11 COMMIT
