# The sdlc-lite planning suite — architecture & gap analysis

_Dated 2026-09-20. **Supersedes and reconciles** the three prior analyses (now under_
_`docs/research/`): `2026-09-20-agentic-sdlc-gap-analysis.md` (implement-feature vs the field),_
_`2026-09-17-plan-feature-analysis-external.md` (the external 12-point plan-feature review), and_
_`docs/design/plan-feature.md` §8 open questions. Where they disagree with this doc, this doc is_
_the current view; where they go deeper on a point, they are cited, not repeated._

_Research/synthesis doc. It records the **decisions made this session** — the suite is three_
_tiers, not one command — and re-reads five prior-art systems (cloned to_
_`~/dev/agentic-sdlc-prior-art/`, read from source) through them. **This is the launch pad:** the_
_working plan `planning-suite-restructure-plan.md` (repo root, branch-scoped) carries the_
_execution order; the frozen implement-feature backlog is tracked in epic **#46**. The next step_
_is to evolve §1–§10 here into the durable design docs listed in §11._

---

## 0. What changed, and why a fourth document exists

Two of the prior docs analysed a **single command each** (implement-feature; a single-command
plan-feature). The external review's 12 points were, in aggregate, an attempt to grow
plan-feature *upward* into system-level thinking — its points 1, 2, 3, 7, 11 literally ask for
"system intent," "capabilities first," "lightweight architecture," "minimum coherent system,"
and a "decision horizon." That pressure is the signal that **one command was carrying two jobs.**

The decision this session splits them:

```
  /design-system   ──►   /plan-feature   ──►   /implement-feature
  (understand &          (decompose ONE        (build ONE node,
   model the system,      capability into a     tested + reviewed +
   DURABLY)               buildable DAG)        committed)
```

- **`/design-system`** — brainstorm → capabilities → lightweight architecture, written to a
  **durable, accumulating** substrate. New tier. **None of the three prior docs covered it.**
- **`/plan-feature`** — decompose one capability into an `A/B/C/Z` DAG of GitHub issues.
  The concept in `plan-feature.md`, re-scoped: it plans *a capability*, not "the system," and
  not "one feature in isolation."
- **`/implement-feature`** — unchanged in essence; field-leading on vertical depth already.

**Steering is the DAG, not a supervisor** (confirmed this session): decompose → build each
node → verify the whole at `Z`. No resident process. `plan-feature.md` D4 stands, with one
amendment (§5).

This doc's job is therefore net-new: analyse the **suite**, anchor each tier to the strongest
prior art, and fold the three prior analyses into one prioritised gap list.

---

## 1. The spine — a durable, capability-organized spec substrate

**This is the foundational decision the rest of the suite hangs on.** Everything else is shaped
by it.

Today nothing in sdlc-lite **accumulates**. implement-feature's handoff artifacts live in a
gitignored per-run dir; the plan-feature concept writes `docs/plans/<X>/`, a **per-feature
folder**. Feature #2 cannot see feature #1's contract; the human cannot diff a capability across
features; nothing compounds. `2026-09-20-agentic-sdlc-gap-analysis.md` flagged this as B3 ("worth
an explicit revisit") and the external review circled it (points 1, 6, 10) — but neither made it
structural.

**OpenSpec is the worked reference, and the suite should adopt its shape.** OpenSpec splits the
world in two:

```
project-root/
├── specs/                     ← SOURCE OF TRUTH: how the system behaves NOW,
│   ├── <capability-a>/spec.md    organized BY CAPABILITY, durable, in git
│   └── <capability-b>/spec.md
└── changes/                   ← in-flight modifications, each a folder of deltas
    └── <change>/                 (ADDED / MODIFIED / REMOVED requirements)
        └── specs/<cap>/spec.md   that MERGE BACK into specs/ on archive
```

The properties that matter for a 3-tier agentic suite:

1. **It accumulates.** "Specs grow organically as changes are archived… the accumulated spec is
   what makes the *next* change cheap." (OpenSpec) A capability spec built once is regressed
   against forever after.
2. **A spec is a behavior contract, not an implementation plan** — OpenSpec enforces the *same
   interface/internal wall* one tier up that implement-feature enforces internally. `spec.md` =
   observable behavior + scenarios (Given/When/Then); `design.md`/`tasks.md` = how. This is the
   natural home for the external review's "requirements vs design decisions" (point 4) and
   "assumptions as first-class" (point 5).
3. **Deltas, not rewrites.** A change touches a capability as ADDED/MODIFIED/REMOVED, reviewed
   as a diff, merged on archive. This maps *exactly* onto the suite's lifecycle:

   | OpenSpec | sdlc-lite suite |
   |---|---|
   | `specs/<cap>/spec.md` | the durable capability spec `/design-system` seeds |
   | a `changes/<change>/` folder | one `/plan-feature` run against a capability (the `feat/X` work) |
   | delta ADDED/MODIFIED/REMOVED | what X changes about the capability |
   | **archive → merge deltas into specs/** | **Z-green `feat/X` merges to `main`** (D8) |

   D8's `feat/X → main` merge *is* the archive step. The concept doc already invented the
   lifecycle; OpenSpec gives it a durable home.

4. **Dependencies are enablers, not gates.** OpenSpec's artifact graph (`proposal → specs →
   design → tasks`) is a DAG you can enter anywhere sensible — the same "fluid not rigid" posture
   the suite wants across its tiers (see §4, progressive rigor).

> **Decision (challenges `plan-feature.md`'s `docs/plans/<X>/`):** the durable output is
> **capability-organized `specs/`**, not per-feature folders. Per-run planner-private reasoning
> stays gitignored (`.plan-feature/<run>/`, D6) — that separation is right and unchanged. What
> changes is that the *product* of planning lands in an accumulating, capability-indexed store.

---

## 2. The three tiers, and the address that unifies them

| Tier | Owns | Primary durable output | Prior-art anchor |
|---|---|---|---|
| `/design-system` | intent → capabilities → lightweight architecture | **capability map** (stable ids + dep DAG) + per-capability `spec.md` | OpenSpec `specs/`; addy Phase-0 capability map; mattpocock CONTEXT-MAP |
| `/plan-feature` | decompose **one capability** into a buildable DAG | `A/B/C/Z` issues + a **locked inter-child seam contract**; a change/delta against the capability | mattpocock `to-tickets` (vertical tracer bullets + integrate-and-verify node = `Z`) |
| `/implement-feature` | build one node | tested, reviewed, committed code | the existing product |

### 2.1 The stable capability id is the suite's shared address (S2)

Every planning-tier tool in the field converges on a **capability map** as the primary
artifact — and on **stable ids** as the reason it works:

- **addy** (`spec-driven-development` Phase 0): a `| module id | responsibility | depends on |`
  table + build order. Ids are *"kebab-case, chosen once, never renamed mid-initiative. Specs,
  plans, and downstream commands **select work by these ids** instead of guessing which spec is
  active."* Dependency direction one-way, no cycles ("if two modules each need the other, they
  are one module").
- **mattpocock** (`domain-modeling`): a root `CONTEXT-MAP.md` when a repo has multiple bounded
  contexts, each pointing to where it lives.
- **superpowers** (`brainstorming`): *"if the request describes multiple independent subsystems…
  help the user decompose into sub-projects… each sub-project gets its own spec → plan →
  implementation cycle."*

The external review asked only for "a capabilities *section* — a numbered list." The field says
more: make it a **map with stable ids and a dependency DAG**, because the id is the thing every
tier addresses work by. `plan-feature.md` has **no cross-tier addressing scheme at all** — this
is what turns three commands into one system:

```
capability id: covenant-extraction     ← /design-system owns the spec
      │
      ├─ /plan-feature covenant-extraction  →  issues A,B,C,Z (a "change" against the capability)
      │        └─ each child issue names capability id + the AC(s) it serves
      │
      └─ /implement-feature <child>          →  code; commits reference the capability id
```

Traceability the suite can then answer mechanically (external review points 6, 9): *"which
issues deliver capability C?"* and *"which requirement is covered by no child?"*

---

## 3. Gaps in `/design-system` (the new tier)

**S1 — No durable substrate.** Covered in §1; it is the spine. *(Subsumes external points 1,3,6,10; research-doc B3.)*

**S2 — Capability map with stable ids as the load-bearing object.** Covered in §2.1. *(Subsumes external points 2,6,9.)*

**S3 — Behavior/implementation split at this tier.** A capability `spec.md` states observable
behavior + scenarios; the *how* stays out (OpenSpec's rule). Lift the interview-gate proposal's
already-drafted "assumptions (evidence-bearing)" block (§3.1) and "requirements vs decisions"
labelling up to this tier rather than reinventing them. *(Subsumes external points 4,5.)*

**S4 — No progressive rigor / no downgrade path, and three tiers triple the cost of that.** The
field universally ships an escape hatch: OpenSpec **lite vs full** spec; superpowers
**spike / bounded / architectural** with a *one-way ratchet* ("when in doubt take the heavier
path; nothing downgrades mid-task"); addy "when NOT to use"; GSD `/gsd-quick`. The suite as drawn
is heavyweight-only. Each tier needs a **documented, human-confirmed downgrade**:

- "this is one feature, not a system" → skip `/design-system`;
- "this capability is one node" → skip `/plan-feature`, go straight to implement-feature;
- and the existing smell-test (advisory-with-friction) is the *upgrade* direction of the same
  ratchet.

*(This is the research doc's Tier-D "no progressive rigor," amplified ×3.)*

---

## 4. Gaps in `/plan-feature` (decomposition tier)

**P1 — Vertical slices must be an enforced invariant, not a red-team preference.** The single
biggest decomposition-correctness risk, and every prior-art system names it:

- mattpocock `to-tickets`: *"each slice cuts a narrow but COMPLETE path through every layer
  (schema, API, UI, tests): vertical, NOT a horizontal slice of one layer… demoable or
  verifiable on its own."*
- addy `planning-and-task-breakdown`: the "bad (horizontal) vs good (vertical)" worked example,
  verbatim.
- the interview-gate proposal §2.4 already says it for implement-feature: *"Never split by
  technical layer… no slice of it is independently verifiable."*
- the external review's point 8: `database/API/LLM/UI` is a *bad* decomposition;
  `ingestion/extraction/evaluation` (capability-shaped) is good.

`plan-feature.md` describes children only abstractly ("interface, deps, acceptance, NFR slice")
and files semantic coherence under a red-team *option*. **Make "each A/B/C is an independently
demoable vertical slice of the capability" a Rule, and name horizontal/layer decomposition as a
refused anti-pattern.** The red-team then *verifies an invariant* rather than discovering a
philosophy.

The one principled exception is already in the field and already in the concept doc without
knowing it: mattpocock's **wide-refactor → expand/migrate/contract → "a final integrate-and-verify
ticket that every batch blocks"** *is* the concept doc's `Z` node. The convergence validates `Z`.

**P2 — The inter-child seam must be pinned (exact signatures) and locked BEFORE any child is
built. D5 under-weights this.** "Contract, not algorithm" (D5) protects algorithm-blindness one
level up — correct, keep it. But the *harder* failure it doesn't address: children A and B, built
in **isolated** implement-feature runs, independently invent **incompatible seams**, and `Z`
cannot integrate them. The field's fix:

- superpowers `writing-plans` gives every task an explicit `Interfaces: Consumes / Produces
  [exact function names, parameter and return types]` block — *because* each task's implementer
  sees only its own task (the same isolation the suite has between child runs).
- addy: *"Features that share an API contract — define the contract first, then parallelize."*

D5's template lists "interface" but does not make the **cross-child seam a frozen, planner-owned,
review-gated artifact.** This is where a wrong decomposition actually bites — and `Z` is where you
discover it, which is too late. **Elevate the inter-child interface contract to a first-class
locked output of `/plan-feature`, reviewed before issues are emitted.** (It is also the artifact
that makes D7 — "Z talks to seams, not guts" — actually true.)

**P3 — The red-team reviewer has the exact structural hole §4 of the implement-feature analysis
diagnosed, and the exact fix transfers.** The decomposition is the highest-leverage reasoning
step in `/plan-feature`, authored by the **interactive conductor** — unpinned model, no
independent critic. That is Gate 2 all over again (`agentic-sdlc-gap-analysis` §4.0). The concept
doc leaves the reviewer an open question ("one gate, or gaps + NFR split?"). The §4 answer
applies unchanged:

1. **Rubric before gate.** Give the reviewer something concrete to review against *first*:
   vertical-slice coherence (P1), inter-child seam compatibility (P2), NFR allocatability
   (allocate-or-verify-at-Z, else it's a decomposition smoke alarm — D3.3 already says this),
   and no internal-design leakage into child bodies (D6).
2. **Then make it a pinned-Opus isolated gate**, with the same contract shape as
   implement-feature's Gates 4/7.
3. **Framing (addy `doubt-driven-development`):** *"assume the author is overconfident… pass
   ARTIFACT + CONTRACT only, do NOT pass the CLAIM."* So the reviewer gets the requirements +
   capability spec + the draft decomposition — **not** the conductor's narration of why the
   decomposition is good. Add superpowers' **"declined to judge"** list so nothing is dropped
   silently. *(Answers concept-doc §8's "one gate or split" — start as one gate with this rubric;
   split only if dry runs show it overloaded.)*

**P4 — `Z` must be an auditable oracle tied to the capability spec.** "X done ≡ Z closed" is the
right done-signal (D3, keep). Make it stronger by binding it to the durable spec: GSD's Verify
checks *requirement coverage + decision coverage + goal alignment* (not just "tests pass");
OpenSpec `/opsx:verify` checks implementation-matches-spec. `Z` verifies the **capability's
behavior contract green, un-mocked** — which is also precisely what makes the archive/merge-back
(§1) meaningful: you merge a delta only when the capability spec it claims is proven.

---

## 5. Steering — the DAG plus one orientation artifact

The "DAG is the steer" decision is right and matches the field's rejection of resident
supervisors. But GSD shows the missing piece even in a stateless model: a **cheap orientation
layer**. GSD's `.planning/STATE.md` is *"the navigation layer… any agent or workflow that needs
to orient itself reads STATE.md first."* GitHub sub-issues + dependency edges are *queryable*, not
*readable-at-a-glance* — and integration happens weeks later, often in a fresh session that cannot
see "where are we / what's unblocked / what's next" without re-deriving it from the API.

> **Amendment to D4 (not a reversal):** `/plan-feature` emits, writes a durable
> `STATE.md`-style orientation file (or the capability map annotated with per-node status), and
> **exits**. The steer is a *file plus the DAG*, refreshed on demand — never a running process.
> If ever wanted, a stateless `/plan-status` that regenerates that file from the GitHub DAG is
> the entire feature; it holds no resident state, so it does not reopen the "living supervisor"
> door D4 correctly shut.

---

## 6. ADR reconsiderations (challenged where the evidence warrants)

| ADR / claim | Verdict | Why |
|---|---|---|
| §6 non-goals: "plans **one feature X** / not a roadmap tool" | **Rewrite** | Overruled this session; `/design-system` is the capability/roadmap tier. Left as-is, the doc contradicts the suite. |
| `docs/plans/<X>/` durable location | **Challenge** | Replace with capability-organized `specs/` that accumulate (§1). |
| D4 emits-and-exits | **Amend** | Keep exit; add the `STATE.md` orientation artifact (§5). |
| D5 contract-not-algorithm | **Strengthen** | Right in intent; add the locked inter-child seam (P2). |
| D10 recursion depth-cap 2–3 | **Reframe** | With a system tier, "a child is capability-sized" is not recursion — it is *wrong tier chosen*; the rule becomes "kick back up to `/design-system`," cleaner than 2–3-level GitHub-issue recursion. |
| D3 falsifiable done (one child green) | **Keep** | GSD Verify + OpenSpec verify validate it; P4 binds it to the capability spec. |
| D7 `Z` against seams · D9 human-gated re-plan | **Keep** | Field-universal; P2 makes D7 actually enforceable. |

---

## 7. Adjacent & suite-level gaps

- **The `feat/X → main` merge (D8) has no owning command.** This is the research doc's B2
  (finish-the-branch / `/ship`) surfacing *inside* plan-feature. superpowers makes it a whole
  skill: three-option menu, base-branch confirm, **test on the merged result**, "integration is
  the human's decision." The suite cannot complete X without it, and it is where the OpenSpec
  *archive/merge-back* (§1) physically happens.
- **`/fix-bug` (B1)** — still the cheapest missing sibling; more valuable once a durable
  capability spec exists to regress against (superpowers' red-green-**revert**-red proof).
- **No eval harness (C1)** — now *three* commands whose wording changes cannot be measured. The
  compounding gap; addy's three-tier model (structural / trigger-routing / behavioral) is the
  reference. Everything above gets cheaper to land once change is measurable.
- **Building this suite RESOLVES A8** — "the feature is the unit of work; there is no
  decomposition step," the single biggest item in the implement-feature analysis. Worth stating
  plainly: the planning suite's *existence* closes A8, and per-node isolation resolves A9
  (batch-TDD) at the node level.

---

## 8. Falsifiable acceptance (per tier — "done ≠ the skill exists")

- **`/design-system`:** on a toy multi-capability request → a committed capability map (stable
  ids + dep DAG) + at least one durable `specs/<cap>/spec.md`; a **second** run adds a delta that
  merges cleanly (proves accumulation, §1).
- **`/plan-feature`:** the existing acceptance in `plan-feature.md` §7, plus: the red-team catches
  a **seeded horizontal decomposition** (P1) and a **seeded incompatible sibling seam** (P2). If
  it passes either, the gate is theatre.
- **`/implement-feature`:** unchanged.
- **Suite:** one threaded path — `/design-system` → pick a capability → `/plan-feature` → drive
  one child to green on `feat/X` → `Z` → merge/archive back into `specs/<cap>/`.

---

## 9. Recommended sequence

Ordered so each step de-risks the next; the spine first because everything addresses it.

1. **Decide the durable substrate (§1) and the capability-id scheme (§2.1).** Everything hangs
   here. Nothing else is worth building until the address exists.
2. **`/design-system` v1:** capability map + one durable `spec.md`, delta-on-archive lifecycle.
   Lift S3's assumption/decision blocks from the interview-gate proposal.
3. **Write doc (5) `/plan-feature`** (absorbing + re-scoping `plan-feature.md`, which is then
   deleted): drop §6 non-goals, add P1 (vertical-slice Rule) and P2 (locked inter-child seam) to
   the contract template, reframe D10, amend D4 (§5).
4. **`/plan-feature` red-team (P3):** rubric first, then a pinned-Opus isolated gate.
5. **`/ship` / finish-the-branch (§7)** — owns D8's merge = OpenSpec's archive.
6. **Progressive-rigor downgrades (S4)** across all three tiers.
7. **Eval harness (C1)** — do it earlier than instinct says; it makes 1–6 measurable.
8. **`/fix-bug`** — cheapest new sibling, once specs are durable.

---

## 10. Execution model & the "real seams" principle

- **Prioritization.** `/implement-feature` is **frozen** on the suite branch (its quality backlog
  parked in epic **#46**); focus is `/design-system` → `/plan-feature`; return to that backlog
  only after **both** new tiers are built + dry-run green. Bugs, if any, are fixed on separate
  branches — never here.
- **Interleave, branch-per-tier** (dogfoods D8, "each tier is a shippable unit on its own
  branch"): this branch delivers the durable docs (§11.A) + cleanup → `main`; `feat/design-system`
  builds design-system (expect **one revision pass** on the suite architecture here —
  architecture is a hypothesis, external review point 12); `feat/plan-feature` finalizes and
  builds plan-feature.
- **PRINCIPLE — "design against real seams, not imagined ones."** Design a downstream command's
  **stable core** now; keep its **cross-tier interface PROVISIONAL** until the upstream tier is
  built and its real output shape exists. Applied to `/plan-feature`: stable core (P1, red-team,
  D3/D7/D8/D9, `Z`) now; the child-contract template that *consumes a capability spec* and the
  **P2** inter-child seam stay provisional → two issues (**A** = core, **B** = cross-tier
  interface, *blocked-by* design-system-built).
- **"Build" = skill-authoring** — `SKILL.md` + `agents/*.md` + templates + `guard.py` + a toy
  fixture + a **green dev-container dry run**, the same bar as implement-feature.
  `/implement-feature` **cannot** build these (it builds python; these are markdown/skill
  artifacts).

---

## 11. Artifacts — what will be created (the clarity check)

### A. Durable design docs (this restructure produces these; they supersede the research)
| Doc | Tier | Owns | Origin |
|---|---|---|---|
| **(3)** suite architecture | all | the spine (§1), capability-id addressing (§2.1), inter-tier handoff contracts, progressive-rigor policy (S4), the "real seams" principle (§10), per-tier acceptance (§8) | **evolved from THIS doc** |
| **(4)** `/design-system` | design-system | requirements + high-level design of the tier internals | new, this branch |
| **(5)** `/plan-feature` | plan-feature | requirements + high-level design; **stable core now**, provisional cross-tier parts flagged | new, this branch (finalized on `feat/plan-feature`) |
| — | implement-feature | **no new doc** — design stays in `developer-guide.md` + ADRs; pending changes tracked in **#46** | — |

### B. Runtime artifacts the SUITE produces (product), by tier
- **`/design-system` →** a durable, capability-organized **`specs/`** store: the **capability
  map** (stable ids + dependency DAG) + per-capability **`spec.md`** (behavior contract +
  scenarios + assumptions/decisions). Each later change is a **delta** (ADDED/MODIFIED/REMOVED)
  merged back on archive.
- **`/plan-feature` →** per capability change: **`A/B/C` child issues** (each a contract:
  capability id + interface + deps + acceptance + NFR slice), the terminal **`Z`**
  integrate-and-verify issue, the **locked inter-child seam contract**, the **`feat/X` branch**, a
  **`STATE.md`** orientation file, and gitignored planner-private **`.plan-feature/<run>/`**.
- **`/implement-feature` →** tested, reviewed, committed code per node. **`Z`** merges `feat/X` →
  `main` = the OpenSpec **archive** of the delta into `specs/<cap>/`.

### C. Build/support artifacts (per tier, at build time)
- A "deliberately-decomposable" **toy fixture** (mirrors `toy-greet-plugin`) as the dry-run subject.
- **`agents/*.md`** for any pinned reviewer (e.g. the plan-feature red-team) + matching
  **`guard.py`** isolation rules.
- The **dev-container dry run** as the falsifiable acceptance harness (§8).

### D. This-branch cleanup artifacts (already partly done)
- `docs/research/` now holds the frozen material (gap-analysis, two gate proposals, external
  analysis). Epic **#46** tracks it. Still to do on this branch: absorb `plan-feature.md` into
  (5)-stable-core then delete it; `#32` reconciliation (re-scope + a `/design-system` issue);
  `git rm planning-suite-restructure-plan.md` in the finishing commit.

---

## Sources

- Prior art, read from source (cloned to `~/dev/agentic-sdlc-prior-art/`):
  [OpenSpec](https://github.com/Fission-AI/OpenSpec) ·
  [superpowers](https://github.com/obra/superpowers) ·
  [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) ·
  [mattpocock/skills](https://github.com/mattpocock/skills) ·
  [gsd-core](https://github.com/open-gsd/gsd-core)
- In-repo, reconciled by this doc (now under `docs/research/`):
  `2026-09-20-agentic-sdlc-gap-analysis.md`, `2026-09-20-design-review-gate-proposal.md`,
  `2026-09-20-interview-gate-proposal.md`, `2026-09-17-plan-feature-analysis-external.md`;
  plus `docs/design/plan-feature.md` (still active — absorbed into (5)).
