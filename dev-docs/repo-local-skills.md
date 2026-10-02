# Repo-local skills — the SDLC for changing `sdlc-lite` itself

Three slash commands govern work on **this repo**: `/issue`, `/feature`, `/fix`. They live in
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

## Planned

- `/regression` — the whole eval suite, 3 runs per case, before a release (#64, backlog).
