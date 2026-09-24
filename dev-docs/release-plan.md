# Release plan — current & next release

_Forward-looking only, and designed to be resumed with **"read release-plan.md and continue."** This
file holds two things: the **narrative** (where we are, what the current and next releases are *for*)
and the **execution order** (given the milestone's issues, which order to implement them in). It does
**not** hold issue *specs* — **GitHub is the source of truth** for *which* issues ship
(milestones = releases); this file only adds the *ordering*, referencing each issue as
**`#NN` + its title as a convenience copy** so a reader knows what `#NN` is without a round trip.
Titles can drift — GitHub wins; re-check with `gh issue list --milestone "<title>" --state open`.
Decision history lives in the issues and the ADRs (`developer-guide.md` §6);
release conventions live in `RELEASING.md`._

_Last updated: 2026-09-24._

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

## Current release — `1.0.0-beta.3` (process & tooling)

Theme: **get the house in order before GA.** Two pieces of groundwork, neither of which changes the
plugin's runtime behavior: a documentation restructure that gives the repo one discoverable shape,
and the repo-local SDLC skills that give *this repo* the requirements → design → test discipline the
`sdlc-lite` plugin gives a Python repo.

**Why before GA, and why it is a beta and not GA.** The six `1.0.0` issues are real behavior changes
to a product whose source is prose, and today they would be verified only by ad-hoc dry runs and
judgment. #48 supplies the missing verification primitive (`claude plugin eval` over `SKILL.md`, plus
the T1/T2/T3 ladder). Using new tooling for the first time on release-critical work is a risk, so the
release it is first exercised on is labeled **beta.3**, not GA — the tooling gets proven on real work
before `1.0.0` depends on it.

## Execution order (current release)

Current milestone: **`1.0.0-beta.3`**.

1. ~~**#55**~~ — `fix(skill): a same-named command suppresses the implement-feature SKILL.md body`
   **Done 2026-09-24** (`2d4f1c6`). *Was first, ahead of #50: the plugin shipped
   `commands/implement-feature.md` and `skills/implement-feature/SKILL.md` under the same name, and
   the command suppressed the skill body — the conductor then improvised gate prose. That is the
   path `claude plugin eval` uses, so #50's whole premise (eval as the T1 verification primitive)
   rested on this being fixed first.*
2. ~~**#56**~~ — `fix(guard-hook): a bare, un-namespaced skill id bypasses explicit-entry`
   **Done 2026-09-24** (`e7d8b6b`). *#55's explicit-entry rule keyed on the `sdlc-lite:` prefix, so
   one spelling of the `Skill` call was defended by the skill `description` alone. A one-surface
   policy change plus tests — cheap enough that it did not wait behind the milestone's larger work.*
3. ~~**#49**~~ — `docs(repo): restructure into README (user) + dev-docs/ (developer)`
   **Done 2026-09-23** (`13c4f7c`). *Docs-only, so it could not destabilize the plugin, and every
   later issue's doc edits now land in the final structure instead of being moved twice. It changed
   two path strings the shipped `SKILL.md` prints at runtime and inbound links in nearly every open
   issue — far cheaper before GA publishes them more widely. This file moved to
   `dev-docs/release-plan.md` as part of it.*
4. **#48** — `feat(repo): repo-local SDLC — verification ladder + /issue, /feature, /fix skills`
   *Tracking issue, not a unit of work — it ships as the four children below and closes when the
   last one closes. After #49 — its documentation is written directly into `dev-docs/` rather than
   written and then moved. Each child gets its own branch (`<NN>-<slug>`) and merges to `main` when
   green; nothing half-broken lands.*
5. ~~**#50**~~ — `feat(repo): verification ladder + eval seed suite + release-verify hook`
   **Done 2026-09-24** (`6553a6a`). *First of the four: the only one with standalone value — the
   ladder and the eval corpus are how any prose change to the plugin gets verified, skills or no
   skills. It is also every later child's quality signal. Follow-ups filed to the backlog: #58 (two
   prose deviations the suite caught) and #59 (container bump — the release-verify eval step pins
   `claude-opus-5-5`, which the container's claude cannot run yet).*
6. **#59** — `chore(repo): bump the dev container claude so the eval gate can run on claude-opus-5-5`
   *Next — a #50 follow-up. `release-verify.sh`'s eval step pins `claude-opus-5-5`, which the
   container's claude 2.1.260 rejects, so cutting beta.3 would mean `--no-evals` and skipping the
   very tooling this release exists to prove. Before #57, whose checker also runs in the container
   and is better built on the final container than re-verified after a bump.*
7. **#57** — `test(repo): automate the 8-cell entry-point contract`
   *After #50 — the checker is a rung of that issue's verification ladder, so it lands inside the
   ladder rather than beside it. It locks what #55 and #56 established: both slash spellings work in
   both session modes, and the model never starts the workflow on its own.*
8. **#51** — `feat(repo): shared SDLC gate spine + /issue skill`
   *After #50 — `.claude/sdlc/gates.md` links to the ladder rather than restating it, and
   `/issue`'s two eval cases need the suite to live in. The spine must land before #52 or #53 so
   neither invents its own gate prose. Settle the eval target first — `/issue` is repo-local, not in
   the plugin (see the comment on #51).*
9. **#52** — `feat(repo): /feature skill — 9 gates, 4 STOPs`
   *After #51 — it executes the spine. Its **Open Question** (whether `/feature` also updates
   this file) is settled: **no** — roadmap ordering stays a human call. #52 is unblocked.*
10. **#53** — `feat(repo): /fix skill — REPRODUCE + DEPOSIT gates`
   *Last — reuses #52's spine and adds the two gates that close the regression-safety gap. Also
   carries the close-out: the developer-guide rationale, README routing, this file's final update,
   and removing `48-plan.md`.*

## Next release — `1.0.0` (GA)

The GA build. Theme: **robustness and real-user UX hardening** — beta-validation feedback plus the
committed follow-ups from v1 acceptance: toolchain auto-install so a stranger can run it unaided, and
closing the test-quality and isolation-correctness gaps the acceptance runs surfaced. Milestone:
`1.0.0`. Scope may grow or shrink during the release — that's expected; when beta.3 ships, this
section becomes the current release.

**Execution order** (verified with the ladder and eval corpus from #48):

1. **#45** — `fix(toolchain): dev container never runs "claude plugin install"; live-workspace load path unverified`
   *First: every other issue's "Done" bar is a green dry run in the dev container — this is what
   makes a fresh container boot reliably testable at all, and it also settles whether workspace
   edits load live or need a reinstall, which the remaining issues' verification depends on.*
2. **#58** — `fix(skill): conductor sometimes skips the lock STOP and the explicit-entry redirect`
   *After #45 — a prose fix whose proof is the eval suite (`--tag gate-0 --tag routing --runs 8`)
   in the container. A runtime behavior change, so it waits for GA rather than beta.3.*
3. **#43** — `fix(guard-hook): bash_write_targets misreads scratch writes as product-tree writes`
   *Self-contained, unit-testable on the host, and it removes the false denials that make the
   other issues harder to verify in a dry run.*
4. **#44** — `feat(gate-7): pre-configure [tool.mutmut] in the python-starter fixtures`
   *After #43 — its verification is a clean Gate 7 mutmut run, which #43 stops the guard from blocking.*
5. **#37** — `feat(skill): add a mechanical pytest.raises match= check at gates 3 and 4`
   *After #43/#44 — proving it needs a Gate 7 run that isn't drowning in mutmut-setup noise.*
6. **#19** — `feat(toolchain): add a setup command that installs the pinned toolchain`
   *A new command with a **blocking Open Question** (the command's name) that must be answered
   before work starts.*
7. **#21** — `feat(toolchain): add a clean-run harness that rebuilds the dev container per dry run`
   *Last: automates the exact clean-boot verification loop the other issues rely on, so it
   should land once the boot path (#45) and the changes it will exercise (#43/#44/#37/#19) exist.*

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
