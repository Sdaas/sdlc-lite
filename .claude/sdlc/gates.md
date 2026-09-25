# The repo-local SDLC spine

Shared by this repo's own skills — `/issue`, `/feature` (#52), `/fix` (#53). A skill **executes**
this spine; it never restates it. Change a gate here, once.

**Scope:** work on *this* repo — the plugin's prose (`SKILL.md`, `agents/*.md`, `references/*`,
`hooks.json`) and its small code surface (`guard.py`, `policy.py`, `agentdefs.py`, `analyzer/`).
Not the `sdlc-lite` plugin's own workflow, which serves a user's Python repo.

**Tiers:** T1 / T2 / T3, what each proves, and the change → minimum-tier table are defined in
[`dev-docs/verification-ladder.md`](../../dev-docs/verification-ladder.md). This file only names
them. Why this repo cannot use `sdlc-lite` on itself: that file, §6.

---

## Modes

- **[C]** — the interactive session (the conductor).
- **[I]** — an ad-hoc subagent with a fresh context and an inline `model:`. Its brief carries
  only what the gate needs; never your intent, never the answer you expect.
- **↔H** — the gate talks to the human before it can finish.
- **STOP** — the gate ends by waiting for an explicit human approval. Silence is not approval.

---

## Gates 0–8

| Gate | Mode | What | STOP |
|---|---|---|---|
| **0 CLASSIFY** | [C]↔H | Resolve `#NN` with `gh issue view NN`. Missing, or not conforming to `dev-docs/issue-template.md` → hand off to `/issue` and exit. Classify the surface: prose · hook · code (`guard.py`/`policy.py`/`agentdefs.py`/`analyzer/`) · docs-only. Docs-only or shell-only → **decline and exit** (not gated). Declare the minimum tier from the ladder. Create branch `<NN>-<slug>` — never work on `main`. Decide whether `<NN>-plan.md` is warranted (root `CLAUDE.md` → Planning docs). | **① scope · tier · branch** |
| **1 DESIGN** | [C]↔H | Which files change and how; the behavior delta a cold reader should show; the eval cases that will prove it, **in run order**, and the `--max-cost-usd` cap (see Eval budget). Write `<NN>-plan.md` if Gate 0 said so. | **② plan** |
| **2 EXPECTATIONS** | [C] | **Write the eval cases before editing any prose**, then run each new case once: it must fail, or pass for the wrong reason. This is the repo's "red". Do not stop on a failure here; a case that **passes** is the surprise — show it to the human, it does not test the change. For a code change, write the failing `pytest` instead. | |
| **3 IMPLEMENT** | [C] / [I] | Edit the Markdown or code. [C] by default; [I] when the diff spans more than 3 files or touches `guard.py` / `policy.py` / `analyzer/`. | |
| **4 VERIFY** | [C] + H | Run the tier declared at Gate 0 and present the evidence, not a claim. T1: this change's new cases only, fail-fast (see Eval budget). T3 cannot be automated: the human runs it and attests. | **③ evidence** |
| **5 REVIEW** | [I] `opus` | Cold review of the whole diff against the six dimensions below. | |
| **6 REGRESSION** | [C] | Existing eval cases, fail-fast: `smoke`-tagged first, then those tagged with the areas the diff touched. Plus `pytest` if code changed. Never the full suite. | |
| **7 REVIEW-GUIDE** | [C]↔H | Changed files in review order, one line each, with pointers to the eval report and the review findings. | **④ pre-commit** |
| **8 COMMIT** | [C]↔H | Commit per logical unit, referencing `#NN`. At close, `git rm <NN>-plan.md`, ask the human **"open a PR, or merge to `main`?"**, then close the issue. | |

A skill may **add** gates between these (e.g. `/fix`'s REPRODUCE, DEPOSIT) or **omit** a range
(`/issue` runs none of them). It never renumbers or rewords a spine gate.

---

## The four STOPs

More gates than this produce rubber-stamping, which is worse than no gate.

1. **Scope · tier · branch** (Gate 0) — the human agrees what is in scope and what proof it owes.
2. **Plan** (Gate 1) — the human approves the design before anything is written.
3. **Evidence** (Gate 4) — the human judges the evidence sufficient. For T3, the human is the
   oracle.
4. **Pre-commit** (Gate 7) — the human has reviewed the diff. **Nothing is committed before it.**

---

## The six review dimensions

Every review states each dimension. `N/A — <why>` is allowed; silently dropping one is not.

1. **Unambiguity** — would a cold agent read this exactly one way?
2. **Consistency** — does it contradict another gate, an `agents/*.md`, the guard, or the docs?
3. **Enforcement parity** — does a new prose rule the guard should enforce have its `guard.py`
   denial and a T2 test?
4. **Context cost** — does the edit earn the tokens it adds to an always-loaded file?
5. **Isolation integrity** — does it leak a withheld artifact into a gate's inbox?
6. **Doc parity** — do `README.md`, `developer-guide.md`, or an ADR need to change with it?

---

## Eval budget

Every T1 run spends real tokens — roughly $0.20–1.00 per case per run. Inside a change, spend the
least that still answers the question.

- **Order.** This change's new cases first, in the order Gate 1 approved; then `smoke`-tagged
  cases; then cases tagged with the touched areas. Never the full suite inside a change.
- **Fail fast.** One `claude plugin eval` invocation per case (`--case <name> --runs 1`); stop at
  the first failure. The tool has no fail-fast flag, so the ordering is the mechanism.
- **A failure stops the gate.** Show it to the human, who decides whether to re-run. Never re-run
  on your own. A case tagged `flaky` is labelled as such when it fails.
- **One run is one run.** Evidence says "1 run"; at STOP ③ the human may ask for more.
- **Hard cap.** Every eval command at Gates 2, 4 and 6 carries the `--max-cost-usd` cap approved
  at STOP ②. Hitting it stops the gate. There is no default: the plan states it.
- **Not here:** the 3-runs-per-case pass over the whole suite is `/regression` (#64; before a
  release, or twice a week); the full release gate is `release-verify.sh` (ladder §8).

---

## Rules every skill inherits

- **Never commit before STOP ④.**
- **GitHub is the source of truth** for what an issue asks; no conforming issue → `/issue`.
- **Review runs on a higher model than implementation.** Repo-local skills cannot pin dated
  models; the REVIEW subagent is spawned with `model: opus`.
- **Bound every loop.** REVIEW → fix → re-review runs at most twice; then STOP and ask the human.
- **Never mark T3 satisfied** without the human's attestation.
