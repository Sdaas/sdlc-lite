# The repo-local SDLC spine

Shared by this repo's own skills — `/issue`, `/feature` (#52), `/fix` (#53). A skill **executes**
this spine; it never restates it. Change a gate here, once. How to execute each gate:
[`runbook.md`](runbook.md).

**Scope:** work on *this* repo — the plugin's prose (`SKILL.md`, `agents/*.md`, `references/*`,
`hooks.json`) and its small code surface (`guard.py`, `policy.py`, `agentdefs.py`, `analyzer/`).
Not the `sdlc-lite` plugin's own workflow, which serves a user's Python repo.

**Same SDLC, different *how*.** The plugin designs, tests and implements **code**; this spine
designs, evaluates and implements **prose**. Gate names match the plugin's where the concept is
the same (see *Mapping to `implement-feature`*); the contents do not, and the two will not
converge. Why: [`dev-docs/verification-ladder.md`](../../dev-docs/verification-ladder.md) §6.

**Tiers:** T1 / T2 / T3, what each proves, and the change → minimum-tier table are defined in
the ladder. This file only names them.

---

## Modes

- **[C]** — the interactive session (the conductor).
- **[I]** — an ad-hoc subagent with a fresh context and an inline `model:`. Its brief carries
  only what the gate needs; never your intent, never the answer you expect.
- **↔H** — the gate talks to the human before it can finish.
- **STOP** — the gate ends by waiting for an explicit human approval. Silence is not approval.
- **halt** — the run stops on a failure or an unmet precondition, shows what happened, and the
  human rules (re-run, repair, re-scope, abandon). Not an approval STOP: there are still four.

---

## Gates 0–11

| Gate | Mode | What | STOP |
|---|---|---|---|
| **0 CLASSIFY** | [C] | Resolve `#NN` with `gh issue view NN`. Missing, or not conforming to `dev-docs/issue-template.md` → hand off to `/issue` and exit. Classify the surface: prose · hook · code (`guard.py`/`policy.py`/`agentdefs.py`/`analyzer/`) · docs-only. Docs-only or shell-only → **decline and exit** (not gated; ladder §3 names the one exception). Take the minimum tier from the ladder. New branch: a dirty working tree → **halt**. The branch exists → resume on it (its uncommitted work is the run's own) from the plan file's tracker; no plan file → **halt**: the human names the gate to resume at; no past approval is inferred. Create branch `<NN>-<slug>` from `main`, or from a base the human names — never work on `main`. Decide whether `<NN>-plan.md` is warranted (root `CLAUDE.md` → Planning docs). | |
| **1 INTERVIEW** | [C]↔H | Grill to scope clarity. **Anchor the smallest viable scope first**: propose a one-paragraph minimal version and an explicit out-of-scope list; every extra is a scope decision the human opts into. Skip the grilling (not the STOP) when the issue's acceptance criteria are already testable. After approval, post the settled scope as one comment on the issue. | **① scope** (+ tier, branch) |
| **2 DESIGN** | [C]↔H | Which files change and how; the behavior delta a cold agent should show; the eval cases that will prove it, **in run order**, each with its prompt and graders; the failing `pytest` for a code change; what T1 cannot prove and so needs T3: the T3 fixture (by slug) and the evidence the dry run must show, which that fixture must actually exercise; the `--max-cost-usd` cap (see Eval budget). After approval, write `<NN>-plan.md` if Gate 0 said so. | **② design** |
| **3 WRITE-EVALS** | [C] | Write the approved eval cases (and any `pytest`) **before touching any prose**. Each case's `tags:` name the areas it covers, and it gets an `evals/README.md` row. Their frontmatter must parse. Nothing that costs money is run yet. | |
| **4 EVAL-REVIEW** | [I] `opus` | Cold review of the new cases against the *Eval-review checks* below; no new eval case → the new `pytest`, against checks 2–3. Findings → back to Gate 3, then re-review. Present the cases and the verdict. | **③ tests** |
| **5 IMPLEMENT** | [C] / [I] | **First, confirm red:** run every new case once (`/fix`: the reproducing case only if its fingerprint changed since its last red run) — each must fail; a case that **passes** does not test the change → a `→ WRITE-EVALS` finding; run the new `pytest` red. Then edit the Markdown or code — [C] by default; [I] `sonnet` when the diff spans more than 3 files or touches `guard.py` / `policy.py` / `analyzer/`. Exit when the **fast checks** pass (repairs within the loop bound). | |
| **6 CODE-REVIEW** | [I] `opus` | Cold review of the whole change since the base — committed, uncommitted and new files — against the six review dimensions, **before any further eval spend**. Findings are typed (see *Routing findings*). | |
| **7 VERIFY** | [C]↔H | Run the declared tier: T1 on this change's new cases, fail-fast; T2; T3: the conductor starts and watches the dry run, the human drives the session and attests. A failure **halts** the gate and is shown (except a `flaky` case — see Eval budget). | |
| **8 REGRESSION** | [C] | Existing eval cases, fail-fast: `smoke`-tagged first, then those tagged with the areas the diff touched. Plus `pytest` if code changed. Never the full suite. | |
| **9 REVIEW-GUIDE** | [C] | Changed files in review order, one line each; the Gate 7/8 evidence (per case, pass/fail, "1 run", results dir; `flaky` failures and diagnostic re-runs marked as such); the Gate 4 and 6 findings and how each was resolved; the proposed commit split (with a plan file: its own `git rm` commit last). | |
| **10 HUMAN REVIEW** | [C]↔H | The human reviews the implementation with the evidence in hand. T3, if declared, is attested here. Change requests route to the gate that owns them, then the run re-converges forward. | **④ implementation** |
| **11 COMMIT** | [C]↔H | Re-check HEAD is not `main`. Commit the Gate 9 split, referencing `#NN`. At close, `git rm <NN>-plan.md` (it went in with the first commit) and `rm` any root `*.md.tmp` review files (gitignored; root `CLAUDE.md` → Temp files), ask the human **"open a PR, or merge to `main`?"** (merge = `--no-ff` into `main`; push only when asked), then close the issue. | |

A skill may **add** gates between these (e.g. `/fix`'s REPRODUCE, DEPOSIT) or **omit** a range
(`/issue` runs none of them). It never renumbers or rewords a spine gate.

---

## Gates added by `/fix`

A bug fix must leave a case behind that proves it stays fixed. Added gates take a letter suffix, so
nothing is renumbered, and add no STOP.

| Gate | Mode | What | STOP |
|---|---|---|---|
| **1b REPRODUCE** | [C]↔H | After STOP ①, before DESIGN. Reproduce the bug at the **cheapest tier that shows it** — T2 `pytest`, else T1 eval case, else T3 (a dry run the human attests). Below T3, the reproduction **is** the reproducing case: written now, shown red. The route is approved at STOP ①; a costlier one never runs unapproved. Record the tier, the case (or T3 recipe), the red evidence and the case's fingerprint (T1/T2 only — a T3 recipe has none); they open STOP ②. Not reproduced → **halt**; no design for an unreproduced bug. | |
| **8b DEPOSIT** | [C] | After REGRESSION. The reproducing case — red before the fix, green at Gate 7 — goes in the fix's commit and stays: T1 tagged so Gate 8 replays it, T2 collected by the fast checks. T3-only → no fingerprint and no stashed re-run: the human's attestation (red at 1b, green at Gate 7) is the check; the recipe is posted on the issue and a follow-up issue asks for a cheaper case. | |

**The reproduction tier is a floor.** Gate 7 always runs the tier the bug was reproduced at, on top
of the ladder's minimum; nothing claims "fixed" at a weaker tier than that. A reproducing case
whose fingerprint changed after its last red run is re-run red before it counts (Gate 5, or 8b with the fix stashed).

**Two carve-outs, both approved at STOP ①:** the reproducing case is written before STOP ②, and a
T1 repro run may spend eval money before STOP ③, within its own cap.

---

## The four STOPs

The human approves **scope, design, tests and implementation** — nothing else. More STOPs than
this produce rubber-stamping, which is worse than no gate.

1. **Scope** (Gate 1) — what is in and out, the tier the change owes, the branch; for `/fix`, how
   the bug will be reproduced and any T1 repro cap.
2. **Design** (Gate 2) — the plan, the eval cases in run order, the cost cap. Nothing is written
   before it (except `/fix`'s reproducing case) — `<NN>-plan.md` included: it records the approved
   design.
3. **Tests** (Gate 4) — the reviewed eval cases (none → the reviewed `pytest`). No eval money is spent before it (except
   `/fix`'s capped T1 repro run). A case changed
   after this STOP comes back for re-approval (changed cases only).
4. **Implementation** (Gate 10) — the diff, with the eval evidence and any T3 attestation.
   **Nothing is committed before it.** Its approval is the pre-commit approval root `CLAUDE.md`
   requires, for exactly the commit split shown at Gate 9; any other commit needs a fresh approval.

Every STOP summary is short: what was decided or produced, where the real files are, and the one
question the human must answer. Point at the files; never ask approval for something not shown.

---

## Fast checks

Cheap, deterministic, run at the end of Gate 5 and after every repair — before any eval spend.

- `python3 -m pytest sdlc-lite-plugin -q`
- `./release-verify.sh --links-only`
- Every new or edited `sdlc-lite-plugin/evals/*/prompt.md` (its frontmatter) and `case.yaml` parses
  as YAML:
  `python3 -c 'import sys,yaml; [yaml.safe_load(open(f).read().split("---")[1] if f.endswith(".md") else open(f)) for f in sys.argv[1:]]' <files>`

`verify-entry-points.py` is **not** a fast check — it drives real Claude sessions.

---

## Eval-review checks (Gate 4)

The reviewer is given the issue, the new cases, and the prose they target, and may read any other
repo file — never the conductor's reasoning. Per case, one line each:

1. **No leak** — does the prompt read as a user would type it, or does it hint at the answer?
2. **Behavior, not proxy** — does each grader assert the observable behavior the issue's
   Expected / acceptance criteria name?
3. **Wrong edit still passes?** — name one plausible wrong or missing edit; does a grader fail it?
4. **Cost** — free graders unless an `llm` grader is justified; `max_turns` no larger than needed.

---

## The six review dimensions (Gate 6)

Every review states each dimension. `N/A — <why>` is allowed; silently dropping one is not. The
reviewer may read any repo file (dimensions 2 and 6 need them) — never the conductor's reasoning.

1. **Unambiguity** — would a cold agent read this exactly one way?
2. **Consistency** — does it contradict another gate, an `agents/*.md`, the guard, or the docs?
3. **Enforcement parity** — does a new prose rule the guard should enforce have its `guard.py`
   denial and a T2 test?
4. **Context cost** — does the edit earn the tokens it adds to an always-loaded file?
5. **Isolation integrity** — does it leak a withheld artifact into a gate's inbox?
6. **Doc parity** — do `README.md`, `dev-docs/architecture.md`, `developer-guide.md`, or an ADR need to change with it?

## Routing findings

Each finding — Gate 6's, a case passing at confirm-red, a Gate 10 change request — names its
repair target:

- **→ IMPLEMENT** — the prose or code is wrong. Fix it (Gate 5), re-run the fast checks, re-review.
- **→ WRITE-EVALS** — a case is weak, leaky or missing. Fix it (Gate 3), re-run EVAL-REVIEW, and
  bring the changed cases back to STOP ③. A case written or edited after the prose edit is then
  confirmed red with the change stashed (as 8b does) before it counts.
- **→ DESIGN** — the approved design is wrong or incomplete. Revise it (Gate 2), back to STOP ②,
  then forward from the first gate the revision touches.

---

## Eval budget

Every T1 run spends real tokens — roughly $0.20–1.00 per case per run. Inside a change, spend the
least that still answers the question.

- **Order.** This change's new cases first, in the order Gate 2 approved (`/fix`: the reproducing
  case first); then `smoke`-tagged
  cases; then cases tagged with the touched areas. Never the full suite inside a change.
- **One case per invocation.** One `claude plugin eval` invocation per case (`--case <name> --runs 1`).
- **Fail fast at Gates 7 and 8 only.** There, stop at the first failure; the tool has no fail-fast
  flag, so the ordering is the mechanism. At 1b, 5 and 8b red is the expected result and every case
  runs. At 5 and 8b a case that **passes** is a `→ WRITE-EVALS` finding; at 1b it means the bug was
  not reproduced → **halt**.
- **A failure at Gate 7 or 8 halts the gate** (except a `flaky` case, below). Before the human rules, re-run that one case once with
  `--keep-temp`, under the STOP ② cap, so the sandbox survives for diagnosis. That re-run never
  turns the failure into a pass: a pass is reported as "failed, then passed on the diagnostic
  re-run". The human then decides re-run, repair or abandon. No other re-run on your own.
- **A `flaky` case does not stop the gate.** An existing case tagged `flaky` that fails at Gate 7
  or 8 gets no diagnostic re-run; it is noted in the Gate 9 evidence as a `flaky` failure and the
  gate goes on. A case this change adds may not carry `flaky`.
- **One run is one run.** Evidence says "1 run" (a diagnostic re-run is listed separately); at
  STOP ④ the human may ask for more.
- **Hard cap.** Every eval command at Gates 5, 7, 8 and 8b carries the `--max-cost-usd` cap
  approved at STOP ②; at 1b, the repro cap approved at STOP ①. The cap is per invocation
  (one case, one run), not a total for the change. Hitting it halts the gate. There is no default:
  the design states it.
- **Not here:** the 3-runs-per-case pass over the whole suite is `/regression` (#64; before a
  release, or twice a week); the full release gate is `release-verify.sh` (ladder §8).

---

## Mapping to `implement-feature`

Same concept, same name; the *how* differs because the product here is prose.

| This spine | `implement-feature` | What differs here |
|---|---|---|
| 0 CLASSIFY | 0 CLASSIFY + PREFLIGHT | No toolchain preflight or run lock; declines docs/shell-only |
| 1 INTERVIEW | 1 INTERVIEW | Settled scope goes to the GitHub issue, not a requirements file |
| 1b REPRODUCE (`/fix`) | — | `implement-feature` has no bug path |
| 2 DESIGN | 2 DESIGN / SPEC | No interface/internal split; eval cases replace the test plan |
| 3 WRITE-EVALS | 3 WRITE-TESTS | Eval cases, written in-session; not algorithm-blind |
| 4 EVAL-REVIEW | 4 TEST-REVIEW | Adds the leak check; human STOP ③ |
| 5 IMPLEMENT | 5 IMPLEMENT | Opens with the confirm-red run (red is undefined before an eval runs) |
| 6 CODE-REVIEW | 7 CODE-REVIEW | Runs **before** VERIFY — here VERIFY is the expensive step |
| 7 VERIFY | 6 VERIFY | Eval runs + T3 attestation instead of driving code un-mocked |
| 8 REGRESSION | — | Replays the tagged eval cases a prose change could break |
| 8b DEPOSIT (`/fix`) | — | A fixed bug leaves its reproducing case behind |
| 9 REVIEW-GUIDE | 8 REVIEW-GUIDE | — |
| 10 HUMAN REVIEW | 9 HUMAN REVIEW | — |
| 11 COMMIT | 10 COMMIT | — |
| — | 11 REPORT | No analyzer: one interactive session, no audit trail |

---

## Rules every skill inherits

- **Never commit before STOP ④; never stage before Gate 11** (the Gate 6/9 diff's intent-to-add
  entries, reset at once, are the one exception).
- **GitHub is the source of truth** for what an issue asks; no conforming issue → `/issue`.
- **Reviews are isolated and run on `opus`.** Repo-local skills cannot pin dated models: both
  review subagents are spawned with `model: opus`, an isolated implementer with `model: sonnet`.
  An in-session ([C]) implementation runs on the session's model, so there the review's edge is
  its fresh context, not a higher model tier.
- **Bound every loop.** A review → fix → re-review loop is the first review plus at most two
  re-reviews; findings left after the second re-review → **halt**. Fast-check repairs get the same
  bound: still red after two repairs → **halt**.
- **Never mark T3 satisfied** without the human's attestation.
