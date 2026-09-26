# 53-plan — `/fix` skill (REPRODUCE + DEPOSIT) and the #48 close-out

**Issue:** [#53](https://github.com/Sdaas/sdlc-lite/issues/53) · **Parent:** #48 (`48-plan.md` P5) ·
**Milestone:** `0.1.0` · **Branch:** `53-fix-skill` · **Status:** plan approved; P1 next

Branch-scoped working plan. `git rm` this file (and `48-plan.md`) in the close-out commit (P5).
GitHub #53 is the spec; this file holds only the locked decisions, the phases and the tracker.

---

## 1. Locked decisions (agreed 2026-09-26)

| # | Decision | Rationale |
|---|---|---|
| F1 | **DEPOSIT = a case at the tier the bug was reproduced at.** T1 → an eval case in `sdlc-lite-plugin/evals/`; T2 → a `pytest`. T3-only → the repro recipe is recorded on the issue, a follow-up issue is filed, and the skill says plainly it cannot claim "fixed" below T3. | Deviates from the AC's "the eval case": a deterministic inbox/prose-consistency bug (e.g. #61) is reproduced for free by a T2 test; an eval case would be a costly proxy. |
| F2 | **REPRODUCE tries the free routes first** (read the files, T2). A T1 repro run needs its `--max-cost-usd` cap approved at **STOP ①**. | Keeps the spine rule "no eval money before approval" without a fifth STOP. |
| F3 | **DEPOSIT is its own gate, but thin.** The case is written at REPRODUCE (or Gate 3); DEPOSIT checks the recorded red-then-green evidence and that the case is in the commit split. | The AC says "adds two gates"; folding it into 3/9 hides the invariant. |
| F4 | **Numbering: `1b REPRODUCE`, `8b DEPOSIT`.** | `gates.md`: a skill may add gates, never renumber. |
| F5 | **`/fix` accepts only `bug`-labelled issues.** Decision-only outcomes (e.g. #63) are not `/fix`'s job. | Keeps the three skills' entry conditions disjoint. |
| F6 | **Docs:** new page `dev-docs/repo-local-skills.md` — gates, STOPs, when each skill fires, routing (bug → `/fix`, enhancement → `/feature`, docs → not gated), why it diverges from `sdlc-lite` (links ladder §6, not restated). Developer-guide §4 shrinks to the table + link. | AC: one `dev-docs/` page for all three skills. |
| F7 | **Root scripts stay at the root.** Recorded as a comment on #53. | ~105 references; moving them is churn with no user-visible benefit. |
| F8 | **Order:** build + merge `/fix` → run `/fix #61` on its own branch (the proof) → #53 close-out → close #53 and #48. #53 stays open until #61 is green. | The proof needs `/fix` on `main` to be a real, fresh-session run. |
| F9 | **Shared runbook** `.claude/sdlc/runbook.md` holds the per-gate *how* now in `/feature`'s `SKILL.md`; `/feature` and `/fix` both execute it. `gates.md` stays the *what*. | Decided pre-#53 (Q2c): two skills with duplicated how-to drift. |

## 2. Target layout

```
.claude/sdlc/gates.md          # + 1b REPRODUCE, 8b DEPOSIT, their STOP-① budget note, mapping rows
.claude/sdlc/runbook.md        # NEW — per-gate how-to, extracted from feature/SKILL.md
.claude/skills/feature/SKILL.md  # slimmed: entry conditions + hard rules + "execute runbook.md"
.claude/skills/fix/SKILL.md      # NEW — entry (bug only) + runbook + 1b + 8b
dev-docs/repo-local-skills.md    # NEW (P5)
```

## 3. Phases

| P | Deliverable | Verification |
|---|---|---|
| **P1** | Extract `/feature`'s per-gate how-to into `.claude/sdlc/runbook.md`; `feature/SKILL.md` keeps entry conditions + hard rules and points at it. **No behavior change.** | Cold read by an `opus` subagent: given only the new `feature/SKILL.md` + `runbook.md` + `gates.md`, it reconstructs the same gate sequence, STOPs and commands as the old `SKILL.md` (diff of the two answers). `./release-verify.sh --links-only`. |
| **P2** | `gates.md`: define `1b REPRODUCE` and `8b DEPOSIT` (F1–F4), STOP ① budget note, mapping-table rows; runbook sections for 1b / 8b. | Links check; `opus` cold review against the six review dimensions (consistency with the spine's "no eval money before STOP ③" and "never renumber"). |
| **P3** | `.claude/skills/fix/SKILL.md` (F5); `/feature` Gate 0 routes `bug` → `/fix` (drop "(#53)"); developer-guide §4 marks `/fix` available. **Commit + merge to `main`** (F8). | `/fix` appears in a fresh session's skill list and is not model-invocable (`disable-model-invocation: true`); `opus` cold review; `python3 -m pytest sdlc-lite-plugin -q`; links check. |
| **P4** | **Proof:** fresh session, `/fix #61` on branch `61-<slug>` — REPRODUCE at T2, DEPOSIT a `pytest`, fix, T3 `roman-numeral` to Gate 7 per #61. | Deposited case red before, green after; #61's own verification (incl. `claude plugin eval sdlc-lite-plugin --ablation none`, cap approved at that run's STOP ②). Lessons fed back into `/fix` here (on `53-fix-skill`). |
| **P5** | Close-out: `dev-docs/repo-local-skills.md` (F6); route from `dev-docs/README.md` and `CLAUDE.md` (`README.md` stays user-only); F7 comment on #53; `release-plan.md` (#53 → Closed, #48 closed); `git rm 48-plan.md 53-plan.md`. Close #53, then #48. | `./release-verify.sh --links-only`; `python3 -m pytest sdlc-lite-plugin -q`. |

**Commits:** P1, P2+P3 (one unit: the skill), P5 — each after a review list and your approval.

## 4. Progress tracker

- [ ] P1 — runbook extracted, `/feature` slimmed, cold-read parity
- [ ] P2 — `1b REPRODUCE` / `8b DEPOSIT` in `gates.md` + runbook
- [ ] P3 — `fix/SKILL.md`; `/feature` routes bugs; committed + merged to `main`
- [ ] P4 — `/fix #61` green (deposited case red → green)
- [ ] P5 — docs page + routing, F7 comment, release-plan, `git rm` both plans, close #53 and #48
