# The repo-local SDLC spine

Shared by this repo's own skills — `/issue`, `/feature` (#52), `/fix` (#53). A skill **executes**
this spine; it never restates it. Change a gate here, once.

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

---

## Gates 0–11

| Gate | Mode | What | STOP |
|---|---|---|---|
| **0 CLASSIFY** | [C] | Resolve `#NN` with `gh issue view NN`. Missing, or not conforming to `dev-docs/issue-template.md` → hand off to `/issue` and exit. Classify the surface: prose · hook · code (`guard.py`/`policy.py`/`agentdefs.py`/`analyzer/`) · docs-only. Docs-only or shell-only → **decline and exit** (not gated). Take the minimum tier from the ladder. Create branch `<NN>-<slug>` — never work on `main`. Decide whether `<NN>-plan.md` is warranted (root `CLAUDE.md` → Planning docs). | |
| **1 INTERVIEW** | [C]↔H | Grill to scope clarity. **Anchor the smallest viable scope first**: propose a one-paragraph minimal version and an explicit out-of-scope list; every extra is a scope decision the human opts into. Skip the grilling (not the STOP) when the issue's acceptance criteria are already testable. After approval, post the settled scope as one comment on the issue. | **① scope** (+ tier, branch) |
| **2 DESIGN** | [C]↔H | Which files change and how; the behavior delta a cold agent should show; the eval cases that will prove it, **in run order**, each with its prompt and graders; the failing `pytest` for a code change; what T1 cannot prove and so needs T3; the `--max-cost-usd` cap (see Eval budget). Write `<NN>-plan.md` if Gate 0 said so. | **② design** |
| **3 WRITE-EVALS** | [C] | Write the approved eval cases (and any `pytest`) **before touching any prose**. Their frontmatter must parse. Nothing is run yet. | |
| **4 EVAL-REVIEW** | [I] `opus` | Cold review of the new cases against the *Eval-review checks* below. Findings → back to Gate 3, then re-review. Present the cases and the verdict. | **③ tests** |
| **5 IMPLEMENT** | [C] / [I] | **First, confirm red:** run each new case once — it must fail, or pass for the wrong reason (a case that **passes** is shown to the human: it does not test the change); run the new `pytest` red. Then edit the Markdown or code — [C] by default; [I] `sonnet` when the diff spans more than 3 files or touches `guard.py` / `policy.py` / `analyzer/`. Exit when the **fast checks** pass. | |
| **6 CODE-REVIEW** | [I] `opus` | Cold review of the whole diff against the six review dimensions, **before any further eval spend**. Findings are typed (see *Routing findings*). | |
| **7 VERIFY** | [C] | Run the declared tier: T1 on this change's new cases, fail-fast; T2; T3 is handed to the human, who runs it and attests. A failure stops the gate and is shown. | |
| **8 REGRESSION** | [C] | Existing eval cases, fail-fast: `smoke`-tagged first, then those tagged with the areas the diff touched. Plus `pytest` if code changed. Never the full suite. | |
| **9 REVIEW-GUIDE** | [C] | Changed files in review order, one line each; the Gate 7/8 evidence (per case, pass/fail, "1 run", results dir); the Gate 4 and 6 findings and how each was resolved; the proposed commit split. | |
| **10 HUMAN REVIEW** | [C]↔H | The human reviews the implementation with the evidence in hand. T3, if declared, is attested here. Change requests route to the gate that owns them, then the run re-converges forward. | **④ implementation** |
| **11 COMMIT** | [C]↔H | Re-check HEAD is not `main`. Commit per logical unit, referencing `#NN`. At close, `git rm <NN>-plan.md`, ask the human **"open a PR, or merge to `main`?"**, then close the issue. | |

A skill may **add** gates between these (e.g. `/fix`'s REPRODUCE, DEPOSIT) or **omit** a range
(`/issue` runs none of them). It never renumbers or rewords a spine gate.

---

## The four STOPs

The human approves **scope, design, tests and implementation** — nothing else. More STOPs than
this produce rubber-stamping, which is worse than no gate.

1. **Scope** (Gate 1) — what is in and out, the tier the change owes, the branch.
2. **Design** (Gate 2) — the plan, the eval cases in run order, the cost cap. Nothing is written
   before it.
3. **Tests** (Gate 4) — the reviewed eval cases. No eval money is spent before it. A case changed
   after this STOP comes back for re-approval (changed cases only).
4. **Implementation** (Gate 10) — the diff, with the eval evidence and any T3 attestation.
   **Nothing is committed before it.**

Every STOP summary is short: what was decided or produced, where the real files are, and the one
question the human must answer. Point at the files; never ask approval for something not shown.

---

## Fast checks

Cheap, deterministic, run at the end of Gate 5 and after every repair — before any eval spend.

- `python3 -m pytest sdlc-lite-plugin -q`
- `./release-verify.sh --links-only`
- Every new or edited `sdlc-lite-plugin/evals/*/prompt.md` and `case.yaml` parses as YAML.

`verify-entry-points.py` is **not** a fast check — it drives real Claude sessions.

---

## Eval-review checks (Gate 4)

The reviewer sees the issue, the new cases, and the prose they target — not the conductor's
reasoning. Per case, one line each:

1. **No leak** — does the prompt read as a user would type it, or does it hint at the answer?
2. **Behavior, not proxy** — does each grader assert the observable behavior the design names?
3. **Wrong edit still passes?** — name one plausible wrong or missing edit; does a grader fail it?
4. **Cost** — free graders unless an `llm` grader is justified; `max_turns` no larger than needed.

---

## The six review dimensions (Gate 6)

Every review states each dimension. `N/A — <why>` is allowed; silently dropping one is not.

1. **Unambiguity** — would a cold agent read this exactly one way?
2. **Consistency** — does it contradict another gate, an `agents/*.md`, the guard, or the docs?
3. **Enforcement parity** — does a new prose rule the guard should enforce have its `guard.py`
   denial and a T2 test?
4. **Context cost** — does the edit earn the tokens it adds to an always-loaded file?
5. **Isolation integrity** — does it leak a withheld artifact into a gate's inbox?
6. **Doc parity** — do `README.md`, `dev-docs/architecture.md`, `developer-guide.md`, or an ADR need to change with it?

## Routing findings

Each Gate 6 finding names its repair target:

- **→ IMPLEMENT** — the prose or code is wrong. Fix it (Gate 5), re-run the fast checks, re-review.
- **→ WRITE-EVALS** — a case is weak, leaky or missing. Fix it (Gate 3), re-run EVAL-REVIEW, and
  bring the changed cases back to STOP ③.

---

## Eval budget

Every T1 run spends real tokens — roughly $0.20–1.00 per case per run. Inside a change, spend the
least that still answers the question.

- **Order.** This change's new cases first, in the order Gate 2 approved; then `smoke`-tagged
  cases; then cases tagged with the touched areas. Never the full suite inside a change.
- **Fail fast.** One `claude plugin eval` invocation per case (`--case <name> --runs 1`); stop at
  the first failure. The tool has no fail-fast flag, so the ordering is the mechanism.
- **A failure stops the gate.** Show it to the human, who decides whether to re-run. Never re-run
  on your own. A case tagged `flaky` is labelled as such when it fails.
- **One run is one run.** Evidence says "1 run"; at STOP ④ the human may ask for more.
- **Hard cap.** Every eval command at Gates 5, 7 and 8 carries the `--max-cost-usd` cap approved
  at STOP ②. Hitting it stops the gate. There is no default: the design states it.
- **Not here:** the 3-runs-per-case pass over the whole suite is `/regression` (#64; before a
  release, or twice a week); the full release gate is `release-verify.sh` (ladder §8).

---

## Mapping to `implement-feature`

Same concept, same name; the *how* differs because the product here is prose.

| This spine | `implement-feature` | What differs here |
|---|---|---|
| 0 CLASSIFY | 0 CLASSIFY + PREFLIGHT | No toolchain preflight or run lock; declines docs/shell-only |
| 1 INTERVIEW | 1 INTERVIEW | Settled scope goes to the GitHub issue, not a requirements file |
| 2 DESIGN | 2 DESIGN / SPEC | No interface/internal split; eval cases replace the test plan |
| 3 WRITE-EVALS | 3 WRITE-TESTS | Eval cases, written in-session; not algorithm-blind |
| 4 EVAL-REVIEW | 4 TEST-REVIEW | Adds the leak check; human STOP ③ |
| 5 IMPLEMENT | 5 IMPLEMENT | Opens with the confirm-red run (red is undefined before an eval runs) |
| 6 CODE-REVIEW | 7 CODE-REVIEW | Runs **before** VERIFY — here VERIFY is the expensive step |
| 7 VERIFY | 6 VERIFY | Eval runs + T3 attestation instead of driving code un-mocked |
| 8 REGRESSION | — | Prose leaves no regression tests behind; replay tagged cases |
| 9 REVIEW-GUIDE | 8 REVIEW-GUIDE | — |
| 10 HUMAN REVIEW | 9 HUMAN REVIEW | — |
| 11 COMMIT | 10 COMMIT | — |
| — | 11 REPORT | No analyzer: one interactive session, no audit trail |

---

## Rules every skill inherits

- **Never commit before STOP ④.**
- **GitHub is the source of truth** for what an issue asks; no conforming issue → `/issue`.
- **Review runs on a higher model than implementation.** Repo-local skills cannot pin dated
  models; both review subagents are spawned with `model: opus`, an isolated implementer with
  `model: sonnet`.
- **Bound every loop.** Any review → fix → re-review loop runs at most twice; then STOP and ask
  the human.
- **Never mark T3 satisfied** without the human's attestation.
