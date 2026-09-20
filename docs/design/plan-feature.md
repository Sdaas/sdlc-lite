# `/plan-feature` — requirements & high-level design

> **Status:** durable design, but a **hypothesis** — one revision pass expected after the tier is
> built to a green dry run (architecture-as-hypothesis).
> **Scope:** this doc owns the **internals** of the `/plan-feature` tier — its purpose, its
> decomposition philosophy, the `A/B/C/Z` DAG mechanics, the child contract, the red-team gate, the
> re-plan feedback loop, and this tier's acceptance. The **spine** it plugs into (the durable
> `specs/` substrate, the stable capability-id address, the inter-tier handoff contracts, the
> steering model, progressive-rigor policy, shared invariants, suite acceptance) lives in
> `planning-suite-architecture.md` and is **not** re-specified here — only referenced.
> **Stable-core note:** `/plan-feature`'s upstream is `/design-system`, so parts of this design
> **consume `/design-system`'s real output** (a capability `spec.md`). Per the suite's "design
> against real seams" principle (spine §7), those parts are marked
> **`PROVISIONAL — finalize against real /design-system output`** and locked only after
> `/design-system` is built; everything else is **stable core**, designed now. §9 lists exactly
> what is deferred.

---

## 1. Purpose & role

`/plan-feature` is the tier that **decomposes one capability into a buildable DAG** — a set of
implementation slices that each `/implement-feature` can build in isolation, plus a terminal node
that integrates and verifies the whole. Its deliverable is **a plan, not code**.

```
  /design-system   ──►   /plan-feature   ──►   /implement-feature
  (capabilities +        (THIS doc: ONE        (build ONE node:
   durable specs)         capability →          tested + reviewed +
                          A/B/C/Z DAG)          committed code)
```

It sits **downstream** of `/design-system` (it selects one capability by its stable id and reads
that capability's `spec.md` — spine seam A) and **upstream** of `/implement-feature` (it emits
child issues, each a valid `/implement-feature` input — spine seam B). It emits the DAG and
**exits**; it is never a resident supervisor.

**Not a "large-feature splitter."** Decomposition is only valuable if the thing being decomposed is
*already understood* — and that understanding lives one tier up, in `/design-system`. So
`/plan-feature`'s job is narrow and sharp: given a capability that is *already* modelled (a behavior
contract + scenarios), find the **natural implementation seams** that collectively deliver it. The
uncertainty it resolves is *"what are the right pieces and how do they connect?"*, not *"what is
this system?"*.

**When NOT to use it (the downgrade).** Per the suite's progressive-rigor ratchet
(`planning-suite-architecture.md` §6) and §7 below, if a capability is genuinely **one buildable
node** the human confirms *"this capability is one node"* and goes straight to
`/implement-feature`. `/plan-feature` earns its cost only when a capability must be split — when we
cannot yet confidently name the child work items *and* the work can be split into confidently-small
pieces — raw size is merely the usual cause, not the trigger.

---

## 2. What it produces (tier outputs)

One `/plan-feature` run is a **change against a capability** in the spine's `specs/`/`changes/`
substrate (`planning-suite-architecture.md` §2) — the `changes/<change>/` folder that merges back
into `specs/<cap>/` on archive (= the Z-green `feat/X` → `main` merge, spine seam C). Concretely it
emits:

| Output | What it is | Consumed by |
|---|---|---|
| **the change deltas** | ADDED / MODIFIED / REMOVED against the capability's `spec.md` | reviewed as a diff; merged into `specs/` on archive |
| **the `A/B/C/Z` DAG** | GitHub sub-issues (composition) + dependency edges (ordering), sink node `Z` | the human; `/implement-feature` (one child at a time) |
| **child contracts** | one structured **contract, not algorithm** per child (§3.3) — *`PROVISIONAL` template* | `/implement-feature` (spine seam B) |
| **the locked inter-child seam(s)** | the frozen cross-child interface siblings share (§3.4, **P2**) — *`PROVISIONAL` format* | children A/B/… and `Z` |
| **capability→requirement→child→test traceability** | the coverage matrix, one semantic level richer than before (§5) | the red-team gate; the human; `Z` |
| **a `STATE.md`-style orientation file** | the capability map annotated with per-node status (spine §5) | the human, weeks later, in a fresh session |

Planner-private reasoning (how the planner *thought about* the children's internals) stays
gitignored in `.plan-feature/<run>/` and **never** ships into a child issue (see §4). Durable
artifacts are synthesized aggressively and kept small — the same posture `/design-system` takes.

---

## 3. The pipeline (interactive conductor → the DAG)

`/plan-feature` mirrors the suite's declarative pattern — a `SKILL.md` score, pinned-model
agent-defs for the non-interactive gates, and the shared guard hook; no hand-written orchestration
(shared invariant, spine §8). The conductor is **human-interactive** (decomposition is a design
conversation), so it runs interactively on the strong model and **warns on a weaker one**; only the
non-interactive red-team gate (§4) runs as an isolated pinned subagent — a subagent cannot
interview the human.

```
  select capability ─► decompose into slices ─► lock inter-child seams ─► red-team ─► emit DAG + STATE ─► exit
   (seam A inbox)       (§3.2, P1)               (§3.4, P2 · PROV)        (§4)        (§3.1)
```

### 3.1 The shape: a DAG with a sink node, not a running loop

Integration of a decomposed capability realistically happens *weeks* after its parts are built. A
resident supervisor cannot wait that long, and a half-complete "living document" is exactly the
partial state the suite avoids. So the work is tracked **entirely as a DAG of GitHub issues** and
`/plan-feature` **exits forever** after emitting it — steering is the DAG, owned by the spine
(`planning-suite-architecture.md` §5).

```
          plan X  ──►  build A ┐
 (plan-feature)        build B ├──►  Z: integrate + verify X  ──►  merge feat/X to main
                       build C ┘      (another /implement-feature run)   (= archive the change)
```

- Composition (`X` is made of `A,B,C,Z`) → GitHub **sub-issues**; ordering (`Z` blocked by
  `A,B,C`) → GitHub **issue dependencies**; **"X is done" ≡ "Z is closed."**
- **The one addition** to a purely stateless model is the durable
  `STATE.md`-style orientation file (§2) — a *file plus the DAG*, refreshed on demand, never a
  running process. The spine (§5) owns this decision; this tier merely *emits* the file and exits. A
  future stateless `/plan-status` that regenerates it from the GitHub DAG holds no resident state,
  so it does not reopen the "living supervisor" door.

### 3.2 Decomposition philosophy — vertical slices, not technical layers (Rule P1)

> **Rule P1 (vertical-slice invariant).** Children are **capability-coherent vertical slices**,
> never horizontal technical layers. A decomposition can have perfect requirement coverage and
> still be architecturally wrong.

Splitting a capability into `database / API / LLM / UI` is technically convenient but produces
children that are not independently buildable or verifiable — every one is dead until the others
land, and `Z` becomes the only real integration point for *everything*. The right seams follow the
capability's own behavior: e.g. for a covenant-extraction capability, `identify clauses →
normalize covenants → extract facts → evaluate conditions`, each a slice that does a real, testable
piece of the behavior end to end. This is the vertical tracer-bullet idea (credit: mattpocock)
applied inside a single capability, and it is exactly what the red-team gate (§4) exists to
enforce.

### 3.3 What each child carries — a contract, never an algorithm

To decompose a capability, the planner reasons about the children's **internals and their
interactions**. But `/implement-feature`'s central invariant is the interface/internal design split
that keeps its test-writer *algorithm-blind*. If a child issue carried the planner's internal-design
reasoning, the child's test-writer would read it and **algorithm-blindness would break one tier up**
(spine §4, seam B; §8).

So a child renders from a **structured contract template** — no free-form "design notes" field —
carrying *what*, never *how*:

- **capability served** — the stable capability id + the acceptance criteria this child delivers
  (a capability-aware contract gives the implementer a *reason* for the work without leaking
  strategy);
- **interface** — inputs, outputs, and the **inter-sibling seam** it consumes/produces (§3.4);
- **dependencies** — which siblings must exist first (the ordering edges);
- **acceptance** — the child's slice of the requirement→test matrix;
- **NFR slice** — its allocated share of the non-functional budget (§3.5).

The contract is deliberately the **middle path**: shipping the *full* internal design (and letting
`/implement-feature` skip its own design gate) would defeat algorithm-blindness and the double-model
review; shipping only a one-liner would throw the planning work away and force a full re-interview.
The structured contract carries exactly what the implementer needs — *what*, not *how* — and nothing
more.

**`PROVISIONAL — finalize against real /design-system output`:** the *exact field set and rendering*
of this template consumes a capability `spec.md`'s real shape (what a scenario/behavior contract
actually looks like coming out of `/design-system`). The **principle** (contract-not-algorithm,
capability-aware) is stable core and fixed now; the **template mechanics** lock only against a real
spec (§9).

### 3.4 The inter-child seam is a locked, planner-owned artifact (Rule P2)

Children A and B are built in **isolated** `/implement-feature` runs. If each independently invents
an incompatible seam, `Z` cannot integrate them. So:

> **Rule P2 (locked inter-child seam).** The exact cross-child interface — signatures:
> consumes/produces, parameter and return types — is **frozen and review-gated before any issue is
> emitted.** It is the artifact that makes "`Z` talks to seams, not guts" (§3.6) actually true.

The spine (§4) fixes that this seam *must* be a locked output; the **precise seam format** is a
`/plan-feature` internal and is **`PROVISIONAL — finalize against real /design-system output`**
(§9), because a good seam vocabulary depends on the shape of real capability specs.

### 3.5 Non-functional requirements decompose too

NFRs (security, performance, scale, resilience, constraints) are cross-cutting and often only
violable at integration. The planner **allocates what's allocatable** into child contracts —
a concrete, testable slice where one exists (a latency budget: "A owns ≤ 50 ms of the 200 ms p99";
encryption-at-rest; an input-validation obligation) — and **verifies the remainder at `Z`** (a
genuinely global property like an end-to-end erasure SLA). An NFR that can be neither allocated *nor*
verified is a **decomposition smoke alarm** — a signal the seams are wrong, surfaced to the red-team
gate (§4).

### 3.6 The integrate-and-verify node `Z`

`Z` is **just another `/implement-feature` run** — its "feature" is *"write the glue between A/B/C
and make X's named end-to-end tests green."* Its inbox is the **public interfaces** of A/B/C (the
locked seams, §3.4) plus X's end-to-end test plan and the traceability matrix; it stays
**algorithm-blind** about each child's internals, which is fine because **glue talks to seams, not
guts**. Its definition of done is the matrix all-green, **un-mocked** (the repo's VERIFY invariant,
spine §8) — which is precisely what makes the archive/merge-back meaningful: the change's deltas
merge into `specs/` only when the capability they claim is proven. If `Z` *can't* be written against
seams alone, that is itself a signal the decomposition was wrong (a smoke alarm, not a reason to
break isolation).

### 3.7 Branching: `feat/X` is the shippable unit, not the child

A child is usually **not independently shippable** — `A` may be dead code until `B` and `Z`
integrate it. So children must not merge to `main` individually (that pollutes `main` with partial
work, and a re-plan means reverting already-public commits). Instead `/plan-feature` creates a
**per-change integration branch `feat/X`**; each child branches off `feat/X` and PRs back into it;
`Z` integrates and verifies on `feat/X`; **only a Z-green, matrix-passing `feat/X` merges to
`main`** — which *is* the spine's archive/merge-back of the change into `specs/` (seam C). A wrong
decomposition discovered at `Z` is contained to `feat/X`; `main` never saw it. Drift is mitigated by
periodic `main → feat/X` merges.

> **Required change to `/implement-feature`:** its base branch must be a **parameter** (default
> `main`; `feat/X` when invoked on a child), not a hardcoded assumption. Tracked as a change to the
> existing tier (epic #46 / the reconcile issues, §8).

---

## 4. The red-team review gate (non-interactive, isolated)

Before any issue is emitted, an **isolated pinned subagent** attacks the plan — the one bias-
sensitive gate that *can* be a subagent (it does not talk to the human). Its rubric applies the
design-review red-team discipline (credited in Sources):

- **Gaps / overlaps** — does every requirement map to some child, with no orphan requirement and no
  two children owning the same behavior? (traceability, §5)
- **Semantic coherence of the decomposition** — are the children **natural seams of the
  capability** (vertical slices, P1) or merely convenient technical layers/files? A decomposition
  with perfect coverage but layer-shaped children **fails** this check.
- **Seam compatibility** — do the locked inter-child seams (P2) actually compose? Can `Z` be
  written against seams alone (§3.6)?
- **Internal-design leakage** — does any child contract smuggle in *how* (a leaked algorithm)
  rather than *what*? This is a **semantic** judgment — a file-path guard hook genuinely cannot
  decide "contract vs leaked algorithm," so the no-leak invariant is **construction-enforced +
  review-gated, not hook-enforced**. Planner-private reasoning stays gitignored
  (`.plan-feature/<run>/`).

The gate is **falsifiable**: it must catch a **seeded horizontal decomposition** and a **seeded
incompatible sibling seam** (spine §9). If it passes either seeded defect, the gate is theatre.

---

## 5. Traceability: capability → requirement → child → test

The requirement→test matrix survives, extended one semantic level so the DAG is more than a bag of
tickets — it becomes a concrete implementation of the capability model:

```
capability id  ─►  requirement  ─►  child issue  ─►  acceptance test
```

This lets the planner (and the human, and the red-team) answer mechanically: *"which children
collectively deliver capability C?"* and *"which requirement is covered by no child?"* — the
traceability-by-construction the spine promises via the shared capability id (spine §3).

This matrix is also the tier's **falsifiable "done"**: the plan is done when **each child is a
valid `/implement-feature` input** *and* **the children cover the capability's
enumerated requirements with no orphan** — proven by dry-running one representative child to green
(§8). This repo's culture rejects "done = docs exist"; the matrix + one green child is the plan's
green-dry-run analog.

---

## 6. When reality contradicts the plan — the feedback loop

The plan is a **hypothesis; implementation is the test.** A child run may reveal the decomposition
was wrong — a smoke alarm fires (§3.5/§3.6), a child turns out infeasible, or building one exposes a
missing piece. This is a **first-class, explicit outcome**: the child run writes a
*decomposition-defect* note back onto X's issue and **stops**; the **human** decides whether to
re-enter `/plan-feature` (or kick up to `/design-system`). Re-planning is **human-gated, never
automatic** (honoring "surface to the human on no progress," spine §8).

The feedback **vocabulary is broad** so the note names *which layer* was wrong — because the fix
differs:

- **requirements** wrong → the capability spec is wrong → re-enter `/design-system`;
- **architecture / capability boundaries** wrong (a "capability" isn't actually isolable, or two
  are entangled) → re-enter `/design-system` (spine revision — the architecture is a hypothesis
  too);
- **decomposition** wrong (right capability, wrong seams) → re-enter `/plan-feature`.

Naming the layer is what keeps re-planning cheap and honest instead of a vague "it didn't work."

---

## 7. Progressive rigor & wrong-tier routing

Per the spine's one-way ratchet (`planning-suite-architecture.md` §6), `/plan-feature` routes to the
right tier rather than forcing every capability through decomposition:

- **Down (skip):** a capability that is genuinely **one buildable node** → human confirms → straight
  to `/implement-feature` (no DAG). If the plan collapses to a single issue, no harm — it feeds
  `/implement-feature` as usual.
- **Up (kick-up):** a "capability" that turns out to be **a whole system** (multiple capabilities
  hiding inside one) → surface it and recommend `/design-system`, routing the too-big case to the
  correct tier rather than recursing into an ever-deeper sub-DAG. The three-tier split makes *up*
  the natural move: it bounds what would otherwise be unbounded self-recursion by handing the
  too-big case to the upstream tier.
- **Bounded recursion within the tier:** a large *child* may itself re-enter `/plan-feature`
  (a sub-DAG), but depth is **capped** and the cap **surfaces to the human** (v1 fails safe at
  depth 1; deeper is a tracked follow-up), honoring "bound every automated loop."

The ratchet is one-way: when in doubt take the heavier path; **nothing downgrades mid-run.**

---

## 8. Falsifiable acceptance (tier-internal)

The suite-level threaded path is in the spine (§9); this tier's own bar — *"done ≠ the skill
exists"* — is:

> In the dev container, `/plan-feature` takes a **deliberately-decomposable toy capability** (from a
> `/design-system` spec) → produces the change deltas + the capability→requirement→child→test
> matrix → creates a **real GitHub sub-issue DAG `{A, B, C, Z}`** with dependency edges → the
> red-team **catches a seeded horizontal decomposition and a seeded incompatible seam** → and **at
> least one child is driven through `/implement-feature` to green on the `feat/X` branch.**

That single threaded path exercises every seam — contract handoff, locked inter-child seam,
base-branch parameter, red-team, and `Z`'s existence — without implementing the whole capability.
"Build" means skill-authoring to that green dry run (`SKILL.md` + `agents/*.md` + the child-contract
+ seam templates + `guard.py` rules + a purpose-built *"deliberately-decomposable"* toy fixture),
the same bar as `/implement-feature` (spine §7). Expect **one revision pass on
`planning-suite-architecture.md`** and on this doc's provisional parts (§9) during the build.

**GitHub reconcile:** the suite's only GitHub record today is **#32** ("Add /plan-feature",
backlog). Do not close it until replacements exist. When this tier's build starts, split it into
**Issue A — `/plan-feature` core** (this doc's stable core) and **Issue B — cross-tier interface
(provisional)**, the latter **blocked-by** `/design-system` being built (§9). The base-branch
parameter change to `/implement-feature` is tracked alongside (epic #46).

---

## 9. Provisional cross-tier interface (what is deferred, and why)

Per "design against real seams, not imagined ones" (spine §7), these parts consume
`/design-system`'s real output (a capability `spec.md`) and are **`PROVISIONAL — finalize against
real /design-system output`** — locked only after `/design-system` is built, tracked as the
blocked **Issue B** (§8), never finalized against an imagined output shape:

| Provisional part | Why it must wait | Where drafted |
|---|---|---|
| the **child-contract template** field set + rendering | consumes a real capability `spec.md`'s scenario/behavior shape | §3.3 |
| the **inter-child seam format** (P2) | a good seam vocabulary depends on real spec shape | §3.4 |
| the **seam A inbox** — how `/plan-feature` reads a capability spec | reads `/design-system`'s real artifact | §1, spine §4 |

**Stable core (designed now, not provisional):** the decomposition philosophy + vertical-slice Rule
P1 (§3.2); the DAG-with-sink + `STATE.md` model (§3.1); the contract-not-algorithm *principle* (§3.3);
the locked-seam *requirement* P2 (§3.4); NFR allocation (§3.5); the `Z` model (§3.6); `feat/X`
branching (§3.7); the red-team rubric (§4); traceability + falsifiable done (§5); the re-plan
feedback loop (§6); progressive rigor + wrong-tier routing (§7); the acceptance bar (§8).

---

## Sources & credit

- **External `/plan-feature` review** (`docs/research/2026-09-17-plan-feature-analysis-external.md`)
  — the four decomposition-tier points this doc owns: capability→requirement→child→test
  traceability (pt 6, §5), decomposition semantic-coherence / natural-seams check (pt 8, §3.2/§4),
  capability-aware contracts (pt 9, §3.3), implementation-as-architectural-feedback with a broadened
  re-plan vocabulary (pt 12, §6). The review's system-level points (1, 2, 3, 5, 7, 10, 11) grew the
  *upstream* tier and are owned by `design-system.md`.
- **Design-review-gate proposal** (`docs/research/2026-09-20-design-review-gate-proposal.md`) — the
  red-team rubric (§4), lifted from the implement-feature tier to the decomposition level (epic
  #46).
- **OpenSpec** — the change/delta/archive lifecycle a run implements (§2, spine §2).
- **mattpocock/skills** — vertical tracer-bullet slices (Rule P1, §3.2) and the integrate-and-verify
  node `Z` (§3.6).
- **superpowers** — explicit `Consumes / Produces` seam signatures (P2, §3.4) and
  finish-the-branch as its own step (the `feat/X` archive/merge-back, §3.7).
- **gsd-core** — `STATE.md` as the cheap orientation layer (§3.1) and Verify checking
  requirement/decision coverage, not just "tests pass" (§3.6, §5).

_Out of scope for this doc (owned elsewhere): the `specs/`/`changes/` substrate mechanics, the
capability-id addressing rules, the inter-tier handoff contract table, the steering model, the
progressive-rigor policy, and the shared invariants → `planning-suite-architecture.md`; the
system-intent + capability modelling that produces a capability spec → `design-system.md`._
