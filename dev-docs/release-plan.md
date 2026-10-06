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

_Last updated: 2026-10-05 (0.1.0 accepted; 0.1.1 opened)._

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
7. **The Closed table is for the current release only.** Add a row when one of its issues closes;
   at release time it is the source for the `CHANGELOG.md` entry (`RELEASING.md` §4). When the
   release ships, delete its whole section: the changelog is the permanent record.


--- 

## Current release — `0.1.1` (first-run fixes from the 0.1.0 acceptance run)

Current milestone: **`0.1.1`** (patch release).

Theme: **a stranger's first run has no red errors on the normal path.** The 0.1.0 acceptance
run (#100) passed, but a stranger who follows the README saw failures and alarms that read as "the
plugin is broken". 0.1.1 removes them. Cut it with `release.sh`; accept it with a new acceptance
run (`ACCEPTANCE.md`).

| Theme | Issues |
|---|---|
| Customer-visible fixes / hardening | #101, #102, #103, #104 |

**Execution order:**
1. ~~**#101** — `fix(skill): /sdlc-init smoke test fails on a stranger's first run`~~ ✅ done (`b028c3e`)
   *First: it sets the step order that #104 documents.*
2. ~~**#102** — `fix(skill): /sdlc-init changes land in the first feature commit`~~ ✅ done (`02ed86d`)
   *Touches `/sdlc-init`'s finish message and Gate 0, after #101.*
3. **#103** — `fix(guard-hook): the verifier's scratchpad writes show as a breach`
4. **#104** — `docs(docs): README Quick start matches what a stranger actually does`
   *Last: documents the flow #101 and #102 leave behind, and `ACCEPTANCE.md` §4's exact user steps.*

**How 0.1.1 runs** (human decisions, 2026-10-05):
- #101–#103 each run through `/fix #NN` (human-typed), one per fresh session. #104 (docs) by hand.
- No eval spend (the procedure is unsound until #99): `/fix` Gate 8 is waived; each fix rests on
  its REPRODUCE test and the final acceptance run.
- **Before the cut:** host tests (`python3 -m pytest sdlc-lite-plugin -q`) and a green dry run in
  the dev container on `main` with all four fixes in.
- **Cut:** `CHANGELOG.md` `## 0.1.1`, then `release.sh 0.1.1`.
- **After the cut** (the acceptance container installs only released tags):
  `release-verify.sh --no-evals`, then a fresh acceptance run (`ACCEPTANCE.md` §4–§5). Close the
  milestone only when both pass.

### Closed (feeds the `## 0.1.1` entry in `CHANGELOG.md`)

| Issue | Done | What it settled |
|---|---|---|
| **#101** `fix(skill): /sdlc-init smoke test fails on a stranger's first run` | 2026-10-05 (`b028c3e`) | `/sdlc-init` offers `pip install -e .` in its plan when the package won't import; a smoke test with no mutants is a plain skip, not a failure |
| **#102** `fix(skill): /sdlc-init changes land in the first feature commit` | 2026-10-06 (`02ed86d`) | `/sdlc-init`'s finish prints the commit command for its edits; `/implement-feature` Gate 0 stops on a dirty tree (commit first, or `include`), so setup and feature land in separate commits |

_0.1.0 shipped 2026-10-05 (milestone closed); its record is the `## 0.1.0` entry in
`CHANGELOG.md`._

## Next release — `0.2.0` (the planning suite)

Theme: **`/design-system` and `/plan-feature` as customer features**, built by dogfooding `/feature`.
0.2.0 ships only with **both** skills. #47 and #32 are epics; splitting them into child issues is
the first task when 0.2.0 starts (not before), and each child then runs through `/feature`. The
`/implement-feature` quality backlog (#46) stays parked until the suite ships.

| Theme | Issues |
|---|---|
| Customer-visible features | #47, #32, #98 |
| Customer-visible fixes / hardening | #78, #96, #97 |
| Internal SDLC improvements | #70, #64, #94, #62, #90, #77, #100 |
| Internal SDLC fixes / hardening | #99, #95 |

**Execution order:**

0. **File issues from `review-20261004.md`** (#87) — every next-release and backlog finding, plus
   A-2 and B-3 from the 0.1.0 bucket; skip the ones #93 and #89 closed. Group by root cause, follow
   `issue-template.md`, then place them in this order. *First, together with splitting #47 and #32.*
0b. **#99** — `fix(repo): one eval procedure — Opus-pinned conductor and judge, one pass rule, baseline re-recorded`
   *Before any issue that spends eval money: every later eval verdict compares against its baseline.*
1. **#70** — `feat(repo): widen /feature Gate 0 to accept tooling issues`
   *First, so every non-docs issue in this release — tooling included — runs through `/feature` or `/fix`.*
2. **#64** — `feat(repo): add a /regression skill that runs the full eval suite, 3 runs per case`
   *Before the planning-suite prose lands, so regressions in the existing cases show up early.*
2b. **#94** — `feat(repo): per-agent run statistics in /review-repo, /feature and /fix reports`
   *After #70, so it runs through `/feature`; every later run then reports its own cost.*
2c. **#95** — `fix(repo): dev container runs the base image's tool copies instead of the installed toolchain`
   *Before the next T3 run, so every dry run checks with the toolchain preflight measured.*
2d. **#96** — `fix(gate-3): a test file that passes ruff before the module exists fails I001 at IMPLEMENT`
   and **#97** — `fix(gate-3): a test that lists a module's names aborts mutmut at Gate 7`
   *Both cost a loop in the 0.1.0 dry run. After #64, so `/regression` gates them; before #62.*
2e. **#98** — `feat(skill): declare test-only libraries as dev dependencies`
   *Touches `/sdlc-init` and `/implement-feature`; before #62.*
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

**Closed early:** **#100** `feat(repo): acceptance container — a stranger's machine for the release's human run`
— 2026-10-05, built for 0.1.0's step 9d. **#37** `feat(skill): add a mechanical pytest.raises match= check at gates 3 and 4`
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
7. When done, close the issue and add its row to the current release's **Closed** table; update the narrative only if it changed.

**Branching:** feature branch per issue; merge to `main` per issue.

## Triage & releases

Releases are **GitHub milestones**; issues are labeled by **type only** (`bug`/`enhancement`/
`documentation`); **no milestone = backlog**. Full conventions + release procedure: `RELEASING.md`.
