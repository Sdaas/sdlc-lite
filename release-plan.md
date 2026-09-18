# Release plan — current & next release

_Forward-looking only, and designed to be resumed with **"read release-plan.md and continue."** This
file holds two things: the **narrative** (where we are, what the current and next releases are *for*)
and the **execution order** (given the milestone's issues, which order to implement them in). It does
**not** hold issue *lists or specs* — **GitHub is the source of truth** for *which* issues ship
(milestones = releases); this file only adds the *ordering*, referenced **by issue number only** so
the two can't drift. Decision history lives in the issues and the ADRs (`docs/developer-guide.md` §6);
release conventions live in `RELEASING.md`._

_Last updated: 2026-09-18._

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
   issue is added/closed/reordered). Reference issues **by number only** — never copy titles or specs
   here (that's GitHub's job).

## Execution order (current release)

The order to implement the current milestone's open issues — **numbers only**; GitHub owns the detail.
Regenerate the set from the milestone (step 2) and keep this list to the *sequence* and any blockers.

- `1.0.0-beta.1`: **#41** (release engineering) — **landed** 2026-09-18; the milestone has no other
  open issues, so the beta channel is cut. Nothing sequences behind it.

## Where we are

The trust-claim engine is **built and merged to `main`**: isolated, model/effort-pinned gates, a
policy SSOT + guard enforcement, a transcript-based auditor, and a per-run **trust receipt** proving
isolation and bounded model/effort held. As of **2026-09-18** it is also **cut as a versioned,
installable release**: #41 shipped the two-channel distribution + `release.sh`, and `1.0.0-beta.1`
and `1.0.0-beta.2` are tagged and public via the `Sdaas/claude-plugins` umbrella, verified by an
automated clean-room run (`release-verify.sh`, 17/17 — install + Gate 0/1 + a proven `/plugin update`
bump). The
one remaining gap that defines the beta→GA arc is **real-customer validation**.

## Current release — `1.0.0-beta.1`

A shippable, 1.0-quality build put in front of early customers before we commit to GA. Not
"half-built" — 1.0 on probation. Milestone: `1.0.0-beta.1`.

**Shipped.** [#41 — release engineering](../../issues/41) landed 2026-09-18, building the
**two-channel distribution** (dev directory-source vs. umbrella git-subdir tag-pinned release channel)
+ a cross-repo `release.sh`, and — the real gate — **proving** the process-produced plugin installs
cleanly from a clean environment (`release-verify.sh` 17/17: git-subdir GitHub install + Gate 0/Gate 1
+ a `/plugin update` bump proven to pick up a version change). `RELEASING.md` §2/§4/§5 and the README/User
Guide install commands are finalized against that verified path. Beta validation with early customers
is now the open work toward GA.

## Next release — `1.0.0` GA

Theme: **robustness and real-user UX hardening**, driven by beta validation feedback plus the
committed follow-ups from v1 acceptance (toolchain auto-install so a stranger can run it unaided;
closing the test-quality and isolation-correctness gaps the acceptance runs surfaced). Milestone:
`1.0.0`. Scope may grow or shrink during the release — that's expected; when GA ships, this section
is reset to the next release.

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
