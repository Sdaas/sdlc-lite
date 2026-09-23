# 48-plan — Repo-local SDLC skills (`/issue`, `/feature`, `/fix`)

**Issue:** [#48](https://github.com/Sdaas/sdlc-lite/issues/48) · **Milestone:** none (backlog)
**Branch:** `feature/48-repo-local-sdlc` · **Status:** planned, not started

Branch-scoped working plan. `git rm` this file in the merge/close commit.

---

## 1. Goal

Give *this repo* a gated, human-approved SDLC for its own work — authoring Markdown
(`SKILL.md`, `agents/*.md`, `hooks.json`) plus the small real-code surface
(`guard.py`, `analyzer/`).

**Non-goals:** replacing or converging with `sdlc-lite`; evaluating the three new skills
themselves; automating the dev-container dry run.

## 2. Why `sdlc-lite` cannot serve this repo

Its spine rests on three assumptions, and all three fail here. *(This section is the source
for the Developer Guide rationale in P6.)*

| Assumption in `sdlc-lite` | Reality in this repo |
|---|---|
| The artifact is executable, so tests can go **red** before code | The product is **prose**. "Red" is undefined for Markdown. |
| A cheap deterministic green signal exists (`pytest`/`ruff`/`mypy`, seconds) | The real signal is a **dev-container dry run** — a full Claude session, minutes-to-hours, non-deterministic. Only `guard.py`/`analyzer/` have cheap tests. |
| The bias to isolate is "the implementer weakens the tests" | The bias here is **the author's curse of knowledge** — you read your own prose correctly because you know what you meant. |

Four consequences shape the design:

1. **Test-first inverts into expectation-first.** You cannot cold-read a `SKILL.md` section
   that does not exist yet. What transfers is the *assertion* coming first: write the eval
   case and its expected answer **before** editing the prose.
2. **Isolation flips from withholding to simulating.** `sdlc-lite` curates inboxes to
   *withhold* (algorithm-blind test-writer). Here the reviewing agent must see **exactly what
   the real runtime agent will see, and nothing more**. *Leaking your intent into the brief
   voids the test.*
3. **There is no "green" — there is an approved budget.** T3 is expensive and
   non-deterministic, so "done" is a verification tier the human approved at plan time whose
   evidence the human then judged sufficient. The human is the oracle in a way they never are
   in the Python flow.
4. **Prose accumulates no regression safety.** A fixed Python bug leaves a pytest case behind
   forever; a fixed prose bug leaves nothing. `claude plugin eval` closes this gap, and `/fix`
   is what forces the deposit.

**What transfers unchanged:** human approval gates, never-commit-before-approval, bounded
loops, curated handoffs, branch discipline, GitHub-as-SSOT, review on a stronger model than
implementation.
**What dies here:** mutation testing, coverage %, `ruff`/`mypy` (outside `guard.py`/
`analyzer/`), red-before-green on prose, dated model pins.

## 3. Locked decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | Three skills: `/issue`, `/feature`, `/fix` | Filing an issue is a distinct lifecycle moment from implementing one. |
| D2 | `/issue` stops at **triage-grade** clarity | Design-grade interviews produce premature specs, violating the ~300-word cap and duplicating `/feature` Gate 1. |
| D3 | One shared spine in `.claude/sdlc/gates.md` | Two skills with duplicated gate prose drift. |
| D4 | Skills, **not** a plugin | Accepted loss: no `effort` control, no dated model pins (reviewers drift as Opus tiers ship). Inline `model:` on ad-hoc subagents still gives review > implementation. Documented in P6. |
| D5 | **4 human STOPs** | More gates → rubber-stamping, which is worse than no gate. |
| D6 | GitHub is SSOT; no conforming issue → hand off to `/issue` | Hard-refusal creates friction you route around; delegation keeps the invariant without the friction. |
| D7 | T1 = `claude plugin eval`; the hand-rolled `.claude/coldread/` is **dropped** | Do not build a worse version of a shipped tool. |
| D8 | Eval cases **ship** in `sdlc-lite-plugin/evals/` | For a workflow plugin selling rigor, a runnable suite is a feature. |
| D9 | IMPLEMENT runs `[C]` by default, `[I]` only when the diff spans >3 files or touches `guard.py`/`analyzer/` | Spawning a subagent for a 5-line Markdown edit is overhead. REVIEW stays `[I]` + opus, so review > implementation holds. |
| D10 | T3 cannot be automated — the gate STOPs and the human attests | A dev-container dry run is a separate Claude session. Must be called out in the docs. |
| D11 | `dev-docs/verification-ladder.md` is the **SSOT** for T1/T2/T3; `.claude/sdlc/` links to it | Two homes drift. |
| D12 | `/feature` declines docs-only and shell-only changes | Gating a README edit is theater. |
| D13 | No evals for the three new skills (v1) | Dogfooding the evaluator on the evaluator is a rabbit hole; four STOPs govern them. |

## 4. Architecture

```
.claude/skills/issue/SKILL.md       # triage-grade capture → files a GitHub issue
.claude/skills/feature/SKILL.md     # 9 gates, 4 STOPs
.claude/skills/fix/SKILL.md         # same spine + REPRODUCE + DEPOSIT
.claude/sdlc/gates.md               # shared spine: gates, STOPs, review dimensions
dev-docs/verification-ladder.md         # SSOT for T1/T2/T3 (NEW)
dev-docs/eval-tutorial.md               # teaches `claude plugin eval` (NEW)
dev-docs/developer-guide.md             # + section: why this repo has its own SDLC
sdlc-lite-plugin/evals/             # shipped eval suite = the T1 corpus
```

`.claude/sdlc/` rather than `.claude/skills/_shared/` — anything under `skills/` is scanned
as a skill, and a directory with no `SKILL.md` is noise.

### 4.1 The `/feature` spine

| Gate | Mode | What | STOP |
|---|---|---|---|
| **0 CLASSIFY** | [C]↔H | Resolve `#NN` via `gh issue view`; missing/malformed → hand off to `/issue`. Classify surface (prose / hook / `guard.py`+`analyzer` / docs-only). Docs-only or shell-only → **decline and exit**. Pick the verification tier. Branch (never on `main`). Decide if a plan file is warranted. | **① scope · tier · branch** |
| **1 DESIGN** | [C]↔H | What changes in which files, the behavior delta a cold reader should show, and the eval cases that will prove it. Writes `<NN>-plan.md` if plan-worthy. | **② plan** |
| **2 EXPECTATIONS** | [C] | **Write the eval cases before editing any prose.** Run them; they fail or show the wrong behavior. The honest analogue of "red". | |
| **3 IMPLEMENT** | [C]/[I] | Edit the Markdown / code. Per D9. | |
| **4 VERIFY** | [C]+[I] | Run the declared tier (§5). Present evidence. | **③ evidence** |
| **5 REVIEW** | [I] opus | Cold whole-diff review against the six dimensions (§4.4). | |
| **6 REGRESSION** | [C] | Replay existing eval cases tagged by the files the diff touched. | |
| **7 REVIEW-GUIDE** | [C]↔H | Changed files, review order, one line each, pointers to the eval report and findings. | **④ pre-commit** |
| **8 COMMIT** | [C] | Commit per logical unit referencing `#NN`; `git rm <NN>-plan.md` at close. | |

### 4.2 `/fix` — two added gates

- **0.5 REPRODUCE** (before DESIGN) — reproduce at a named tier and record it.
  **Cannot claim "fixed" at a weaker tier than the bug was reproduced at.**
- **6.5 DEPOSIT** — the eval case that reproduces the bug is committed and must now pass.
  *A bug fix ships with a test.*

### 4.3 `/issue` — one STOP

Interviews to triage-grade only (what / why / impact; plus repro and its tier for bugs) →
drafts per `dev-docs/issue-template.md` under the ~300-word cap → type-only label → no milestone
(= backlog) unless told otherwise → `gh issue create` → prints the URL.
**Never branches, never touches code.**

### 4.4 The six review dimensions

Replacing `sdlc-lite`'s Python six. State `N/A — why`; never silently drop one.

1. **Unambiguity** — would a cold agent read this exactly one way?
2. **Consistency** — contradicts another gate, an `agents/*.md`, the guard, or the docs?
3. **Enforcement parity** — a new prose rule has a matching `guard.py` denial.
4. **Context cost** — `SKILL.md` is already 636 lines. Does this edit earn its tokens?
5. **Isolation integrity** — does it leak a withheld artifact into a gate's inbox?
6. **Doc parity** — README / developer-guide / ADR updates needed?

## 5. Verification ladder (summary — SSOT is `dev-docs/verification-ladder.md`)

| Tier | What | Cost |
|---|---|---|
| **T1** | `claude plugin eval` — seeded cases, 3 runs, free graders (`regex`, `tool_used`, `tool_order`, `file_exists`), `llm` sparingly. `context.history_file` seeds mid-workflow state so a gate is testable without driving all 12. | seconds–minutes |
| **T2** | `python3 -m pytest sdlc-lite-plugin -q` — the only executable surface (`guard.py`, `analyzer/`). Genuine TDD applies here. | seconds |
| **T3** | Dev-container end-to-end dry run. The only tier that proves a hook fires or a gate is reached. **Human-attested (D10).** | a full session |

**Change → minimum tier**

| Change | Tier |
|---|---|
| Gate wording / human-facing output | T1 |
| Gate behavior: routing, loop bounds, new gate | T1 + T3 |
| `agents/*.md` inbox or permission | T1 + T2 + T3 if flow changes |
| `guard.py` / `analyzer/` | T2 (+T1 if paired prose changed) |
| `hooks.json` registration | T3 — nothing else proves a hook fires |
| New `references/*` template | T1 |

**Budget:** every change → `--ablation none`, free graders, tag-filtered. Milestone /
pre-release → full suite, `--ablation with-without`, `--judge-model sonnet`, pinned `--model`,
`--threshold`, in the devcontainer; hooked into `release-verify.sh`.

**Known limit:** the eval sandbox loads no `CLAUDE.md`, no project settings, no other plugins,
no memory. Bugs that depend on project config (e.g. the P53 "read outside working directories"
prompt) are **structurally unreproducible** at T1 and stay T3-only.

**Eval practices to encode** (from the docs and the wider eval literature):
start with 5–10 realistic cases phrased as a user would type them, never naming the skill ·
at least one should-not-fire case (`min: 0, max: 0`, `arm: both`) · two graders per case, one
on the result and one on how Claude got there · free graders for the every-change suite ·
long output → `regex` over the file, not an `llm` judge · pin `--model` in CI so a model
rollout is not misread as a regression · run once with `--ablation none` before trusting any
Δ · `tool_used: Skill` passing while Δ is negative means suspect the judge, not the plugin ·
leave `partial: true` runs out of trend charts.

## 6. Phases

| P | Deliverable | Verification |
|---|---|---|
| **P1** | `.claude/sdlc/gates.md` — the shared spine, STOPs, six review dimensions | Read-through; no gate prose duplicated into the skills later |
| **P2** | `.claude/skills/issue/SKILL.md` | File one real backlog issue with it; output conforms to `dev-docs/issue-template.md` |
| **P3** | `sdlc-lite-plugin/evals/` — ≥6 cases incl. one should-not-fire | `claude plugin eval sdlc-lite-plugin --ablation none` (validate graders), then a baseline Δ run |
| **P4** | `.claude/skills/feature/SKILL.md` | Drive a small real enhancement through all 9 gates |
| **P5** | `.claude/skills/fix/SKILL.md` + DEPOSIT gate | Fix a real prose bug end-to-end; the deposited case fails before and passes after |
| **P6** | `dev-docs/verification-ladder.md`, `dev-docs/eval-tutorial.md`, Developer Guide section, README routing | A reader who has never seen this session can run `/feature` and `/fix` from the docs alone |
| **P7** | `release-verify.sh` milestone-tier hook | Full suite runs with `--threshold` and fails the script on a regression |

**Commit per logical unit** — one commit per phase unless a phase splits naturally. Review
list presented before each commit; nothing commits without approval.

## 7. Progress tracker

- [ ] P1 shared spine
- [ ] P2 `/issue`
- [ ] P3 eval seed suite
- [ ] P4 `/feature`
- [ ] P5 `/fix`
- [ ] P6 documentation (ladder · eval tutorial · dev guide · README)
- [ ] P7 release-verify hook
- [ ] `git rm 48-plan.md` in the close commit

## 8. Open items

- The issue-title area vocabulary (`gate-N · skill · guard-hook · analyzer · docs · release ·
  toolchain`) has no slot for repo-local dev tooling. `#48` uses `skill`. Consider adding a
  `repo` area — not blocking.
- Whether `/feature` should also update `release-plan.md`. Currently **no** — roadmap
  ordering stays a human call.
