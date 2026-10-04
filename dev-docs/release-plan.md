# Release plan — current & next release

_Forward-looking only, and designed to be resumed with **"read release-plan.md and continue."** This
file holds two things: the **narrative** (where we are, what the current and next releases are *for*)
and the **execution order** (given the milestone's issues, which order to implement them in). It does
**not** hold issue *specs* — **GitHub is the source of truth** for *which* issues ship
(milestones = releases); this file only adds the *ordering*, referencing each issue as
**`#NN` + its title as a convenience copy** so a reader knows what `#NN` is without a round trip.
Titles can drift — GitHub wins; re-check with `gh issue list --milestone "<title>" --state open`.
Decision history lives in the issues and the ADRs (`adr/`);
release conventions live in `RELEASING.md`._

_Last updated: 2026-10-04._

---

## Using this file ("read release-plan.md and continue")

1. **Find the current release** = the earliest open **milestone**:
   `gh api repos/:owner/:repo/milestones --jq '.[] | "\(.title) (open:\(.open_issues))"'`
2. **List its open issues** — that's the committed work for this release:
   `gh issue list --milestone "<title>" --state open`
3. **Pick the next issue** by the **Execution order** below (respect stated blockers); if the order is
   silent on an issue, use judgment. Then follow **How to work an issue**.
4. **If the current milestone has no open issues**, the release is ready to cut — follow the release
   procedure in `RELEASING.md`.
5. Each release section states its issues under the **four themes** (`RELEASING.md` §3).
6. Only touch this file when the *narrative* or the *execution order* changes (a release ships, an
   issue is added/closed/reordered). Reference issues as **`#NN` + title**; never copy an issue's
   *spec* here (that's GitHub's job).


--- 

## Current release — `0.1.0` (a usable `/implement-feature`)

Theme: **the first release a stranger can rely on.** `/sdlc-init` sets their Python repo up the
right way from day one (toolchain, coverage and mutation config), and no `/implement-feature` run
damages their repo or environment. 0.1.0 began as a process-and-tooling release (the repo-local
SDLC skills, #48, and the docs restructure, #49 — all closed below). On 2026-10-02 it was re-scoped
to also carry the customer-visible fixes that bar needs.

**Release bar.** A stranger installs the plugin, runs it on their own Python repo and finishes
without damage to the repo or environment and without undocumented workarounds. A bug that damages
the user's repo or environment is a release stopper, in every release. A manual step is acceptable
when its call to action is clear.

**Why `0.1.0` and not GA.** The plugin's source is prose, verified by the T1/T2/T3 ladder and the
eval corpus from #48. This is the first release to ship product changes verified that way, so it
proves the tooling before later releases depend on it.

| Theme | Issues |
|---|---|
| Customer-visible features | #19 |
| Customer-visible fixes / hardening | #75, #40, #68, #81, #63, #93 |
| Internal SDLC improvements | #89, #86, #92, #87, #88 |
| Internal SDLC fixes / hardening | — |

On 2026-10-02 **#43 and #74 were parked to the backlog**: textual shell parsing in the guard proved
to be whack-a-mole, and the write policy will be rethought first (rationale on #43).

## Execution order (current release)

Current milestone: **`0.1.0`**.

### Open — in execution order

_Product work is done. The release now runs through this exit checklist, in order. A fix after step 6
re-runs only the affected eval cases if it changes docs only. It re-runs the whole suite if it touches
`SKILL.md`, an agent file, `guard.py` or `policy.py`._

1. ~~#63 — latest model pins.~~ Done.
2. ~~#86 — `/review-repo` skill.~~ Done.
   2b. ~~#92 — cut the cost of a `/review-repo` run.~~ Done.
3. ~~#87 — full-repo review.~~ Done: `review-20261004.md`, 65 findings (7 in the 0.1.0 bucket).
4. ~~#93 — the guard writes every tool call to `if-runlog.jsonl`.~~ Done. Its T3 check moves to step 7.
   *Other 0.1.0-bucket findings:* B-1, B-2 + C-22, X-1 and C-6 are folded into #89. A-2 (wrong
   transcript folder name for paths with `.`; the receipt degrades to UNKNOWN, no damage) and B-3
   (`SKILL.md` says "dev container", the README is right) move to 0.2.0.
5. **#89** — `feat(release): changelog, evergreen README and release-notes step` — `CHANGELOG.md` template, README install/update section,
   the `release.sh` guard, the notes-drafting step (principles: `RELEASING.md` §7).
6. **#88** — `chore(repo): record a by-hand eval baseline for 0.1.0` — the whole suite, 3 runs per case, at the release commit.
   Record it in `sdlc-lite-plugin/evals/BASELINE-0.1.0.md` (model, claude version, commit, date at
   the top; known flakes labeled, e.g. #58). A regression later = any single case below its baseline
   rate. (The file lives outside `evals/results/`, which is gitignored.)
7. **Green dry run** in the dev container (`DEVCONTAINER.md`). Also check #93: no `if-runlog.jsonl`
   in the fixture root before Gate 0.
8. **Draft the 0.1.0 notes** from the closed issues and approve them.
9. **Run `release.sh`** — it bumps the version, tags `v0.1.0` and repoints the umbrella.
10. **Retrospective** — after the tag, review the whole release work and propose changes to the
   release process (`RELEASING.md` §7). File them as issues.

### Closed

| Issue | Done | What it settled for the open work |
|---|---|---|
| **#49** `docs(repo): restructure into README (user) + dev-docs/ (developer)` | 2026-09-23 (`13c4f7c`) | Every later doc edit lands in the final structure. |
| **#55** `fix(skill): a same-named command suppresses the implement-feature SKILL.md body` | 2026-09-24 (`2d4f1c6`) | The eval load path runs the real `SKILL.md` — #50's premise. |
| **#56** `fix(guard-hook): a bare, un-namespaced skill id bypasses explicit-entry` | 2026-09-24 (`e7d8b6b`) | Explicit-entry is enforced for both skill-id spellings. |
| **#50** `feat(repo): verification ladder + eval seed suite + release-verify hook` | 2026-09-24 (`6553a6a`) | T1/T2/T3 ladder + eval corpus: the quality signal for every later issue. |
| **#59** `chore(repo): bump the dev container claude so the eval gate can run on claude-opus-5-5` | 2026-09-25 (`35857b0`) | Container claude 2.1.281; first opus-5-5 baseline 5/7 (the gap is #58). |
| **#57** `test(repo): automate the 8-cell entry-point contract` | 2026-09-25 (`9f0bed7`) | `verify-entry-points.py`, 16/16 green; the #55 bug class is still live, so the check stays. |
| **#60** `docs(repo): audit repo + open issues for staleness; simplify developer-guide` | 2026-09-25 (`ab24d4c`) | Docs and open issues current; filed #61, #62, #63; moved #58 into 0.1.0. |
| **#51** `feat(repo): shared SDLC gate spine + /issue skill` | 2026-09-25 (`7247813`) | `.claude/sdlc/gates.md` is the spine #52/#53 execute, incl. the fail-fast eval budget; `/issue` filed #64 (`/regression`, backlog). |
| **#52** `feat(repo): /feature skill — 12 gates, 4 STOPs` | 2026-09-26 (`fc05474`) | Spine reworked to 12 gates / 4 STOPs (scope, design, tests, implementation), both reviews before any eval spend; proven by driving #37 end to end. Filed #65, #66. |
| **#45** `fix(toolchain): dev container never runs "claude plugin install"; live-workspace load path unverified` | 2026-09-26 (`574c15d`) | Fresh volume boots with the plugin live-loaded from the workspace (no install) and no onboarding/login/trust prompt; `~/.claude.json` keys are merged each start. |
| **#21** `feat(toolchain): add a clean-run harness that rebuilds the dev container per dry run` | 2026-09-26 (`5f61943`) | `make clean-run` resets to a known dry-run state in ~20 s (container reset, volume kept, `settings.json` re-seeded, fixtures, status table); `--rebuild` = no-cache image rebuild. #66 builds on it. |
| **#66** `feat(toolchain): hands-off dev-container test runs — fresh state, auto-auth, tmux, live progress` | 2026-09-26 (`d3ecef8`) | `make t3-start / t3-attach / t3-peek / t3-watch / t3-stop` (`dev-docs/t3-runs.md`): the agent launches and watches, the human only attaches, answers STOPs and attests; proven by a hands-off `roman-numeral` run. Filed #68, #69; moved #40 to `1.0.0`. |
| **#61** `fix(skill): agent inboxes and quality-standards disagree with SKILL.md` | 2026-10-02 (`e7fdc6c`) | First `/fix` run, and #53's proof: REPRODUCE at T2 (`test_inbox_parity.py` red, then green), T3 dry run. Its lessons became #72–#75. |
| **#53** `feat(repo): /fix skill — REPRODUCE + DEPOSIT gates` | 2026-10-02 | `/fix` adds 1b REPRODUCE + 8b DEPOSIT with no fifth STOP; shared `runbook.md`; `dev-docs/repo-local-skills.md`; root scripts stay at the root. Closes **#48** (`feat(repo): repo-local SDLC — verification ladder + /issue, /feature, /fix skills`). |
| **#73** `feat(repo): runbook — T3 evidence, flaky-case handling, --keep-temp on eval failure` | 2026-10-02 (`a7c0038`) | A failing `flaky` case is noted, not halted (no case is tagged since #76 removed the last one); a non-flaky failure gets one `--keep-temp` re-run; Gate 2 names the T3 fixture and evidence it exercises. |
| **#72** `fix(repo): t3-run.sh watch replays transcripts from earlier runs` | 2026-10-02 | `t3-start` touches `/tmp/t3-start.marker`; `watch` reads only newer transcripts (old ones kept), so #58's T3 watching is trustworthy. Done by hand (tooling, pre-#70). |
| **#58** `fix(skill): conductor sometimes skips the lock STOP and the explicit-entry redirect` | 2026-10-02 (`cbcc5e5`) | Second `/fix` run, reproduced from recorded T1 runs: the lock check is the first, sole action (`gate-0-lock-stop` 8/8, `flaky` removed). Routing can't be fixed in prose (the model never reads the skill list when built-in tools suffice) → #76. |
| **#76** `fix(skill): a plain request should get ordinary help; the routing case grades only auto-invocation` | 2026-10-02 (`072980a`) | Third `/fix` run, reproduced at T2 (`test_entry_points.py` §3): the description forbids only self-invocation, not ordinary help; `routing-no-autoinvoke` grades only auto-invocation (8/8, `flaky` removed); ADR-14 records why the workflow is opt-in. |
| **#71** `fix(repo): resolve contradictions and gaps in the repo-local spine` | 2026-10-03 (`07b2803`) | By hand, opus cold read before/after: 9 contradictions → 0. Adds *halt*, a `→ DESIGN` route, the whole-change diff (intent-to-add + merge-base), resume rules; "red" = the case fails. Remaining gaps → #79 (backlog). |
| **#67** `fix(repo): setup-fixture.sh leaves an untracked *.egg-info in every fixture run` | 2026-10-03 (`9f384cb`) | By hand (tooling, pre-#70): the fixture template ships a `.gitignore` (not `.coverage`) and `clean-run.sh` counts untracked files again, so a dirty `git status` after a dry run is the workflow's doing. #70 needs another tooling issue as its proof run. |
| **#44** `feat(repo): ship the python-starter fixtures configured as /sdlc-init would leave them` | 2026-10-03 (`2cc5e42`) | By hand (tooling, pre-#70): `roman-numeral` ships `[tool.mutmut]` `source_paths`, ignores `mutants/`, and kills all 6 baseline mutants. T3: Gate 7 ran `mutmut run` once (51/51, no setup loop). #19 now pins `mutmut>=3` (#40 then pinned `==3.8.0`). |
| **#40** `feat(gate-7): the conductor runs coverage and mutmut; the code-reviewer only reads results` + **#75** `fix(guard-hook): critic's pytest --cov writes .coverage into the product tree` | 2026-10-03 (`9352965`) | `/feature` run: before the Gate 7 dispatch the conductor measures into `<artifact_dir>/quality/` (`COVERAGE_FILE`, `mutmut results --all true`, `mutants/` removed); a mutmut error halts with a `/sdlc-init` pointer; `skip — <reason>` is the only skip. The guard denies critics `mutmut` / `pytest --cov`; `mutmut==3.8.0` pinned. T3 `roman-numeral`: no `.coverage*` / `mutants/` in the product tree, reviewer 0 denials. |
| **#68** `fix(guard-hook): read-only critics can run pip install and repoint the user's environment` | 2026-10-03 (`ad9c486`) | `/fix` run, reproduced at T2 (guard subprocess test, 6/6 red): `policy.changes_environment()` denies critics `pip`/`pip3`/`pipX.Y` install/uninstall, `python -m pip`, `uv pip install/uninstall/sync` (rule `critic-env-change`, architecture.md §5 row 9); conductor and implementer unaffected. Gate 8 smoke 3/3. No T3; critic briefs don't mention pip yet. |
| **#19** `feat(skill): /sdlc-init — set a Python repo up for /implement-feature` | 2026-10-03 (`4e4f110`) | `/feature` run: `/sdlc-init` measures with read-only `toolchain/setup_check.py` (found / floor / action table + missing config), shows one plan, applies it after approval, runs a `mutmut run "*__mutmut_1"` smoke test, never commits; a 2nd run is a no-op. Gate 0 checks all seven pins + mutmut config and stops with "run `/sdlc-init`". `mutmut>=3`; both fixtures carry exactly its config. T3 `roman-numeral` (`ENTRY=/sdlc-init VENV=1`): install + upgrade, no-op re-run, `/implement-feature` through Gate 7 (mutmut 90.9%), #68 import check held; `git init` offer attested in a non-git copy (T1 can't stage "not a repo"). |
| **#81** `fix(skill): critic briefs don't state the pip install/uninstall guard rule` | 2026-10-04 (`1d1995d`) | `/fix` run, reproduced at T2 (`test_inbox_parity.py` red): `code-reviewer`, `verifier`, `test-reviewer` briefs state guard rule 9 in the deny reason's words (never change the Python environment; a missing dependency is a finding, not retried or worked around); a host test fails if a brief drops it. T1 waived (guard-enforced). Gate 8 5/5 run, `guard-secret-read-denied` failed once (unrelated; filed separately). |
| **#63** `chore(skill): move all gate pins to the latest dated models` | 2026-10-04 (`d26e5cd`) | `/feature` run: all five `[I]` gates pin dated ids — reviewers `claude-opus-5-5`, producers `claude-sonnet-5-5` (the `sonnet` alias still resolved to `claude-sonnet-5`); ADR-2 is "every isolated gate pins a dated model", frontmatter the SSOT; `test_agentdefs.py` tripwires keep SKILL.md's ids equal to the pins. T3 `roman-numeral` receipt: all five ✅ exact. Gate 8 found the test-writer skipping its `pytest.raises` grep self-check on sonnet-5-5 (3/5) → the grep output is now a `## Self-check` deliverable in `05-test-intent.md` (3/3 green). Filed #84, #85; evidence added to #80. |
| **#86** `feat(repo): /review-repo skill — full-repo review pinned to Opus 5.5 at high effort` | 2026-10-04 (`59176bf`) | `/feature` run in an ad-hoc tooling lane (#70 not built): 9 area agents + 1 consolidator in `.claude/agents/`, pinned `claude-opus-5-5` / `high`; `measure.py` checks the pins before any spawn (a wrong pin costs $0) and the transcripts after the areas and after the consolidator, against fixed values. Real run: 10/10 at opus-5-5/high, but ~$28 → #92; the conductor didn't wait for the consolidator (fixed in prose, proven by #87). Wrong-pin run: INVALID at pre-flight, 0 agents. |
| **#92** `feat(repo): cut the cost of a /review-repo run` | 2026-10-04 (`5ca71db`) | `/feature` run, tooling lane: 9 areas → 3 (A product · B install path and evals · C docs, history, process, structure) + consolidator; `measure.py` owns the area table, adds a `plan` phase and `--since <ref>` (only changed areas are reviewed; the expected count is derived from the diff, never passed in). A since-ref run checks structure only when area C changed, so the pre-release run is a full one. Canary dropped. T2 only (305 passed, $0); #87's run is the T3 proof and the "after" cost. |
| **#87** `chore(repo): run the full-repo review and triage findings before 0.1.0` | 2026-10-04 (`7abeddc`) | `/review-repo` full run: 3 areas + consolidator, 4/4 at opus-5-5/high, the conductor ran the final measurement on its own (#86 wait rule proven); $11.61 vs the $28.35 baseline (#92 proven). 65 findings in `review-20261004.md`. 0.1.0: #93 (A-1); B-1, C-6 folded into #89. All other findings (incl. A-2, B-3) target 0.2.0 and are filed as issues when 0.2.0 starts. |
| **#93** `fix(guard-hook): the guard writes every tool call to if-runlog.jsonl in every project's root` | 2026-10-04 (`f9a1c48`) | `/fix` run, reproduced at T2 (4 guard subprocess tests red): with no `.active-run` and no `$IF_RUNLOG` the guard writes no audit line (project-dir and `/tmp` fallbacks gone). Every deny rule stays global (AC 3); with no handoff dir, confined critics write only to scratch. `.gitignore` lines keep `if-runlog.jsonl`. Gate 8 9/9 (`gate-0-model-plan-pins` failed once on its regex grader, then passed twice). T3 check folded into step 7. |

## Next release — `0.2.0` (the planning suite)

Theme: **`/design-system` and `/plan-feature` as customer features**, built by dogfooding `/feature`.
0.2.0 ships only with **both** skills. #47 and #32 are epics; splitting them into child issues is
the first task when 0.2.0 starts (not before), and each child then runs through `/feature`. The
`/implement-feature` quality backlog (#46) stays parked until the suite ships.

| Theme | Issues |
|---|---|
| Customer-visible features | #47, #32 |
| Customer-visible fixes / hardening | #78 |
| Internal SDLC improvements | #70, #64, #94, #62, #90, #77 |
| Internal SDLC fixes / hardening | — |

**Execution order:**

0. **File issues from `review-20261004.md`** (#87) — every next-release and backlog finding, plus
   A-2 and B-3 from the 0.1.0 bucket; skip the ones #93 and #89 closed. Group by root cause, follow
   `issue-template.md`, then place them in this order. *First, together with splitting #47 and #32.*
1. **#70** — `feat(repo): widen /feature Gate 0 to accept tooling issues`
   *First, so every non-docs issue in this release — tooling included — runs through `/feature` or `/fix`.*
2. **#64** — `feat(repo): add a /regression skill that runs the full eval suite, 3 runs per case`
   *Before the planning-suite prose lands, so regressions in the existing cases show up early.*
2b. **#94** — `feat(repo): per-agent run statistics in /review-repo, /feature and /fix reports`
   *After #70, so it runs through `/feature`; every later run then reports its own cost.*
3. **#62** — agent-facing prose pass (retitled; #83 folded in) — *one pass over `SKILL.md`, agent
   files and references: precise wording plus Opus 5.5 practices. Gated by the 0.1.0 baseline
   and `/regression`; lands before the planning-suite prose so the new skills start in the cleaned style.*
4. **#90** — `docs(docs): rewrite human-read docs in ASD-STE100 style` — ASD-STE100 rewrite of README and dev-docs (`developer-guide.md` §5).
   *No eval gate (link check only), so it can run at any point in the release.*
5. **#77** — `chore(skill): drive a large decomposable feature through /implement-feature and record how it fails`
   *Before #32 is split: its design is pinned to the observed failure, not an imagined one.*
6. **#47** — `feat(skill): /design-system — model a system into durable capability specs`
   *Split into child issues, then built child by child through `/feature`.*
7. **#32** — `feat(skill): /plan-feature — decompose one capability into a buildable A/B/C/Z DAG`
   *After #47: it decomposes a capability `/design-system` produced. Split, then built the same way.*
8. **#78** — `feat(skill): every terminal STOP ends with one exact command the user can run`
   *Covers `/sdlc-init`'s STOPs too, so after #19.*

**Moved on 2026-10-02:** #63, #44 and #19 to 0.1.0; #62 to the backlog (no prose rewrite right
before a release). **On 2026-10-04** #62 moved to 0.2.0, after #64 and the 0.1.0 baseline; #83 was folded into it and closed.
Earlier: #45 and #21 to 0.1.0 (2026-09-26).

**Proposed for 0.3.0:** a retrospective analyzer — where the conductor and the isolated agents spend
time and tokens, loops, waste (epic **#91** `feat(analyzer): retrospective analysis…`, no milestone yet; children #65, #69, #80). 0.2.0 stays the planning suite.

**Closed early:** **#37** `feat(skill): add a mechanical pytest.raises match= check at gates 3 and 4`
— 2026-09-26 (`e2a33e7`), as the `/feature` proof run; its T3 reached Gate 7 with no loop.

## Backlog

Everything else — **open issues with no milestone**, including work that was previously milestoned
here but isn't committed now (e.g. **#43**, **#74**, parked 2026-10-02; **#79**, filed 2026-10-03). Not tracked here; query GitHub: `gh issue list --state open --search "no:milestone"`.
Promote an issue into a milestone when it's committed to a release.

---

## How to work an issue (per session)

Work happens **one issue per fresh session**.

1. Read the **GitHub issue** (`gh issue view NN --comments`) — it is the detailed spec.
2. **If goal / method / instructions are unclear — stop and ask.** State your understanding of
   Goal / Constraints / Instructions and get confirmation before writing anything.
3. Plan → get approval → phased execution. **Commit per logical unit; keep git history.**
4. Behavior lives in **Markdown** (`SKILL.md`, `agents/*.md`, `references/*`, `hooks.json`); the only
   real code is `guard.py` + `policy.py` and `analyzer/` + `agentdefs.py`. Changing a gate's
   model/effort/tools = edit the matching `agents/*.md` frontmatter. Changing what an agent may
   read/write = update **both** the agent's prose inbox **and** `policy.py`.
5. **"Done" ≠ "the change exists."** Done = a **green end-to-end dry run in the dev container**
   (`DEVCONTAINER.md`). Host unit tests: `python3 -m pytest sdlc-lite-plugin -q`.
6. **Never commit before human approval.**
7. When done, close the issue; update this plan only if the release narrative changed.

**Branching:** feature branch per issue; merge to `main` per issue.

## Triage & releases

Releases are **GitHub milestones**; issues are labeled by **type only** (`bug`/`enhancement`/
`documentation`); **no milestone = backlog**. Full conventions + release procedure: `RELEASING.md`.
