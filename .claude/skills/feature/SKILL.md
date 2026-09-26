---
name: feature
description: Implement one GitHub issue for this repo (plugin prose, hooks, or guard/policy/agentdefs/analyzer code) through the repo-local spine — gates 0–11 with 4 human STOPs (scope, design, tests, implementation), eval cases before prose, opus reviews before any eval spend, and no commit before approval. Declines docs-only and shell-only changes.
disable-model-invocation: true
argument-hint: "#NN [optional note]"
---

# /feature — one issue through gates 0–11

Take the issue in `$ARGUMENTS` through **all twelve gates** of
[`.claude/sdlc/gates.md`](../../sdlc/gates.md). **Read that file first** — it defines every gate,
the four STOPs, the fast checks, both review checklists, finding routing, the eval budget and the
inherited rules. This skill adds only *how to execute* each gate here; where the two seem to
disagree, `gates.md` wins.

Announce each gate as you enter it (`Gate N — NAME`), so the human always knows where the run is.

## Hard rules

- **Never work on `main`.** Branch at Gate 0, before any edit.
- **Stop at every STOP.** End the turn and wait; never chain two STOPs in one turn.
- **Nothing is committed before STOP ④.** Silence is not approval.
- **No eval money before STOP ③.**
- **One issue per run.** Scope creep found mid-run → offer `/issue` for it, don't absorb it.

## Gate 0 — CLASSIFY

1. `$ARGUMENTS` has no `#NN` → ask for one, or offer `/issue` to file it.
2. `gh issue view NN --json number,title,state,labels,milestone,body,comments`. Not found, closed,
   or missing the required sections of [`dev-docs/issue-template.md`](../../../dev-docs/issue-template.md)
   → say what is missing, tell the human to run `/issue`, and **exit**. A `bug` → point to `/fix`
   (#53) and exit.
3. Classify the surface from the acceptance criteria. **Docs-only** (`README.md`, `dev-docs/**`)
   or **shell-only** (`*.sh`) → decline in one line and exit; those are not gated (ladder §3 has the
   one exception — a doc path the shipped `SKILL.md` prints).
4. Take the minimum tier from [`dev-docs/verification-ladder.md`](../../../dev-docs/verification-ladder.md)
   §3 (union across rows).
5. `git status` must be clean. Create `<NN>-<slug>` from `main`, or switch to it if it exists.
6. Plan file: warranted only if the work is multi-session, multi-phase or structurally complex.

## Gate 1 — INTERVIEW

Work the scope as a design tree, in rounds: ask the whole frontier at once, each question numbered
with your recommended answer, defaulting to the smaller option. Look facts up yourself; put only
decisions to the human. Open with the minimal version and the out-of-scope list. Issue ACs already
testable → say so and go straight to the STOP.

**STOP ①** — show the settled scope (in / out), the surface, the tier with its ladder §3 row, the
branch, plan file yes/no. On approval, post the scope as one issue comment:
`gh issue comment NN --body-file <file>`.

## Gate 2 — DESIGN

Present the items Gate 2 lists in `gates.md`, in that order. A case's prompt is what a user would
type — never the answer you expect (ladder §6, "simulating"). Write `<NN>-plan.md` now if Gate 0
said so; it holds the design and a progress tracker.

**STOP ②** — the design.

## Gate 3 — WRITE-EVALS

Write the cases under `sdlc-lite-plugin/evals/<case>/` (authoring: `dev-docs/eval-tutorial.md`);
add a row to the case table in `sdlc-lite-plugin/evals/README.md`. Code change: write the `pytest`.
Check the frontmatter parses. Run nothing that costs money.

## Gate 4 — EVAL-REVIEW

Spawn an ad-hoc subagent with **`model: opus`**. Brief: the issue body, the new case directories,
the prose files they target, and the four eval-review checks copied from `gates.md`. It returns one
line per check per case. Fix findings (Gate 3), re-review — at most twice.

**STOP ③** — the cases (paths + one line each) and the review verdict.

## Gate 5 — IMPLEMENT

1. **Confirm red** — each new case once, in design order (see *Running a case*); new `pytest` red.
   Record per case: fails · passes for the wrong reason (why) · **passes** (show it to the human).
2. Edit. In this session by default; spawn an ad-hoc subagent with **`model: sonnet`** when the
   diff spans more than 3 files or touches `guard.py`, `policy.py` or `analyzer/` — its brief is the
   approved design and the red cases, nothing else. Agent read/write change → both the agent's
   prose inbox and `policy.py` (root `CLAUDE.md`).
3. Run the fast checks until they pass.

## Gate 6 — CODE-REVIEW

Spawn an ad-hoc subagent with **`model: opus`**. Brief: `git diff main...HEAD` plus the
working-tree diff, the issue body, and the six dimensions and routing rules copied from `gates.md` —
**not** your reasoning or the answer you expect. It returns one line per dimension (`OK` · finding
with its `→ IMPLEMENT` / `→ WRITE-EVALS` target · `N/A — why`); a missing dimension → send it back
once. Route findings per `gates.md`; fast checks after every fix; re-review at most twice.

## Gate 7 — VERIFY

- **T1** — this change's new cases, in design order, fail-fast, one run each.
- **T2** — `python3 -m pytest sdlc-lite-plugin -q` (host).
- **T3** — give the human the exact dry-run steps (`dev-docs/DEVCONTAINER.md`) and what to look
  for. Collect the attestation at STOP ④; never mark it satisfied yourself.

A failure stops here: show it; the human decides re-run, repair (→ Gate 5), or abandon.

## Gate 8 — REGRESSION

Existing cases only, fail-fast, one run each: every `smoke` case first, then cases whose tags match
the areas the diff touched (e.g. edited Gate 0 prose → `gate-0`), skipping ones run at Gate 7.
List tags with `grep -h '^tags:' sdlc-lite-plugin/evals/*/prompt.md`. A failing `flaky` case is
labelled `flaky`. Code changed → pytest again. Never the full suite (`/regression`).

## Gate 9 — REVIEW-GUIDE

`git status` + `git diff --stat main...`, then the items Gate 9 lists in `gates.md`.

## Gate 10 — HUMAN REVIEW

**STOP ④** — ask for approval of the implementation, plus the T3 attestation if declared. A change
request → the owning gate (prose → 5, a case → 3 and back through STOP ③), then forward again.

## Gate 11 — COMMIT

Confirm HEAD is `<NN>-<slug>`, not `main`. Commit per logical unit, message
`<type>(<area>): <summary> (#NN)`. At close: `git rm <NN>-plan.md` if one exists; tick the parent
tracking plan's box if there is one. Ask **"open a PR, or merge to `main`?"** and do that. Then
`gh issue close NN` with a one-line comment naming the merge or PR. Do not edit
`dev-docs/release-plan.md` — roadmap ordering is the human's call.

## Running a case

T1 runs in the dev container, not on the host (ladder §5). From the repo root on the Mac:

```bash
devcontainer exec --workspace-folder . bash -c \
  "set -a; source /workspaces/sdlc-lite/.env; set +a; cd /workspaces/sdlc-lite && \
   claude plugin eval sdlc-lite-plugin --ablation none --case <name> --runs 1 \
   --max-cost-usd <cap> --scaffold --no-publish --trust-plugin --allow-tools Bash Write Edit"
```

`--allow-tools` stays last (variadic). The container isn't up → tell the human to run
`devcontainer up --workspace-folder .` and wait. Report each case with its results dir.
