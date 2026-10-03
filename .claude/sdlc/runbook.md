# The repo-local runbook — how to execute the spine

Executed by `/feature` and `/fix`. [`gates.md`](gates.md) defines **what** each gate is — the four
STOPs, the fast checks, both review checklists, finding routing, the eval budget and the inherited
rules. This file says only **how** to execute each gate here. Where the two seem to disagree,
`gates.md` wins. The skill that sent you here adds only its **Entry** check.

Announce each gate as you enter it (`Gate N — NAME`), so the human always knows where the run is.

## Hard rules

- **Never work on `main`.** Branch at Gate 0, before any edit.
- **Stop at every STOP.** End the turn and wait; never chain two STOPs in one turn.
- **Nothing is committed before STOP ④, nor staged before Gate 11** (except the intent-to-add
  entries of *Diffing the change*). Silence is not approval.
- **No eval money before STOP ③** — except `/fix`'s T1 repro run, within the cap approved at STOP ①.
- **One issue per run.** Scope creep found mid-run → offer `/issue` for it, don't absorb it.

## Gate 0 — CLASSIFY

1. `$ARGUMENTS` has no `#NN` → ask for one, or offer `/issue` to file it.
2. `gh issue view NN --json number,title,state,labels,milestone,body,comments`. Not found, closed,
   or missing the required sections of [`dev-docs/issue-template.md`](../../dev-docs/issue-template.md)
   → say what is missing, tell the human to run `/issue`, and **exit**. Then apply the skill's
   **Entry** check.
3. Classify the surface from the acceptance criteria. **Docs-only** (`README.md`, `dev-docs/**`)
   or **shell-only** (`*.sh`) → decline in one line and exit; those are not gated (ladder §3 has the
   one exception — a doc path the shipped `SKILL.md` prints).
4. Take the minimum tier from [`dev-docs/verification-ladder.md`](../../dev-docs/verification-ladder.md)
   §3 (union across rows).
5. **New branch:** `git status` must be clean; dirty → show it and **halt** (never stash, commit
   or discard on your own). Create `<NN>-<slug>` from the **base** — `main` unless the human names
   another (e.g. an unmerged branch the work builds on). Gates 6 and 9 diff against that base.
   **The branch already exists** → switch to it; its uncommitted work is the run's own (nothing is
   committed before Gate 11). Resume from `<NN>-plan.md`'s tracker; no plan file → **halt** and ask
   which gate to resume at, and from which base. Never infer a past approval.
6. Plan file: warranted only if the work is multi-session, multi-phase or structurally complex.

## Gate 1 — INTERVIEW

Work the scope as a design tree, in rounds: ask the whole frontier at once, each question numbered
with your recommended answer, defaulting to the smaller option. Look facts up yourself; put only
decisions to the human. Open with the minimal version and the out-of-scope list. Issue ACs already
testable → say so and go straight to the STOP.

**STOP ①** — show the settled scope (in / out), the surface, the tier with its ladder §3 row, the
branch, plan file yes/no; for `/fix`, the planned reproduction route (T2 · T1 · T3 — read the files
the Steps to Reproduce name to choose it) and, if T1, its `--max-cost-usd` cap. A T3 route that cites
an existing dry run asks for the human's attestation here. On approval, post the scope as one issue
comment: `gh issue comment NN --body-file <file>`.

## Gate 1b — REPRODUCE (`/fix` only)

Run the route approved at STOP ①:

- **T2** — the defect is visible in files alone (e.g. two files that disagree): write a `pytest`
  under `sdlc-lite-plugin/` that asserts the Expected; run `python3 -m pytest <file> -q`, show it red.
- **T1** — it needs a model to show it: write the eval case complete (as at Gate 3: its `tags:`
  name the areas it covers, its `evals/README.md` row exists), run it once (see *Running a case*)
  with the repro cap, show it red.
- **T3** — nothing cheaper shows it: the STOP ① attestation stands, or run the dry run per Gate 7's
  T3 procedure.

The route does not show the bug → **halt** (no diagnostic re-run): show
what was tried; the human approves another route (and its cap), narrows the issue, or closes it as
not reproducible. Never move to a costlier route unapproved; never design a fix for an unreproduced
bug. Record the tier, the case path (or the recipe), the red output, and — T1/T2 only — the
fingerprint `git hash-object <files>` over the case **and every fixture, conftest or helper it
depends on** (a T3 recipe has none);
they open the Gate 2 design.

## Gate 2 — DESIGN

Present the items Gate 2 lists in `gates.md`, in that order. A case's prompt is what a user would
type — never the answer you expect (ladder §6, "simulating"). T3 declared → name the fixture (its
`SLUG`), each piece of T3 evidence, and the fixture step that exercises it (e.g. a concurrency rule needs a fixture with
shared state; a pure-function fixture never opens it). No fixture exercises it → pick another
fixture, or drop that evidence and say what is left unproven.

**STOP ②** — the design. On approval, write `<NN>-plan.md` if Gate 0 said so; it holds the
approved design and a progress tracker, updated at each gate exit.

## Gate 3 — WRITE-EVALS

Write the cases under `sdlc-lite-plugin/evals/<case>/` (case rules: `sdlc-lite-plugin/evals/README.md`; flags: `claude plugin eval --help`);
give each case `tags:` naming the areas it covers (Gate 8 selects by them) and add a row to the case
table in `sdlc-lite-plugin/evals/README.md`. Code change: write the `pytest`. Check the frontmatter
parses (the YAML fast check). Run nothing that costs money. `/fix`: the reproducing case exists
from 1b; write only the other approved cases.

## Gate 4 — EVAL-REVIEW

Spawn an ad-hoc subagent with **`model: opus`**. Brief: the issue body, the new case directories,
the prose files they target, and the four eval-review checks copied from `gates.md`; it may read any
other repo file. No new eval case → brief it the new `pytest` and checks 2–3 only. It returns one
line per check per case. Fix findings (Gate 3), re-review — the loop bound is in `gates.md` Rules.

**STOP ③** — the cases (paths + one line each; none → the `pytest`) and the review verdict.

## Gate 5 — IMPLEMENT

1. **Confirm red** — every new case once, in design order (see *Running a case*), without
   stopping at a red one; new `pytest` red.
   `/fix`: re-run the reproducing case only if its fingerprint changed since its last red run; either way record
   the fingerprint of its last red run.
   Record per case: fails · **passes**. A pass is a
   `→ WRITE-EVALS` finding: fix the case (Gate 3), re-run EVAL-REVIEW, bring the changed case back
   to STOP ③, then confirm it red here before editing any prose.
2. Edit. In this session by default; spawn an ad-hoc subagent with **`model: sonnet`** when the
   diff spans more than 3 files or touches `guard.py`, `policy.py` or `analyzer/` — its brief is the
   approved design and the red cases, nothing else. Agent read/write change → both the agent's
   prose inbox and `policy.py` (root `CLAUDE.md`).
3. Run the fast checks; repair and re-run, at most twice, then **halt**.

A case written or edited after step 2 (a `→ WRITE-EVALS` finding, or a Gate 10 change request) is
confirmed red with the change stashed: `git stash push -u -- <changed prose/code files>`, run the
case, `git stash pop`. Green → it is not testing the change; back to Gate 3.

## Gate 6 — CODE-REVIEW

Spawn an ad-hoc subagent with **`model: opus`**. Brief: the output of *Diffing the change*, the
issue body, and the six dimensions and routing rules copied from `gates.md`; it may read any other
repo file — **not** your reasoning or the answer you expect. It returns one line per dimension (`OK` · finding
with its `→ IMPLEMENT` / `→ WRITE-EVALS` / `→ DESIGN` target · `N/A — why`); a missing dimension → send it back
once. Route findings per `gates.md`; fast checks after every fix; re-review within the loop bound.

## Gate 7 — VERIFY

- **T1** — this change's new cases, in design order, fail-fast, one run each.
- **T2** — `python3 -m pytest sdlc-lite-plugin -q` (host).
- **T3** — follow `dev-docs/t3-runs.md` §1: `make t3-start SLUG=<fixture slug from Gate 2>`, check `make t3-peek`, run
  `make t3-watch` under Monitor, give the human `make t3-attach`, and report each event in chat
  (⏸ at every WAITING, with the ask). Read handoff files yourself via `devcontainer exec`. Ask the
  human only for what you cannot or must not do — typing into the session, approvals — never to check
  something you can read, and never `tmux send-keys`. At `ENDED`: tell them to detach, `make t3-stop`,
  collect the attestation at STOP ④; never mark it satisfied yourself.

`/fix`: always include the tier the bug was reproduced at, and run the reproducing case first
(T2: `python3 -m pytest <file> -q`, then the suite).

A failure **halts** here — see *When a case fails*; the human decides re-run, repair (→ Gate 5), or
abandon.

## Gate 8 — REGRESSION

Existing cases only, fail-fast, one run each: every `smoke` case first, then cases whose tags match
the areas the diff touched (e.g. edited Gate 0 prose → `gate-0`), skipping ones run at Gate 7.
List tags with `grep -h '^tags:' sdlc-lite-plugin/evals/*/prompt.md`. A failure **halts** here, as at
Gate 7 (see *When a case fails*). Code changed → pytest again. Never the full suite (`/regression`).

## Gate 8b — DEPOSIT (`/fix` only)

Checks only — 8b edits nothing. A failed check is a `→ WRITE-EVALS` finding (Gate 3, then back
through STOP ③ and forward again).

1. T1/T2: recompute the fingerprint (same file set as 1b) and compare with the last red run's (1b or
   Gate 5). Changed → stash the fix (`git stash push -u -- <fixed files>`), re-run the case as at 1b
   (T1 with the STOP ② cap), then `git stash pop`. It must be red; green means the case no longer
   reproduces the bug.
2. Confirm it was green at Gate 7. T3: no fingerprint and no stashed re-run — the human's
   attestation (red at 1b, green at Gate 7) is the check, collected at STOP ④.
3. T1 → its `tags:` name the areas it covers and its `evals/README.md` row exists. T2 → it sits
   where `python3 -m pytest sdlc-lite-plugin -q` collects it.
4. T3-only → post the recipe on the issue (`gh issue comment NN --body-file <file>`) and ask the
   human to file a follow-up with `/issue` for a cheaper case.

Emit one line for Gate 9: `Deposit: <path or recipe> — <tier>, last red <1b|5|8b>, green at 7`.

## Gate 9 — REVIEW-GUIDE

`git status` + the `--stat` form of *Diffing the change*, then the items Gate 9 lists in `gates.md`; `/fix` adds
the Deposit line and puts the reproducing case in the same commit as the fix.

## Gate 10 — HUMAN REVIEW

**STOP ④** — ask for approval of the implementation, plus the T3 attestation if declared. A change
request → the owning gate (prose → 5, a case → 3 and back through STOP ③, the design → 2 and back
through STOP ②), then forward again.

## Gate 11 — COMMIT

Confirm HEAD is `<NN>-<slug>`, not `main`. Commit the split approved at STOP ④ — one logical unit
per commit, message `<type>(<area>): <summary> (#NN)`; a commit outside that split needs a fresh
approval. `<NN>-plan.md`, if any, goes in the first commit. At close: `git rm <NN>-plan.md` in its
own commit; if the issue has a parent issue, tick its box in the parent's checklist (never
`dev-docs/release-plan.md`). Ask **"open a PR, or merge to `main`?"**:

- **Merge** — `git checkout main && git merge --no-ff <NN>-<slug> -m "Merge branch '<NN>-<slug>' — <summary> (#NN)"`.
- **PR** — `git push -u origin <NN>-<slug>`, then `gh pr create`.

Push `main` only when the human asks. Then
`gh issue close NN` with a one-line comment naming the merge or PR. Do not edit
`dev-docs/release-plan.md` — roadmap ordering is the human's call.

## Diffing the change (Gates 6, 9)

Nothing is committed before Gate 11, so `<base>...HEAD` is empty and a plain `git diff` misses new
files. Use:

```bash
git add -A -N && git diff "$(git merge-base <base> HEAD)"; git reset -q    # Gate 9: add --stat
```

`-N` (intent-to-add) makes untracked, non-ignored files show in the diff; `git reset -q` drops
those entries at once — left in the index they break 8b's `git stash push -u`. Safe because nothing
else is staged before Gate 11. The merge-base keeps commits that landed on the base mid-run out of
the diff.

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

## When a case fails (Gates 7, 8)

- **An existing case tagged `flaky`** → no re-run, no halt: note it for Gate 9 as `<case> — FAIL (flaky), 1 run,
  <results dir>` and go on to the next case.
- **Not `flaky`** → re-run that one case once, adding `--keep-temp` (before `--allow-tools`), with
  the cap approved at STOP ②. Report both runs and the kept sandbox path; a pass on the re-run is
  reported as "failed, then passed on the diagnostic re-run" — still a failure. Then stop for the
  human's ruling.
