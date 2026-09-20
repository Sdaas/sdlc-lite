# Proposal — Gate 1 INTERVIEW hardening + requirements rubric

_Dated 2026-09-20. Companion to `2026-09-20-design-review-gate-proposal.md`; both implement
findings from `2026-09-20-agentic-sdlc-gap-analysis.md`. **Nothing here is wired in** — no file
under `sdlc-lite-plugin/` has been changed. Three blocking decisions in §1._

_Unlike the design proposal, this one adds **no new gate and no new agent**. Every change below
is prose in `SKILL.md` Gate 1 or structure in `requirements-template.md`, plus one free
addition to the already-proposed `design-reviewer`. No `guard.py` change, no renumbering, no
extra model call per run._

---

## Read this first

**Three decisions block everything else** — all in §1:

| | Decision | Recommendation |
|---|---|---|
| **D1** | Batching: keep whole-frontier rounds, or one question at a time? | **Capped frontier** (3–4, load-bearing first, tree-reshaping questions asked alone) — not strict one-at-a-time |
| **D2** | Does the intent hypothesis replace or precede the P57 scope anchor? | **Precede it** — you can perfectly scope the wrong feature |
| **D3** | Given/When/Then for ACs: universal or conditional? | **Conditional** — GWT for stateful/sequenced ACs only |

**Two things worth flagging before you read the deltas:**

1. **The `➡️` recommended answer is a bias with no counterweight, and P57 aims it.** Attaching a
   recommendation is right — a human reacts to a wrong guess faster than they generate an answer
   — but addy ships the same mechanic *and* names the sycophancy risk it carries. We ship it
   with no mitigation, and P57 additionally tells the conductor to default to the *smaller*
   option. Together that is a systematic scope-loss bias the human is invited to rubber-stamp.
   **§2.3 is the mitigation, and it is the highest risk-weighted item in this document** — more
   so than anything in §2.1 or §2.4, because it degrades silently and looks like agreement.

2. **Principle IDs are unallocated.** Highest `P<n>` currently in use is **P57**. Five additions
   here would want IDs — the intent hypothesis + stop test, the sycophancy rule, the
   explicit-approval definition, the evidence-bearing assumption block, and the split check. I
   have not assigned numbers; that is yours.

**Also worth knowing before reading:** §5 records six ideas considered and deliberately *not*
proposed (strict one-at-a-time, a persisted `CONTEXT.md` glossary, extracting `grilling` as a
reusable primitive, a dedicated assumptions subagent, a full intent-discovery phase, and
user-expertise profiling) — each with the reason, so they are not silently dropped.

---

## 0. Position

Gate 1's core primitive — design tree, frontier worked in rounds, `❓`/`➡️` numbered questions,
"facts are your job, decisions are the human's" with non-blocking subagent dispatch — is
**functionally identical to mattpocock's `grilling`**, which is the best-in-class version of
this primitive in the field. Two things we have that nobody else does:

- **P57 smallest-viable anchor.** Grilling's completeness bias is real and none of the five has
  a counterweight.
- **The boundary inventory**, with its per-boundary "how it will be exercised un-mocked at
  VERIFY" column — unique, and load-bearing for Gate 6.

Nothing below touches either. The changes are about **how questions land, how the gate knows it
is finished, and what the output carries.**

---

## 1. Three decisions needed

### D1 — Batching policy: keep frontier rounds, or one question at a time?

We ask the whole frontier per round. **Two of the five explicitly forbid this.** Addy's
`interview-me` lists *"Three or more questions in a single message: that's batching, not
interviewing"* as a Red Flag, with four arguments:

> The user can't react to your hypotheses if you bury them in a list · Batches encourage
> skim-reading and surface answers · The third question often depends on the answer to the
> first; asking them all at once locks in the wrong framing · The user's energy for thinking
> carefully is finite

Superpowers: *"Only one question per message."* Mattpocock batches the frontier, like us. GSD
asks one question at a time with 2–4 concrete options to react to.

The frontier argument is sound in theory — questions whose prerequisites are settled genuinely
are independent. Addy's third point is the rebuttal: **the dependency graph is the asker's
hypothesis, and you only learn it was wrong when an answer surprises you.** A batch spends that
surprise before it can be acted on.

| Option | Trade-off |
|---|---|
| **A. Capped frontier (recommended)** | Keep rounds, cap at 3–4 questions, lead with the load-bearing one, and ask a *tree-reshaping* question alone. Keeps throughput; removes the worst of the skim-reading failure. |
| B. One at a time | Matches addy + superpowers exactly. Costs round-trips — and for a scoped feature in an existing repo the tree is shallower than greenfield, so the cost is less justified. |
| C. Status quo | Defensible, but then the round-size risk should at least be written down as a known trade-off. |

**Recommendation: A**, with the principled rule stated explicitly — *the frontier is for
independent decisions; a question whose answer could reshape the tree is asked alone.*

### D2 — Does the hypothesis replace or precede the P57 minimal-version opener?

P57 currently makes the first move a **scope** proposal (minimal version + deferred list). Addy
makes the first move an **intent** hypothesis with a confidence number. These are different
objects: you can have a perfectly-scoped minimal version of the wrong feature.

| Option | Trade-off |
|---|---|
| **A. Hypothesis, then scope anchor (recommended)** | One extra exchange. Catches the "you asked for a dashboard, you need a list" class before scope is anchored to the wrong thing. |
| B. Merge into one opener | Cheaper, but conflates "what do you actually want" with "what is the smallest version" — the second presumes the first. |
| C. Keep P57 as the opener | No change; accepts the risk of efficiently scoping the wrong feature. |

**Recommendation: A.** The anchor is more valuable once you know what you're anchoring.

### D3 — Given/When/Then for acceptance criteria: universal or conditional?

OpenSpec's `### Requirement: … SHALL …` + `#### Scenario:` GIVEN/WHEN/THEN makes each scenario
directly a test case, which tightens the `01 → 04` handoff. But forcing GWT on
`parse_duration("5m") → 300` is ceremony.

**Recommendation: conditional** — GWT required when an AC involves state, sequence, or a flow;
a plain assertion form is fine for a pure input→output AC. §3.2 drafts both forms.

### Principle IDs

The house style tags rules with `P<n>` (highest currently in use: **P57**). The additions below
would need IDs assigned — I have not allocated them, since numbering is yours. The candidates
are: the intent hypothesis + stop test, the sycophancy rule, the explicit-approval definition,
the evidence-bearing assumption block, and the split-detection check.

---

## 2. `SKILL.md` Gate 1 — proposed deltas

Drop-in prose, in the order it would appear. Existing Gate 1 text not shown here is unchanged.

### 2.1 New — opens the gate, before the P57 anchor

```markdown
**State your hypothesis and your confidence FIRST.** Before proposing scope, before the first
question, write one sentence naming what you believe the human actually wants, plus an honest
confidence (0–100%):

> **Hypothesis:** You want <one sentence>.
> **Confidence:** ~35% — missing: <what is unresolved>

**Below ~70%, the missing-list is mandatory** — the human cannot close a gap they cannot see.
The number forces honesty: if you wrote a high number but cannot predict the human's reaction
to the next three questions you would ask, the number is wrong.

What people ask for and what they want diverge. "Build me a dashboard" has turned out to mean
"I need a list." Anchoring scope (below) to a misread request produces a well-scoped version of
the wrong feature — the most expensive failure this gate can make, because every downstream
gate will faithfully implement it.
```

### 2.2 Amend — the Method block

Replace *"Each round, ask the whole **frontier** — every question whose prerequisites are
already settled"* with:

```markdown
- Each round, ask from the **frontier** — the questions whose prerequisites are already
  settled. **Cap a round at 3–4 questions** and lead with the load-bearing one. The frontier
  is for *independent* decisions: **a question whose answer could reshape the tree is asked
  alone**, because a batch spends the surprise before you can act on it. If an answer
  invalidates the rest of the round, say so and re-ask rather than proceeding on stale framing.
- Separate questions with a `---` rule so a multi-question round stays readable.
```

### 2.3 New — immediately after the question format block

```markdown
**Your `➡️` recommendation is a bias you must actively counteract.** Attaching a recommended
answer is right — a human reacts to a wrong guess faster than they generate an answer from
scratch — but it invites a polite human to agree with you, and P57 additionally tells you to
default to the *smaller* option. Together that is a systematic scope-loss bias the human is
being invited to rubber-stamp. So:

- Be **visibly willing to be wrong**, and on at least one question per round, recommend in the
  direction you expect push-back on.
- A recommendation the human accepts without comment on a **load-bearing** question is not a
  decision. Re-put it as an explicit either/or.

**Probe "want" versus "should want".** Treat these as unanswered, not answered:
- best-practice talk with no specifics — "scalable", "clean architecture", "robust", "modern";
- deference to convention — "the standard approach", "however most projects do it";
- "I should probably…", "I think I'm supposed to…".

The probe that does the most work: *"If you didn't have to justify this to anyone, what would
you actually want?"* Never accept a fuzzy answer — "good" means what? "fast" means what number?
"users" means who?
```

### 2.4 New — a splitting check, placed inside the P57 scope-anchor step

```markdown
**Before anchoring scope, check the request is ONE capability.** P57 stops a single capability
from growing; it does not detect a request that is genuinely several. These are different
failures and this one is worse — anchoring "the smallest viable version" of four features
produces a coherent-looking requirements doc for a thing that cannot be designed as a unit.

Trigger a split conversation if **any** of these fire:
- **Compound capability** — two or more independent user actions joined by "and".
- **Multi-actor** — more than one role ("as a user *or admin*…").
- **Vague capability** — a noun phrase rather than a verb-noun pair ("use the dashboard" —
  which interaction?).
- **Length** — the one-sentence restatement will not fit in one sentence.

On a trigger, present the split and **STOP**: name the capabilities, recommend which one to
build now, and say the others are separate runs. Split along *user-visible* lines — happy path
before edge paths, one data scope before many, basic rules before complex policy. **Never split
by technical layer** ("first the schema, then the API, then the CLI"): that is horizontal
planning, and no slice of it is independently verifiable.

The human may overrule and proceed with the whole thing; record that as an explicit decision.
```

### 2.5 Amend — the completeness rule

Replace *"Done when the frontier is empty — **nothing silently assumed**"* with:

```markdown
- Each answer reshapes the tree; recompute the frontier and ask the next round.

**Two stop conditions, both required.** "The frontier is empty" is assessed by the same agent
that built the tree — a tree missing a branch yields an empty frontier and a confident, false
"done". So pair it with a test you can fail:

1. **The frontier is empty** — every branch visited, nothing silently assumed; and
2. **You can predict the human's reaction to the next three questions you would ask.**

If (2) fails, you are not finished, whatever (1) says. If you have run several rounds and (2)
still fails, that is information about the request, not a reason to keep grinding: **STOP and
say so** — "I've asked N questions and still can't predict your answers; something foundational
is missing. Can we step back?"
```

### 2.6 Amend — the gate close

Insert before the existing draft-authoring step:

```markdown
**Restate, short, before you write the file.** Give the human a 6-line restate in their own
words, so misalignment surfaces against something they can read in one breath rather than a
40-line document:

> - **Outcome:** …
> - **Who it's for:** …
> - **Why now:** …
> - **Success looks like:** …
> - **Binding constraint:** …
> - **Out of scope:** …

**The out-of-scope line is not optional** — half of all misalignment is silent disagreement
about what is *not* being built. Then author the draft (below); the restate orients the human,
the file is what they approve (P47).
```

And amend the approval step:

```markdown
- **STOP. Do not promote or proceed until the human replies APPROVED.**

  **These are not approval.** Each one means the gate is not finished:
  - *"whatever you think is best"* — delegation, not a decision. Re-put the open question as
    two concrete options.
  - *"sounds good" / "sure, let's go"* — ambiguous, and often a polite exit. Ask "anything
    you'd refine?" Silence is not confirmation.
  - Silence followed by "ok, start" — the human has given up on the interview, not converged.
    Ask what you missed.

  An approval that follows a vague restate is hollow. Restate concretely and re-confirm.
```

### 2.7 New — a non-interactive guard, at the top of the gate

```markdown
**This gate requires a live human.** If the session is non-interactive (headless, CI, a
scheduled or looped run), do **not** infer answers — STOP and report the underspecified request
as a blocker. A workflow whose first gate guesses produces a requirements file that looks
approved and was not.
```

---

## 3. `requirements-template.md` — proposed deltas

### 3.1 New §2 — Assumptions (evidence-bearing), before the ACs

Renumbers the existing §2–§6 down by one. The current §6 "Out of scope / assumptions" keeps
out-of-scope and loses assumptions to here.

```markdown
## 2. Assumptions
What this feature's requirements assume — about the existing codebase, its conventions, library
behaviour, or the environment. Surface these **before** the ACs, not after: an assumption baked
silently into an AC is invisible to every downstream gate.

Facts are the conductor's job (Gate 1) — so where an assumption came from reading the repo,
**cite the file**. Every row states a concrete consequence, not "could cause issues".

| Assumption | Why (evidence — cite a path, or "asked the human") | If wrong | Confidence |
|---|---|---|---|
| … | … | … | Confident / Likely / Unclear |

### Needs external research
Anything the codebase cannot settle (library version behaviour, ecosystem convention) that was
*not* resolved during the interview. "None" is a valid and common answer.
```

### 3.2 Amend — functional acceptance criteria

```markdown
## 3. Functional acceptance criteria
Numbered, independently testable. Cover inputs/outputs, core behaviour, error conditions, and
edge cases. Each AC becomes one or more rows in `04-test-plan.md`, so write them in the shape a
test can consume:

**Stateless AC** (a pure input → output claim) — a plain assertion is enough:
- **AC1** — `parse_duration("5m")` returns `300`.

**Stateful or sequenced AC** (involves state, ordering, a flow, or a side effect) — use
Given/When/Then, so the scenario *is* the test case:
- **AC2** —
  - **GIVEN** a cache holding a previously-fetched value
  - **WHEN** the upstream call raises a connection timeout
  - **THEN** the timeout propagates to the caller
  - **AND** the stale value is not returned and not re-cached

Use MUST / MUST NOT for absolute requirements and SHOULD where a justified exception exists.
An AC that cannot be written in either form is not yet an acceptance criterion — it is a
wish. Take it back to the interview.
```

### 3.3 Amend §1 — carry the confirmed restate

Add under **Summary**:

```markdown
### Confirmed intent (the Gate 1 restate, as approved)
- **Outcome:** …
- **Who it's for:** …
- **Why now:** …
- **Success looks like:** …
- **Binding constraint:** …
- **Out of scope:** …
```

This makes the file self-sufficient in the sense the template already claims ("This file — not
the conversation — is the inbox for downstream gates"), and it is the block a future
`designer` agent would need if DESIGN ever becomes an `[I]` gate (design proposal §4.3).

### 3.4 Amend §1 — record a split decision

Under the scope-boundary block:

```markdown
- **Split check:** "Single capability" — or, if a split trigger fired: the capabilities
  identified, which one this run builds, and the human's decision on the rest.
```

---

## 4. One free addition to the `design-reviewer`

The requirements have no independent critic — the same structural hole as the design, and it
now bites twice, because the proposed `design-reviewer` is told to treat `01-requirements.md`
as **the contract** and therefore structurally cannot flag that the contract is wrong.

Add to `agents/design-reviewer.md`, under **Judge**:

```markdown
9. **Defects in the contract itself.** You judge the design *against* `01-requirements.md`, but
   you also have the repo in front of you and the requirements may be wrong. Report these
   **separately**, under a `## Requirements findings` heading, never mixed with design
   findings: an AC that is untestable as written; an AC that contradicts another; a constraint
   the codebase already violates or makes impossible; a boundary the feature obviously touches
   that the inventory omits; an assumption in §2 that the code contradicts (cite the file).
   These route back to **Gate 1**, not Gate 2 — flag them for the conductor to take to the
   human, and do not attempt to resolve them yourself.
```

This costs nothing: the agent already reads both artifacts.

---

## 5. Considered and NOT proposed

Recorded so they are not silently dropped:

| Idea | Source | Why not now |
|---|---|---|
| Switch to strict one-question-at-a-time | addy, superpowers | D1 option B — throughput cost not justified for a scoped feature in an existing repo. Revisit if dry runs show skim-answering. |
| Persist a `CONTEXT.md` domain glossary built during the interview | mattpocock `grill-with-docs` | High value (he rates it his best technique) but it is the durable-artifact question (gap B3), which is a v2 decision, not a Gate 1 patch. |
| Extract `grilling` into a reusable model-invoked skill | mattpocock | Right answer, wrong time — it becomes load-bearing when `/fix-bug` exists and needs the same discipline with different buckets. Do it then, not speculatively. |
| A dedicated assumptions-analyzer subagent | GSD `gsd-assumptions-analyzer` | §3.1 captures the *output shape* (evidence / if-wrong / confidence) without a sixth agent. Promote to an agent only if dry runs show the conductor doing this badly. |
| Full intent-discovery phase (purpose, who, why now, before anything) | superpowers `brainstorming` | §2.1 + the §2.6 restate capture most of the value at a fraction of the cost. Our scope is a feature in an existing repo, not a greenfield project. |
| Adapt questioning to the user's expertise | GSD `gsd-user-profiler` | GSD's own questioning guide forbids asking about it ("NEVER ask about user's technical experience"). Not worth the contradiction. |

---

## 6. What a dry run must show

1. **The hypothesis is wrong at least once, visibly.** Seed a run whose one-line request is
   conventional but misleading ("add a dashboard for the run stats" when a list is wanted). The
   opening confidence should be low, and the hypothesis should change. If the conductor opens
   at 90% on every run, the number is decoration.
2. **Split detection fires.** A request with an "and" in it must trigger §2.4 and STOP, not get
   anchored as one capability.
3. **The stop test bites.** Verify at least one run where the frontier empties but the
   conductor continues because it cannot predict the next three answers. If that never happens,
   the second condition is not being applied.
4. **"Sounds good" is not accepted.** Reply to the approval request with "sounds good" and
   confirm the gate re-asks rather than promoting.
5. **Assumptions cite real paths.** Every row in §2 with a file citation — open the file and
   confirm the claim. A fabricated citation here is worse than no citation.
6. **Interview cost.** Gate 1 is the most human-time-expensive gate; §2.1, §2.4 and §2.6 each
   add an exchange. Measure whether round count goes up or down — the hypothesis is that
   earlier correction *reduces* total rounds.

---

## 7. Suggested commit sequence

Smaller and lower-risk than the design proposal — no new gate, no new agent, no guard change.

1. **Requirements template** — §3.1–§3.4. Takes effect at the next Gate 1; improves the
   artifact even with no `SKILL.md` change.
2. **Gate 1 stop test + non-interactive guard** — §2.5, §2.7. Self-contained.
3. **Gate 1 intent hypothesis + restate + approval definition** — §2.1, §2.6 (D2).
4. **Gate 1 anti-sycophancy + round cap** — §2.3, §2.2 (D1).
5. **Split detection** — §2.4.
6. **`design-reviewer` requirements-findings class** — §4, folded into whichever commit lands
   that agent.
7. Dry run (§6), then developer-guide principle IDs and the user-guide walkthrough.
