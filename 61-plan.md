# 61-plan — agent inboxes and quality-standards disagree with SKILL.md

Run via `/fix #61` on branch `61-agent-inbox-parity` (base `main`). Nothing committed yet — all work
is in the working tree. Became multi-session on 2026-09-26, hence this file (`git rm` at close).

## Locked decisions
- **STOP ① (approved):** scope per the issue comment; tier **T1 + T2 + T3**; repro route T2. AC2 already
  met by #37 (`agents/test-reviewer.md:19`) — not re-edited.
- **STOP ② (approved):** 4 prose files; eval cases `gate-7-reads-test-plan`, `gate-6-concurrency-policy`;
  cap `--max-cost-usd 3` per eval invocation.
- **STOP ③ (approved twice):** the cases; then the edited repro test after the Gate 6 finding.
- `gate-7-reads-test-plan` passes pre-fix (the reviewer finds the test plan anyway) — human chose
  **keep** it as a behavior guard; README row says so.

## Progress
- [x] 0 CLASSIFY · 1 INTERVIEW (STOP ①) · 1b REPRODUCE (T2 red)
- [x] 2 DESIGN (STOP ②) · 3 WRITE-EVALS · 4 EVAL-REVIEW (2 rounds, PASS; STOP ③)
- [x] 5 IMPLEMENT — confirm-red: gate-7 passes pre-fix (kept), gate-6 red; edits by sonnet; fast checks green
- [x] 6 CODE-REVIEW — round 1 CHANGES (SKILL Gate 6 parity, `dev-docs/architecture.md` §3 table,
      test extended), round 2 APPROVE; repro test re-red with fix stashed (8 failed); STOP ③ re-approved
- [x] 7 VERIFY — T2 green (9/9, suite 186); T1 gate-7 1.00 ($0.85), gate-6 1.00 ($0.24), 1 run each
- [x] 7 VERIFY — T3 re-run 2026-10-02 (fixture commit `4b8201a`): run-log shows `test-reviewer` and
      `code-reviewer` Read `04-test-plan.md`; `verifier` named the standards in its brief and wrote
      "No concurrency surface" but did **not** Read the standards (pure feature, nothing to look up) —
      human **accepted** at STOP ④ (AC is prose-level; met + T2-tested). Side findings (not #61): guard `cd`/`$VAR` false positives (reviewer
      tried `"py""project.toml"` splitting), `code-reviewer` ran `pip uninstall`/`pip install -e`
      (#68), reviewer `pytest --cov` left `.coverage` in the product tree.
- [x] 8 REGRESSION — smoke (3) → gate-0 (4) → gate-3, gate-4; cap $3 each; fail-fast
      - smoke ($0.71): entry-slash-bare 1.00, guard-secret-read-denied 1.00, routing-no-autoinvoke 0.50
        (no `/implement-feature` redirect) — human ruled known flake **#58**, excluded; continue
      - gate-0 ($0.86): entry-slash-bare 1.00, entry-slash-namespaced 1.00, gate-0-not-importable-stop 1.00,
        gate-0-lock-stop 0.50 (Bash ran despite lock) — #58 symptom, excluded per the same ruling
      - gate-3/4 ($0.57): gate-3-raises-match 1.00; gate-4-raises-match 0.75 (`names-bare-test` miss,
        verdict still CHANGES-REQUESTED). Re-run with `--keep-temp` ($0.32): **1.00**, 4/4 — single-run
        wording miss, not a regression. Gate 8 total $2.46.
- [x] 8b DEPOSIT — fingerprint unchanged (`ecd60abd`, no conftest/helpers) → no re-red needed; T2 green at 7;
      collected by `python3 -m pytest sdlc-lite-plugin -q` (186 passed). Link check green.
      Deposit: `sdlc-lite-plugin/tests/test_inbox_parity.py` — T2, last red 5, green at 7
- [x] 9 REVIEW-GUIDE · 10 HUMAN REVIEW (STOP ④ approved 2026-10-02) · 11 COMMIT → merge to main, close #61

## Notes
- `t3-run.sh watch` replays stale subagent transcripts from `~/.claude/projects/-workspaces-roman-numeral-run/`
  (two old `code-reviewer` guard denials) — filed as #72, out of scope for #61.
- #71 got one comment (Gate 2 "real conductor brief" ambiguity).
