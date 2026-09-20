# Release plan — current & next release

_Forward-looking only, and designed to be resumed with **"read release-plan.md and continue."** This
file holds two things: the **narrative** (where we are, what the current and next releases are *for*)
and the **execution order** (given the milestone's issues, which order to implement them in). It does
**not** hold issue *specs* — **GitHub is the source of truth** for *which* issues ship
(milestones = releases); this file only adds the *ordering*, referencing each issue as
**`#NN` + its title as a convenience copy** so a reader knows what `#NN` is without a round trip.
Titles can drift — GitHub wins; re-check with `gh issue list --milestone "<title>" --state open`.
Decision history lives in the issues and the ADRs (`docs/developer-guide.md` §6);
release conventions live in `RELEASING.md`._

_Last updated: 2026-09-20._

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
5. Only touch this file when the *narrative* or the *execution order* changes (a release ships, an
   issue is added/closed/reordered). Reference issues as **`#NN` + title**; never copy an issue's
   *spec* here (that's GitHub's job).


--- 

## Current release — `1.0.0` (GA)

The GA build. Theme: **robustness and real-user UX hardening** — beta-validation feedback plus the
committed follow-ups from v1 acceptance: toolchain auto-install so a stranger can run it unaided, and
closing the test-quality and isolation-correctness gaps the acceptance runs surfaced. Milestone:
`1.0.0`; committed issues and their order are in **Execution order** above. Scope may grow or shrink
during the release — that's expected; when it ships, this section resets to the next release.

## Execution order (current release)

The order to implement the current milestone's open issues. Titles are a convenience copy — regenerate
the set from the milestone (step 2); GitHub owns the detail.

Current milestone: **`1.0.0`** (GA).

1. **#43** — `fix(guard-hook): bash_write_targets misreads scratch writes as product-tree writes`
   *First: self-contained, unit-testable on the host, and it removes the false denials that make the
   other three harder to verify in a dry run.*
2. **#44** — `feat(gate-7): pre-configure [tool.mutmut] in the python-starter fixtures`
   *After #43 — its verification is a clean Gate 7 mutmut run, which #43 stops the guard from blocking.*
3. **#37** — `feat(skill): add a mechanical pytest.raises match= check at gates 3 and 4`
   *After #43/#44 — proving it needs a Gate 7 run that isn't drowning in mutmut-setup noise.*
4. **#19** — `feat(toolchain): add a setup command that installs the pinned toolchain`
   *Last, and largest: a new command with a **blocking Open Question** (the command's name) that must
   be answered before work starts.*


## Next release — post-GA (not yet defined)

No milestone opened. Shape it from GA feedback plus the backlog; if beta validation surfaces enough to
warrant more probation before GA, open a `1.0.0-beta.3` milestone and pull scope out of `1.0.0`.

## Backlog

Deferred capability and polish — **open issues with no milestone**. Not tracked here; query GitHub:
`gh issue list --state open --search "no:milestone"`. Promote an issue into a milestone when it's
committed to a release.

---

## How to work an issue (per session)

Work happens **one issue per fresh session**.

1. Read the **GitHub issue** (`gh issue view NN --comments`) — it is the detailed spec.
2. **If goal / method / instructions are unclear — stop and ask.** State your understanding of
   Goal / Constraints / Instructions and get confirmation before writing anything.
3. Plan → get approval → phased execution. **Commit per logical unit; keep git history.**
4. Behavior lives in **Markdown** (`SKILL.md`, `agents/*.md`, `references/*`, `hooks.json`); the only
   real code is `guard.py` and `analyzer/`. Changing a gate's model/effort/tools = edit the matching
   `agents/*.md` frontmatter. Changing what an agent may read/write = update **both** the agent's prose
   inbox **and** `guard.py` (defense-in-depth).
5. **"Done" ≠ "the change exists."** Done = a **green end-to-end dry run in the dev container**
   (`DEVCONTAINER.md`). Host unit tests: `python3 -m pytest sdlc-lite-plugin -q`.
6. **Never commit before human approval.**
7. When done, close the issue; update this plan only if the release narrative changed.

**Branching:** feature branch per issue; merge to `main` per issue.

## Triage & releases

Releases are **GitHub milestones**; issues are labeled by **type only** (`bug`/`enhancement`/
`documentation`); **no milestone = backlog**. Full conventions + release procedure: `RELEASING.md`.
