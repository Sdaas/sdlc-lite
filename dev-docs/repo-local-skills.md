# Repo-local skills — the SDLC for changing `sdlc-lite` itself

Four slash commands govern work on **this repo**: `/issue`, `/feature`, `/fix`, and `/review-repo`
for the full-repo review before a release. They live in
`.claude/skills/`, are **not shipped** with the plugin, and are **human-typed only**
(`disable-model-invocation: true`) — the model never starts one on its own.

They share one process, so it is defined once:

- [`.claude/sdlc/gates.md`](../.claude/sdlc/gates.md) — **the *what*:** every gate, the four
  STOPs, the fast checks, both review checklists, the eval budget, the inherited rules.
- [`.claude/sdlc/runbook.md`](../.claude/sdlc/runbook.md) — **the *how*:** the hard rules and the
  per-gate steps both `/feature` and `/fix` execute.

Each `SKILL.md` adds only its entry condition (and, for `/fix`, two gates). This page is the map;
when it and `gates.md` disagree, `gates.md` wins.

## When each one fires

| You have… | Type | Run | Not this |
|---|---|---|---|
| An idea or a bug, no conforming issue | any | `/issue` — files one issue per [`issue-template.md`](issue-template.md) | — |
| An issue labelled `enhancement` | prose · hook · code | `/feature #NN` | a `bug` → `/feature` sends you to `/fix` |
| An issue labelled `bug` | prose · hook · code | `/fix #NN` | not a `bug` → `/fix` sends you to `/feature` |
| A release to cut (exit checklist) | — | `/review-repo <version> [<since-ref>]` — see [below](#review-repo--full-repo-review) | — |
| A docs-only or shell-only change | — | none — edit directly, normal review-before-commit | both skills decline at Gate 0 |

`/feature` and `/fix` both hand off to `/issue` when the `#NN` is missing or does not conform to the
template. "Code" means `guard.py`, `policy.py`, `agentdefs.py`, `analyzer/`.

## Gates and STOPs

| Skill | Gates run | STOPs |
|---|---|---|
| `/issue` | none of the spine — interview → draft → file | one: approve the draft |
| `/feature` | 0 – 11 | ① scope · ② design · ③ tests · ④ implementation |
| `/fix` | 0, 1, **1b REPRODUCE**, 2 – 8, **8b DEPOSIT**, 9 – 11 | the same four — no fifth |

The spine, one line per gate (full definitions in `gates.md`):

**0 CLASSIFY** (resolve the issue, surface, minimum tier, branch) → **1 INTERVIEW** (STOP ①) →
**2 DESIGN** (files, eval cases in run order, cost cap; STOP ②) → **3 WRITE-EVALS** (before any
prose) → **4 EVAL-REVIEW** (`opus`, cold; STOP ③) → **5 IMPLEMENT** (confirm red first) →
**6 CODE-REVIEW** (`opus`, cold, before further eval spend) → **7 VERIFY** (the declared tier) →
**8 REGRESSION** (tagged cases, fail-fast) → **9 REVIEW-GUIDE** → **10 HUMAN REVIEW** (STOP ④) →
**11 COMMIT**.

### What `/fix` adds

A fixed Python bug leaves a `pytest` behind; a fixed `SKILL.md` bug used to leave only a diff.
`/fix` exists to close that gap:

- **1b REPRODUCE** — after STOP ①, before DESIGN. Reproduce the bug at the cheapest tier that shows
  it (T2 `pytest`, else T1 eval case, else a human-attested T3 run). Below T3 the reproduction *is*
  the regression case, written now and shown red. Not reproduced → halt; no design for an
  unreproduced bug.
- **8b DEPOSIT** — after REGRESSION. The reproducing case, red before the fix and green at Gate 7,
  goes in the fix's commit and stays. T3-only → the recipe is posted on the issue and a follow-up
  asks for a cheaper case.
- **The reproduction tier is a floor:** nothing claims "fixed" at a weaker tier than the bug was
  reproduced at.

How the bug will be reproduced, and any T1 repro cost cap, is approved at STOP ① — which is why
no fifth STOP is needed. First real run: #61.

## Why not use `sdlc-lite` on this repo?

Because the plugin's spine rests on assumptions this repo breaks — the argument is
[`verification-ladder.md`](verification-ladder.md) §6. The gate-by-gate correspondence is the
*Mapping to `implement-feature`* table in `gates.md`. The two are not expected to converge.

## `/review-repo` — full-repo review

`/review-repo <version> [<since-ref>]` runs the full-repo review before each release. It is a step of the release
exit checklist. It is not part of the `/feature` spine: it has no gates and no STOPs.

- It spawns three `repo-area-reviewer` agents (A Product, B Install path and evals, C Docs, history,
  process and structure) and one `repo-review-consolidator`. Both agent files pin `claude-opus-5-5`
  at effort `high`.
- With a since-ref, only areas with a file changed since that ref get a reviewer. The report lists
  the other areas as not reviewed.
- A since-ref run checks the repo structure only when area C changed. Run a full review (no
  since-ref) before a release.
- Cost: the #86 run (9 areas) cost $28.35 — 10 agents, 546 turns. The 3-area figure is recorded by #87.
- `.claude/skills/review-repo/measure.py` reads the session transcripts and checks every agent
  against those fixed values. It also owns the area table (`AREAS`) and has a `plan` phase that
  lists the files per area. It measures three times: on the agent files before any agent
  starts (a wrong pin stops the run at no cost), after the area reviewers, and after the consolidator.
- **Hard stop.** A wrong pin stops the run before any agent starts. A wrong model, a wrong effort,
  an unknown effort or a wrong agent count makes the report start with
  `INVALID — not Opus 5.5 / high`. Nothing from that report is triaged.
- Run it in a fresh session, on a clean `main`. The skill files are the source of truth;
  [the proposal](proposals/full-repo-review-prompt.md) is a historical record.

## Planned

- `/regression` — the whole eval suite, 3 runs per case, before a release (#64, backlog).
