# 60-plan — repo + open-issue audit; simplify developer-guide

**Issue:** [#60](https://github.com/Sdaas/sdlc-lite/issues/60) · **Milestone:** `1.0.0-beta.3` ·
**Branch:** `60-repo-review` · **Status:** audit + triage done; Phases A–B done; Phase C next.

Branch-scoped working plan. `git rm` this file in the merge/close commit.

## Resume here ("read 60-plan.md and continue")

1. `git switch 60-repo-review`; read §Locked decisions and §Progress, then the findings below.
2. Pick the first unchecked phase. Work it; present the review list; **commit only after approval**.
3. Issue edits (Phase B) are outward-facing: present them as one batch, apply after approval.
4. Tick the tracker in the same commit as the work.

## Locked decisions (grilling, 2026-09-25)

| # | Decision |
|---|---|
| Q1 | Shipped prose (`SKILL.md`, `agents/*.md`, `references/*`): consistency/wording fixes only, no rewrite. Rewrite = #62. |
| Q2/Q4 | Audit first, then triage, then fix. Issue edits proposed as a batch, applied after approval. |
| Q5 | Tracked by #60; branch `60-repo-review`; one commit per phase; merge before #51. |
| Q6 | Code: docs-match + tests + dead code only. No bug hunt. |
| Q7 | Reviewer model pins not changed here → #63 (backlog). |
| Q8/Q22 | Done = host pytest + `release-verify.sh --links-only` green, plus `claude plugin eval sdlc-lite-plugin --ablation none --tag gate-0` in the container **if** a commit touches `SKILL.md`/`references/*`. Agent-inbox fixes (P0-3..6) moved out to **#61** (beta.3, T3-verified). |
| Q9 | Prose bar: plain subject-verb sentences; define or drop jargon; each fact once, linked elsewhere; ADRs as Context/Decision/Consequences ~15–25 lines; dev-guide ~30–40% shorter. |
| Q10 | `developer-guide.md` stays one file; section numbers §0–§9 and ADR-1..14 unchanged. |
| Q11 | Topic owners: `DEVCONTAINER.md` = container lifecycle, auth, profiles, plugin load paths. `verification-ladder.md` = test tiers + `release-verify.sh`. `RELEASING.md` = channels + release mechanics. Dev-guide keeps fault injection + fixtures, links the rest. |
| Q12 | `CLAUDE.md` trimmed to conventions, hard rules, pointers. |
| Q13 | `findings/`, `proposals/`: links only, no prose edits. |
| Q14 | Root scripts stay; moving them is noted for #53's close-out. |
| Q15 | `SKILL.md` rewrite issue in `1.0.0` after #58 → **#62**. |
| Q16 | **#58 moved into beta.3** (the beta.3 eval gate can't pass without it). Done. |
| Q17 | #51: drop the `/issue` eval-case AC (matches 48-plan D13). |
| Q18 | #53: repo-local SDLC docs go in `dev-docs/` (not `README.md`, not `developer-guide.md`). |
| Q19 | Copy `design-system.md`, `planning-suite-architecture.md`, `planning-suite-restructure-plan.md` from branch `docs/planning-suite-architecture` (`docs/design/…`, root) into `dev-docs/proposals/`; fix links in #32/#46/#47. |
| Q20 | #44's Open Question answered: fixtures only; #40 covers real user repos. |
| Q21 | Merged branches deleted (local 50/54/57/59; remote 41/50/54/57/v1-trust-claim). Done. |

## Phases

| Phase | Scope (finding IDs below) | Commit | Verification |
|---|---|---|---|
| **A** | P0-1, P0-2, P0-7, P0-8, P0-9 — wording/consistency | `docs(repo): fix stale user + shipped-prose facts (#60)` | pytest, links, T1 `--tag gate-0` (touches `SKILL.md`, `quality-standards.md`) |
| **B** | P1-2..P1-13 issue edits (with Q17–Q20 answers) + Q19 file copy; `release-plan.md`: add #60 before #51, #58 + #61 into beta.3 order, #62 into 1.0.0 after #58 | `docs(proposals): …` + `docs(release-plan): …` | links |
| **C** | P2-1..P2-16 — cross-doc consistency + topic ownership (Q11) | `docs(dev-docs): …` | links |
| **D** | P3-1 developer-guide rewrite; P3-2 CLAUDE.md; P3-3 README | `docs(dev-docs): simplify developer-guide (#60)` | links; section/ADR numbers unchanged (`grep '^##' `) |
| **E** | Close-out: re-run pytest + links; T1 `--tag gate-0` eval in the container (deferred from A); `git rm 60-plan.md`; merge; close #60 | merge commit | eval green |

## Progress

- [x] Audit + triage; #60, #61, #62, #63 filed; #58 → beta.3; merged branches deleted
- [x] A — P0 wording fixes (pytest + links green; T1 `--tag gate-0` eval deferred to E, before merge)
- [x] B — issue edits + proposals copy + release-plan
- [ ] C — P2 dev-docs consistency
- [ ] D — P3 simplification
- [ ] E — close-out

---

# Findings

Baseline: host pytest 177/177 green · link check green · verify-entry-points not run (container).
Rec: **FIX** (in #60) · **ISSUE** (edit on GitHub) · **ASK** (decided — see Q-table) · **→#NN** (moved out).

---

## P0 — misleads a user or breaks the product

| ID | Where | Finding | Rec |
|---|---|---|---|
| P0-1 | `README.md:122` | Toolchain install command is broken: `~/.claude/plugins/**/sdlc-lite-plugin/toolchain/...`. A git-subdir install puts the plugin root at `~/.claude/plugins/cache/sdaas/sdlc-lite/<ver>/` (no `sdlc-lite-plugin` segment — `release-verify.sh:201-209`), and `**` doesn't recurse in bash without globstar. | FIX — give the real path, keep the by-name fallback |
| P0-2 | `references/quality-standards.md` §Environment + §Gate 0 | Tells agents the workflow "runs inside the project dev container… not supported on a bare host", and on preflight failure "tell the human to rebuild/enter the dev container… confirm we are inside the container". Contradicts README, SKILL.md Gate 0, and ADR-6. README Troubleshooting papers over it ("the message mentions rebuilding a dev container…"). | FIX — consistency fix to match SKILL.md (install toolchain into active env); drop the README caveat |
| P0-3 | `quality-standards.md` toolchain + "green" | Hardcodes `mypy src/`, `--cov=src`; `implementer.md` and SKILL use `<code_root>`. A flat-layout repo gets the wrong command. | →#61 |
| P0-4 | `agents/code-reviewer.md` inbox | Omits `04-test-plan.md`, yet it must check coverage/kill-rate "vs the threshold in the test plan". SKILL.md's inbox table also omits it for CODE-REVIEW. | →#61 |
| P0-5 | `agents/test-reviewer.md` inbox | Omits `04-test-plan.md`; SKILL.md Gate 4 says it reads it (and must judge coverage "per the test plan"). | →#61 |
| P0-6 | `agents/verifier.md` | SKILL Gate 6 step 3 (run concurrency stress/property checks when flagged) is missing from the agent def; no standards file in its inbox. | →#61 |
| P0-7 | SKILL.md §Observability #3, CLAUDE.md, dev-guide §4 job 5, tutorial §8 | All say write-confinement applies to the **test-reviewer** only. `policy.py:283-285` confines test-reviewer, verifier **and** code-reviewer. Same docs list the hook's tools without `Skill` and omit the explicit-entry job. | FIX — state the actual rule set |
| P0-8 | `dev-docs/tutorial.md:21,28,122-123` | Teaches "a command is a thin file that loads the skill… which is what the real product does" — the exact pattern ADR-14/#55 proved harmful and removed. | FIX |
| P0-9 | CLAUDE.md, dev-guide §4 end + §9, analyzer/README | "Change what an agent may read/write → update the prose **and `guard.py`**, keep the analyzer's mirrored predicate in sync." Rules now live in `policy.py` (single SSOT; nothing to mirror). Sends the next editor to the wrong file. | FIX |

## P1 — GitHub issues

| ID | Issue | Finding | Rec |
|---|---|---|---|
| P1-1 | release-plan / #58 | **Release-cut conflict.** beta.3's `release-verify.sh` runs the eval suite at `--threshold 0.8` on opus-5-5; the baseline is 5/7 because of #58 — which is scheduled in `1.0.0`, not beta.3. As planned, beta.3 cannot pass its own gate. | Done (Q16) — #58 moved to beta.3 |
| P1-2 | #51 | Contradiction: AC "two eval cases for `/issue`" vs 48-plan D13 "no evals for the three new skills". Plus the open comment: `/issue` isn't in the plugin, so the Verification command targets the wrong thing. | ISSUE — drop the eval AC + fix Verification (Q17) |
| P1-3 | #53 | AC "README routing updated for the repo-local SDLC" — README is user-only (#49); repo-local skills belong in `dev-docs/README.md` / `CLAUDE.md`. AC "developer-guide documents all three skills" adds weight to the doc we're trimming; `verification-ladder.md` §6 already holds the rationale. | ISSUE — both ACs → dev-docs (Q18) |
| P1-4 | #52 | Open Question already settled (no) but still listed as blocking; "Blocked by #50" is done. | ISSUE — move to a settled note |
| P1-5 | #48 | #50 unchecked though closed; #57/#59 (children per 48-plan P2) not listed. | ISSUE — tick #50; list #57 |
| P1-6 | #32, #46, #47 | Link to `dev-docs/proposals/design-system.md`, `planning-suite-architecture.md`, `planning-suite-restructure-plan.md` — none on `main`. They live on unmerged branch `docs/planning-suite-architecture` under `docs/design/…` (last commit 2026-09-20). | FIX + ISSUE — copy into `proposals/`, fix links (Q19) |
| P1-7 | #37 | Evidence says the findings doc was removed (see git history) — it exists at `dev-docs/findings/acceptance-31biii-error-message-contract-findings.md`. | ISSUE — fix link |
| P1-8 | #45 | Evidence cites `devcontainer.json:80`; logic now in `post-start.sh`. Memory notes `claude plugin list` shows "No plugins installed" yet the directory marketplace loads (#57 ran 16/16 on it). Likely the "command not found on fresh volume" symptom is gone; the load-path question remains. | ISSUE — refresh evidence; re-scope to the unverified live-load claim (repro during #45, not now) |
| P1-9 | #21 | "No setup script exists" — `test-fixtures/setup-fixture.sh` does; AC "scaffolds fixture repo(s)" overlaps it. | ISSUE — say it wraps setup-fixture.sh |
| P1-10 | #34 | Says `parse-duration` + `async-cached-json-fetcher` fixtures "already exist" — only `roman-numeral` exists. Also overlaps the #50 eval suite in spirit (automated re-proof). | ISSUE — fix evidence; add a line distinguishing it from T1 evals |
| P1-11 | #40 | Says code-reviewer is `effort: high` — now `medium` (#35). | ISSUE — fix |
| P1-12 | #39 | Not template-conforming (no `type(area):` title, no `**Type:**`, ~700 words, narrative). | ISSUE — rewrite to template |
| P1-13 | #44 | Open Question (fixtures only vs real-user repos) overlaps #40 (which is "what makes the fix general"). | ISSUE — answer: fixtures only (Q20) |
| P1-14 | Stale branches | Merged, not deleted: local `50-`, `54-`, `57-`, `59-`; remote `41-release-engineering`, `v1-trust-claim`, `50-`, `54-`, `57-`. | Done (Q21) |

## P2 — dev-docs cross-consistency

| ID | Where | Finding | Rec |
|---|---|---|---|
| P2-1 | README:128, CLAUDE.md:66 | "Auto-install is a v1.1 backlog item" — it's #19 in `1.0.0`. | FIX |
| P2-2 | README Status | Says "v1"; product is `1.0.0-beta.2`. "Requirements at a glance" duplicates Prerequisites. | FIX — current version line; drop duplicate |
| P2-3 | "only real code is guard.py + analyzer/" | CLAUDE.md, dev-guide §1, ladder §1, 48-plan. Also `policy.py`, `agentdefs.py`. | FIX |
| P2-4 | dev-guide §1 layout tree | Missing `policy.py`, `agentdefs.py`, `tests/`, `evals/`, `auditor.py`, `receipt.py`. | FIX |
| P2-5 | dev-guide §8 vs DEVCONTAINER | Plugin-install/load-path story told three ways: §8 step 5 "known gap, install by hand" (+ copies into cache), §8 "loads from workspace, cache vestigial", CLAUDE.md "no cache-sync". DEVCONTAINER (the owner per Q11) says none of it. | FIX — move to DEVCONTAINER as one statement: the three load paths + "unverified, see #45" |
| P2-6 | dev-guide §8 | "Install-from-GitHub verification" section is marked superseded, documents a path that no longer exists, and points "below" to a section above it. | FIX — delete (git history keeps it) |
| P2-7 | dev-guide §8 | "the User Guide documents that distinction" — no User Guide since #49. #21/#34 "are v1.1/v2" — #21 is in `1.0.0`. | FIX |
| P2-8 | dev-guide §8 vs DEVCONTAINER | "Fresh setup from zero", "Two Claude profiles", `.env` auth, release-verify walkthrough duplicated across dev-guide / DEVCONTAINER / RELEASING. | FIX — per Q11 ownership |
| P2-9 | DEVCONTAINER:3-4, :40 | "(and later the code-writing /implement-feature product)" stale; "no fixed name — the CLI names it" but `runArgs --name sdlc-lite-test`. | FIX |
| P2-10 | RELEASING §2 vs ADR-13 | Channel table + git-subdir rationale duplicated. | FIX — RELEASING owns mechanics; ADR-13 keeps decision + why |
| P2-11 | tutorial §8 gotcha 6, "Proving it" | "Don't rely on the transcript for anything critical / best-effort" — ADR-11 makes the transcript auditor the **authoritative** isolation leg. | FIX |
| P2-12 | analyzer/README | Tree omits `auditor.py`/`receipt.py`; "4 verdicts" (now 5); "once #22/#30 land" (landed); `--out` missing; "mirrors guard.py". | FIX |
| P2-13 | Code docstrings | `guard.py:182` "(added next commit)"; `guard.py:4` tool list; `agentdefs.py` example `effort: high` + "the guard fails OPEN on it" (guard no longer reads pins); SKILL.md:29 "floating `claude-opus-5`" (dated). | FIX — comments only, except SKILL.md (goes to the SKILL rewrite issue) |
| P2-14 | 48-plan.md | Status "not started"; §8 open item (`repo` area) already done; §2/§5 restate the ladder (D11 says link). | FIX — status + drop resolved item (file is deleted at #53 anyway) |
| P2-15 | verification-ladder | "T3 cannot be automated" vs "one slice of T3 is scripted" two paragraphs up; `/feature declines…` refers to a skill that doesn't exist yet. | FIX — wording |
| P2-16 | RELEASING status box | "beta.1 cut… 17/17" — beta.2 also cut; count is now 18. | FIX — drop the dated status boxes (RELEASING, ADR-13, ADR-14); git/issues hold history |

## P3 — simplify

| ID | Target | Plan |
|---|---|---|
| P3-1 | `developer-guide.md` (1,056 lines) | Keep §0–§9 + ADR numbers. Cut: §0 reading order → 3 lines; §3 history of #22/#36 (told 5×: §3, §5, ADR-12, agentdefs, guard) → once in ADR-12; §5 restated verdict lists → link analyzer/README; ADR-2 "lesson worth keeping" → findings link; ADR-12/13/14 → Context/Decision/Consequences ≤25 lines, tables kept; §8 → fault injection + fixtures + links (P2-5/6/8). Target ~600–650 lines. |
| P3-2 | `CLAUDE.md` | Rules + pointers; drop the architecture and guard-hook restatement. |
| P3-3 | README | Drop "Requirements at a glance"; tighten the lead bullets (line 22-23 is one 60-word sentence). |
| P3-4 | Root scripts | Recorded for #53 close-out (Q14). |
| P3-5 | →#62 | `SKILL.md` prose rewrite (eval-gated, `1.0.0` after #58): P-number jargon (P47, P53…) undefined for readers, #22/#36 history inline, model-pin rationale repeated 3×, `claude-opus-5` reference. |
| P3-6 | →#63 | Reviewer pins `claude-opus-4-8` while current Opus is 5.5 (ADR-2 intends a deliberate, re-verified bump). |
