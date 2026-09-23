# Concept: `/plan-feature` — decomposing large features into a buildable DAG

> **Status:** proposed (concept / not yet implemented)
> **Companion issue:** [#32](https://github.com/Sdaas/sdlc-lite/issues/32) (this doc is the *why*; the issue is the *do* — they cross-reference each other).
> **Audience:** anyone evaluating, scoping, or building this capability.

---

## 1. Problem statement (why)

`/implement-feature` turns a one-line request into reviewed, tested, committed code through a
test-first, human-in-the-loop workflow. It works well for **small features** — one or two components,
a bounded set of use cases, interactions you can hold in your head and TDD in one sitting.

It breaks down for **large features** — think *"implement GDPR support"*: many components, complex
interactions between them, a large surface of use cases and edge cases, and cross-cutting constraints.
For work like this, jumping straight into the design→implement→test cycle is the wrong move. The
agent's attention gets divided across too many moving parts and the result is a mess.

The missing step is **understanding and decomposition before construction**: understand the
requirements (functional *and* non-functional), identify the key components / interactions / use
cases, produce a system-level design, and break the work into smaller items that *can* each be built
by `/implement-feature`. Then build the pieces and integrate them back into a coherent whole.

**The core reframing.** The trigger for "don't start implementing yet" is **not raw size**. It is
**uncertainty-of-structure combined with decomposability**: we can't yet confidently *name the child
work items*, and the work *can* be split into parts that are each small enough to build well in
isolation. Size is merely the usual cause. A one-component feature with genuine algorithmic
uncertainty may need design; a six-file CRUD change is just six small features wearing a trenchcoat.
Naming the axis this way stops medium-but-clear work from being pushed down the heavyweight path.

## 2. What this is

A new **`/plan-feature`** capability — a *planner* whose deliverable is **a plan, not code**:

- a **system-design document** and a **requirement → test coverage matrix** (functional + NFR),
  committed to the repo under `docs/plans/<X>/`;
- a **bill of work**: a DAG of **GitHub issues** — children `A, B, C, …` plus a terminal
  integration-and-verification issue `Z` that depends on them;
- each child issue carries a **structured contract** (interface, dependencies, acceptance + its slice
  of the NFRs) that is a valid input to `/implement-feature`.

`/plan-feature` is **upstream** of `/implement-feature` and separate from it. It emits issues and
**exits** — it is not a long-lived supervisor. If the plan turns out to be a single issue, no harm
done: that issue simply feeds `/implement-feature` as usual.

The two tools together form a small **SDLC suite**: `/plan-feature` (understand + decompose) →
`/implement-feature` (build each piece) → the terminal `Z` issue (integrate + verify the whole).

## 3. How it works

### 3.1 The shape: a DAG, not a running loop

Integration of a large feature realistically happens *weeks* after its parts are built. We explicitly
reject a "living document" that sits half-complete ("planning done, integrate later…"). Instead the
work splits into three phases tracked entirely as a **DAG of GitHub issues**:

```
          plan X  ──►  build A ┐
 (plan-feature)        build B ├──►  Z: integrate + verify X  ──►  merge to main
                       build C ┘      (another /implement-feature run)
```

- **Composition edges** (`X` is made of `A, B, C, Z`) → GitHub **sub-issues**.
- **Ordering edges** (`Z` is blocked by `A, B, C`) → GitHub **issue dependencies**.
- **"X is done" ≡ "Z is closed."** `Z` is *the* node that re-checks X's requirement→test matrix, so
  there is one unambiguous done-signal rather than "count the checkboxes."

The "outer loop" is therefore a **DAG with a sink node**, not a process that has to stay resident. Any
competent DAG tracker (GitHub issues) keeps the state; nothing needs to keep running.

### 3.2 What each child issue carries — and what it must *not*

To decompose X, the planner reasons about the children's **internals and their interactions**. But
`/implement-feature`'s central invariant is the **interface/internal design split** that keeps its
test-writer *algorithm-blind*. If a child issue carried the planner's internal-design reasoning, the
child's test-writer would read it and **algorithm-blindness would be broken one level up**.

So a child issue carries a **contract, not an algorithm**: its interface (inputs, outputs, the seam to
its siblings), its dependencies, its acceptance intent, and its allocated slice of the NFRs —
**never** a sketch of *how* to implement it internally. `/implement-feature` then runs its normal gates
(including its own interface/internal split and double-model review) **unchanged**.

### 3.3 Non-functional requirements decompose too

NFRs (security, performance, scale, resilience, constraints) are cross-cutting and often only violable
at integration. The planner **allocates what's allocatable** and **verifies the remainder at Z**:

- push a concrete, testable slice into each child's contract where one exists — a latency budget
  ("A owns ≤ 50 ms of the 200 ms p99"), encryption-at-rest, an input-validation obligation;
- leave genuinely global NFRs (e.g. an end-to-end GDPR erasure SLA) as **Z-verified** acceptance.

An NFR that can't be allocated *or* verified is a **decomposition smoke alarm** (see §3.6).

### 3.4 The integration-and-verify node `Z`

`Z` is **just another `/implement-feature` run** — its "feature" is *"write the glue between A/B/C and
make X's named end-to-end tests green."* Its inbox is the **public interfaces** of A/B/C plus X's
end-to-end test plan and the requirement→test matrix; it stays **algorithm-blind** about each child's
internals, which is fine because **glue talks to seams, not guts**. Its definition of done is the
matrix all-green, un-mocked (the repo's VERIFY invariant). If Z *can't* be written against seams
alone, that is itself a signal the decomposition was wrong — a useful smoke alarm, not a reason to
break isolation.

### 3.5 Branching: X is the shippable unit, not the child

A child is usually **not independently shippable** — `A` may be dead code until `B` and `Z` integrate
it. So children must not merge to `main` individually (that pollutes `main` with partial work, and a
re-plan means reverting already-merged, already-public commits).

Instead, `/plan-feature` creates a **per-X integration branch `feat/X`**. Each child branches off
`feat/X` and PRs back into it; `Z` integrates and verifies on `feat/X`; **only a Z-green,
matrix-passing `feat/X` merges to `main` as one coherent unit.** A wrong decomposition discovered at Z
is contained to `feat/X` — `main` never saw it — and reverting a mis-built child is a branch
operation, not a `main` rewrite. Drift is mitigated by periodic `main → feat/X` merges.

> **Required change to the existing tool:** `/implement-feature`'s base branch must become a
> **parameter** (default `main`; `feat/X` when invoked on a child), not a hardcoded assumption.

### 3.6 When reality contradicts the plan (the feedback loop)

The plan is a **hypothesis; implementation is the test.** A child run may reveal the decomposition was
wrong — the Q11 smoke alarm fires, a child turns out infeasible, or building one exposes a missing
component. This is a **first-class, explicit outcome**: the child run writes a *decomposition-defect*
note back onto X's issue and **stops**; the **human** decides whether to re-enter `/plan-feature` for
X or adjust. Re-planning is **human-gated**, never automatic. Without this, the DAG quietly degrades
into fiction the moment one child surprises us.

### 3.7 Recursion (bounded)

By the §1 axis, a child is not guaranteed to be small — discovering `A` is itself GDPR-sized is common.
So largeness may **recurse**: a child that smells large re-enters `/plan-feature`, producing a
sub-DAG. Depth is **capped at 2–3** (beyond that, dependencies become impractical to track as GitHub
issues) and the cap surfaces to the human, honoring the repo's "bound every automated loop, surface on
no progress" invariant.

### 3.8 The smell test in `/implement-feature`

`/implement-feature` gains a **smell test**: after its requirements/interview gate (the honest point —
the trigger is "can't confidently name the pieces"), if the work crosses the uncertainty/component
threshold it states the smell and recommends `/plan-feature`. It is **advisory-with-friction**: it
requires an explicit human *"proceed anyway"* to continue. Blocking fights the human; silent-advisory
gets ignored. Ultimately **the human is accountable** for the code and the decision.

### 3.9 Architecture and models

`/plan-feature` **mirrors the existing declarative pattern** — a skill (`SKILL.md`) as the score,
pinned-model agent-definition files, and the shared guard hook; no hand-written orchestration driver.
It ships as a **second skill inside the existing plugin** (shared hooks/agents/toolchain, one mental
model), turning the plugin into a small SDLC suite with two entry points.

Planning is the **highest-leverage design work in the whole system**, so by the repo's own "design
uses a higher model/effort than implementation" invariant it runs on **Opus 4.8 high**. But the
planning conductor is **human-interactive** (requirements interview, design decisions) and therefore
**cannot be an isolated subagent** — subagents can't talk to the human. So the conductor runs
interactively on the strong model and the skill **warns the user if a weaker model is active**.
*Non-interactive* bias-sensitive gates (notably a **decomposition red-team reviewer** that attacks the
plan for gaps/overlaps before issues are emitted) *can* still be isolated subagents.

## 4. Critical design decisions

*ADR-style; each records the decision, the why, and the approaches discarded.*

### D1 — The axis is uncertainty + decomposability, not raw size
*Decision:* trigger the heavyweight path on *"we can't yet confidently name the child work items, and
the work can be split into confidently-small pieces,"* not on component/file count.
*Why:* size is correlated with the need to plan but isn't the thing itself.
*Discarded:* (a) raw size thresholds — misfires on big-but-trivial CRUD; (b) agent swarms to hold a
large undivided feature in parallel attention — an explicit non-goal, too big a leap for now.

### D2 — A separate upstream `/plan-feature`, not a branch inside `/implement-feature`
*Decision:* planning is its own command; its output is issues; it feeds the unchanged
`/implement-feature`.
*Why:* decomposition (produces *issues*, human-reviewed, maybe never built) and implementation
(produces *committed code*) have different inboxes, done-bars, models, and review cultures. Folding
them under one command because they're adjacent in time is a category error.
*Discarded:* one command that detects scope and branches internally — muddies both contracts.

### D3 — The planning output has a falsifiable "done," not just "docs exist"
*Decision:* done for a plan = *each child is a valid `/implement-feature` input* **and** *the set of
children covers X's enumerated requirements with no orphan requirement* (a requirement→issue/test
coverage matrix), proven by dry-running one representative child to green.
*Why:* this repo's culture rejects "done = docs exist." The plan needs a green-dry-run analog.
*Discarded:* human-approval-only (weakest; unfalsifiable).

### D4 — The outer loop is a DAG with a sink node, not a living supervisor
*Decision:* emit integration+verification as a terminal child issue `Z` that depends on A/B/C;
`/plan-feature` exits forever after emitting.
*Why:* integration happens weeks later; a resident conductor can't wait, and a half-complete "living
document" is exactly the kind of partial state we're avoiding. GitHub tracks the DAG.
*Discarded:* a re-enterable living supervisor with cross-session state + child-status polling — a lot
of machinery to avoid writing one more issue.

### D5 — Children carry a contract, never an algorithm
*Decision:* each child issue renders from a **structured contract template** (interface, deps,
acceptance, NFR slice) — no free-form "design notes" field.
*Why:* protects `/implement-feature`'s algorithm-blindness one level up, and closes the leakage
channel **by construction** rather than by willpower.
*Discarded:* (a) ship the full internal design and have `/implement-feature` skip its design gate —
defeats blindness + double-model review; (b) ship only a one-liner and fully re-interview — loses
planning's work.

### D6 — The no-leak invariant is construction-enforced + review-gated, not hook-enforced
*Decision:* child issues generate only from the structured contract; the red-team reviewer
double-checks for internal-design leakage before emit. Planner-private reasoning lives in a
gitignored `.plan-feature/<run>/`.
*Why:* "is this prose a contract or a leaked algorithm?" is **semantic** — a guard hook (which gates
file paths / `.env`, not meaning) genuinely can't decide it, and the conductor is interactive anyway.
We state this honestly rather than overclaiming hook enforcement.
*Discarded:* pretending the guard hook can detect semantic leakage.

### D7 — `Z` is a normal `/implement-feature` run against seams
*Decision:* integration is implementation; its inbox is A/B/C's *public interfaces* + X's e2e plan; it
stays algorithm-blind.
*Why:* glue talks to seams, not internals. A `Z` that needs internal visibility means the
decomposition was wrong (smoke alarm).
*Discarded:* a new cross-cutting tool with internal visibility — breaks single-feature isolation.

### D8 — Per-X integration branch `feat/X`; X is the shippable unit
*Decision:* children merge into `feat/X`, not `main`; only Z-green `feat/X` merges to `main`.
*Why:* children aren't independently shippable; keeps `main` coherent; makes a re-plan survivable as a
branch operation.
*Discarded:* (a) children→`main` directly — pollutes `main`, painful public reverts on re-plan;
(b) children→`main` behind a feature flag — still leaves dormant cruft on re-plan, plus flag tax.

### D9 — Re-planning is an explicit, human-gated outcome
*Decision:* a child can emit a *decomposition-defect* signal onto X and stop; the human decides.
*Why:* keeps the plan falsifiable by implementation; honors "surface to the human on no progress."
*Discarded:* silent workaround (plan rots); fully automatic re-plan (toward swarm territory — ruled
out).

### D10 — Recursion allowed, depth-capped at 2–3
*Decision:* a large child re-enters `/plan-feature`; cap depth and surface at the cap.
*Why:* the uncertainty axis can bite at any level; but GitHub-issue dependency tracking becomes
impractical past depth ~3.
*Discarded:* guaranteeing small children by construction (the axis makes that impossible); forbidding
recursion entirely (forces manual re-planning).

### D11 — The smell test is advisory-with-friction, fired post-interview
*Decision:* `/implement-feature` warns after its requirements gate and requires an explicit "proceed
anyway."
*Why:* the honest signal exists only once use cases are enumerated; the human is accountable.
*Discarded:* blocking (fights the human); silent-advisory (ignored); firing at raw intake (guessy).

### D12 — Mirror the declarative architecture; run planning on Opus 4.8 high (interactive)
*Decision:* skill + pinned agent-defs + shared guard; conductor is interactive on Opus 4.8 high and
warns on a weaker model; only non-interactive bias-sensitive gates are isolated subagents.
*Why:* planning is the highest-leverage design step; but a subagent can't interview the human.
*Discarded:* running the whole planner as an isolated subagent (can't talk to the human).

## 5. Constraints

- **GitHub is the DAG substrate** (sub-issues + dependency edges). No other tracker in v1.
- **Human-in-the-loop is non-negotiable**: no commit before approval; re-planning is human-gated; the
  smell test needs explicit override.
- **Isolation invariants from `/implement-feature` must survive one level up** — algorithm-blindness,
  design uses a higher model than implementation, green unit tests aren't "done" (VERIFY un-mocked),
  bound every loop and surface on no progress, never commit on the default branch.
- **Interactive conductor** ⇒ the planner can't be a pure subagent; strong-model usage is *warned*,
  not hook-enforced.
- **Depth cap 2–3** on recursion.

## 6. Scope

### In scope (v1)
- Interactive conductor on Opus 4.8 high, with a model warning.
- Functional **and** non-functional requirement elicitation.
- System-design doc + requirement→test matrix committed to `docs/plans/<X>/`.
- Decompose into structured-contract child issues + a terminal `Z` issue.
- Native GitHub sub-issues + dependency edges.
- Decomposition red-team reviewer subagent.
- **Depth-1 decomposition only**, with the depth cap **enforced** (refuse / surface at depth > 1 so v1
  fails safe).
- Changes to the existing `/implement-feature`: the smell test; intake-detection that **collapses** a
  contract-driven intake to a single confirm-or-correct gate (not a full re-interview, not a blind
  skip); the base-branch **parameter**.

### Deferred (v1.1+)
- Recursion depth 2–3.
- Richer auto-allocated NFR *budgets* beyond simple stamping.
- Any automated re-planning.
- Integration-branch drift automation.

### Non-goals (explicit, not to be re-litigated)
- **No agent swarms / no parallel autonomous child execution.**
- **No auto-implementation of the DAG** — the human invokes `/implement-feature` per child.
- **No automatic re-planning** — re-plan is always human-gated.
- **Not a general project-management / roadmap tool** — it plans *one* feature X.
- **No non-GitHub tracker support** in v1.

## 7. Acceptance — the green end-to-end dry run

Per this repo, *"done" ≠ "the skill exists."* The falsifiable bar for the **capability itself**:

> In the dev container, `/plan-feature` takes a deliberately-large, deliberately-decomposable **toy**
> request → produces the committed design doc + requirement→test matrix → creates a **real GitHub
> sub-issue DAG `{A, B, C, Z}`** with dependency edges → and **at least one child is driven through
> `/implement-feature` to green on the `feat/X` branch.**

That single threaded path exercises every seam — contract handoff, intake collapse, base-branch
parameter, and Z's existence — without implementing the whole feature. Mirror the existing
`toy-greet-plugin` idea with a purpose-built *"deliberately-decomposable"* toy fixture.

## 8. Open questions / to validate during build

- Exact threshold + signals the smell test keys on (component count vs. use-case count vs. an
  uncertainty heuristic).
- The precise structured-contract template fields (what's mandatory vs. optional).
- How `feat/X` drift is kept tolerable in practice for long-lived large features.
- Whether the red-team reviewer is one gate or splits into gaps-reviewer + NFR-reviewer.
