# #86 — `/review-repo` skill, pinned to Opus 5.5 / high

Run: `/feature #86`, ad-hoc **tooling lane** (#70 not built yet; approved at Gate 0). Branch
`86-review-repo` from `main`. Scope: comment on #86 (STOP ①).

## Locked decisions (STOP ① + ②)

1. **SSOT:** the briefs move into the agent files; areas table + conductor steps into `SKILL.md`;
   the proposal keeps its prose, only its status note changes.
2. **Script:** `.claude/skills/review-repo/measure.py`, reusing `agentdefs.load_pins`,
   `analyzer.transcript.parse_subagents`, `analyzer.receipt.model_matches`. The shipped analyzer
   is not edited.
3. **Required values are constants** in the script (`claude-opus-5-5`, `high`, 9 area + 1
   consolidator) — a drifted pin cannot pass.
4. **Measure twice:** `--phase areas` (9 + 0; INVALID → stub report, no consolidator) and
   `--phase final` (9 + 1).
5. **Proof:** T2 pytest + two attested dev-container runs (green; wrong pin → INVALID). The green
   run's report is evidence only (`.md.tmp`); #87 runs the real review on `main`.

## Files

| File | Change |
|---|---|
| `.claude/agents/repo-area-reviewer.md` | new; `model: claude-opus-5-5`, `effort: high`, read-only tools |
| `.claude/agents/repo-review-consolidator.md` | new; same pins; writes only the report |
| `.claude/skills/review-repo/SKILL.md` | new; human-typed only; spawns by name, no `model` |
| `.claude/skills/review-repo/measure.py` | new |
| `sdlc-lite-plugin/tests/test_review_repo.py` | new; 18 tests |
| `dev-docs/repo-local-skills.md`, `dev-docs/developer-guide.md`, `CLAUDE.md` | list the skill |
| `dev-docs/proposals/full-repo-review-prompt.md` | status note only |

## Skipped gates (tooling lane)

Gate 3 writes pytest, not eval cases · Gate 4 reviews the pytest (checks 2–3) · Gate 5 confirms
the pytest red · Gate 7 has no T1 · Gate 8 re-runs pytest only.

## Gate 7 proof

- (a) Fresh dev-container session, `/review-repo` → 10 agents, `Measured: VALID`, report written.
- (b) `repo-area-reviewer` temporarily `effort: medium` → INVALID at the pre-flight `--phase pins`, no agent spawned
  (revised at STOP ② on 2026-10-04: the pre-flight makes a wrong pin cost $0).

## Progress

- [x] 0 CLASSIFY · [x] 1 INTERVIEW (STOP ①) · [x] 2 DESIGN (STOP ②)
- [x] 3 WRITE-TESTS (18 tests; counts exact, other agent types ignored) · [x] 4 REVIEW (STOP ③) · [x] 5 IMPLEMENT · [x] 6 CODE-REVIEW (7 findings fixed, re-review OK) · [x] 7 T2 (289 passed)
- [x] 7 VERIFY (a) — 10/10 opus-5-5/high; step 6 run by hand (bg-wait bug → fixed) · [x] 7 VERIFY (b) — pre-flight INVALID, 0 agents · [x] 8 REGRESSION (292 passed) · [ ] 9 GUIDE · [ ] 10 STOP ④ · [ ] 11 COMMIT
