# The sdlc-lite planning suite — architecture

> **Status:** durable design, but a **hypothesis** — not frozen. One revision pass is expected
> after `/design-system` is built and a real capability spec exists (architecture-as-hypothesis).
> **Scope:** this doc owns the **spine** shared by all three tiers — the durable substrate, the
> capability-id address, the inter-tier handoff contracts, the progressive-rigor policy, the
> "real seams" execution principle, and per-tier falsifiable acceptance. It does **not** own any
> tier's internals; those live in the per-tier docs (`design-system.md`, `plan-feature.md`).
> Where the research under `docs/research/` goes deeper on evidence or prior-art comparison, it is
> cited in Sources, not repeated here.

---

## 1. What the suite is

sdlc-lite is an **opinionated agentic SDLC suite of planning tools** — three commands that hand
off to each other along one shared address:

```
  /design-system   ──►   /plan-feature   ──►   /implement-feature
  (understand & model     (decompose ONE        (build ONE node:
   the system into         capability into a     tested + reviewed +
   capabilities,           buildable A/B/C/Z     committed code)
   DURABLY)                DAG)
```

- **`/design-system`** — brainstorm → capabilities → lightweight architecture, written to a
  **durable, accumulating** substrate. The newest tier; internals in `design-system.md`.
- **`/plan-feature`** — decompose **one capability** into an `A/B/C/Z` DAG of GitHub issues, each
  a valid `/implement-feature` input. Internals in `plan-feature.md`.
- **`/implement-feature`** — build one node to tested, reviewed, committed code. Unchanged in
  essence; its design lives in `developer-guide.md` + its ADRs.

The tiers are separate commands, not one command that detects scope and branches internally:
decomposition (produces *issues*, human-reviewed, maybe never built) and implementation (produces
*committed code*) have different inboxes, done-bars, models, and review cultures. The three are
made into one **system** — rather than three adjacent commands — by the four spine elements below:
the substrate (§2), the address (§3), the handoff contracts (§4), and the shared invariants (§8).

---

## 2. The spine — a durable, capability-organized spec substrate

**This is the foundational decision the rest of the suite hangs on.** The substrate must
*accumulate*. A gitignored per-run handoff dir (as `/implement-feature` uses) or a **per-feature**
`docs/plans/<X>/` folder would leave feature #2 unable to see feature #1's contract — nothing
compounds, and every change starts cold.

So the suite adopts **OpenSpec's shape**: split the world into a durable source-of-truth organized
**by capability**, and in-flight **changes** that merge back into it.

```
project-root/
├── specs/                     ← SOURCE OF TRUTH: how the system behaves NOW,
│   ├── <capability-a>/spec.md    organized BY CAPABILITY, durable, in git
│   └── <capability-b>/spec.md
└── changes/                   ← in-flight modifications, each a folder of deltas
    └── <change>/                 (ADDED / MODIFIED / REMOVED requirements)
        └── specs/<cap>/spec.md   that MERGE BACK into specs/ on archive
```

Four properties make this the right substrate for a three-tier agentic suite:

1. **It accumulates.** A capability spec built once is regressed against forever after; the
   accumulated spec is what makes the *next* change cheap.
2. **A spec is a behavior contract, not an implementation plan.** `spec.md` states observable
   behavior + scenarios (Given/When/Then); the *how* stays out. This is the same
   interface/internal wall `/implement-feature` enforces internally, lifted one tier up, and the
   natural home for "requirements vs design decisions" and "assumptions as first-class."
3. **Deltas, not rewrites.** A change touches a capability as ADDED / MODIFIED / REMOVED, is
   reviewed as a diff, and is merged on archive.
4. **Dependencies are enablers, not gates.** The artifact graph is a DAG you can enter anywhere
   sensible — the "fluid, not rigid" posture the suite wants across its tiers.

The delta lifecycle maps exactly onto the suite:

| OpenSpec | sdlc-lite suite |
|---|---|
| `specs/<cap>/spec.md` | the durable capability spec `/design-system` seeds |
| a `changes/<change>/` folder | one `/plan-feature` run against a capability (the `feat/X` work) |
| delta ADDED / MODIFIED / REMOVED | what change X changes about the capability |
| **archive → merge deltas into `specs/`** | **Z-green `feat/X` merges to `main`** |

> **Decision:** the durable output is **capability-organized `specs/`**, not per-feature folders.
> Per-run planner-private reasoning stays gitignored (`.plan-feature/<run>/`). The *product* of
> planning lands in an accumulating, capability-indexed store.

---

## 3. The shared address — the stable capability id

Every tier addresses work by the **stable capability id**: a **kebab-case identifier, chosen once
and never renamed mid-initiative.** It is what turns three commands into one system.

```
capability id: covenant-extraction        ← /design-system owns the spec
      │
      ├─ /plan-feature covenant-extraction →  issues A,B,C,Z (a "change" against the capability)
      │        └─ each child issue names the capability id + the acceptance criteria it serves
      │
      └─ /implement-feature <child>         →  code; commits reference the capability id
```

Rules for the address:

- **Chosen once, never renamed.** Specs, plans, and downstream commands **select work by these
  ids** rather than guessing which spec is active.
- **The capability map is the load-bearing object**, not just a numbered list: a
  `| capability id | responsibility | depends on |` table plus a **dependency DAG**.
- **Dependency direction is one-way; no cycles.** If two capabilities each need the other, they
  are one capability.

Because every artifact carries the id, the suite can answer mechanically: *"which issues deliver
capability C?"* and *"which requirement is covered by no child?"* — traceability by construction.

---

## 4. Inter-tier handoff contracts (the seams between tiers)

Each tier reads a defined inbox and writes a defined outbox; a downstream tier never reads an
upstream tier's raw transcript. The seams:

| Seam | Producer → Consumer | The contract passed |
|---|---|---|
| **A.** system → plan | `/design-system` → `/plan-feature` | a **capability `spec.md`** (behavior contract + scenarios + assumptions/decisions) selected by its **stable id**, plus its place in the capability DAG |
| **B.** plan → build | `/plan-feature` → `/implement-feature` | a **child issue = a contract, never an algorithm**: capability id + interface (inputs/outputs/**inter-sibling seam**) + dependencies + acceptance + its NFR slice — and the **locked inter-child seam contract** siblings share |
| **C.** build → system | `/implement-feature` (at `Z`) → `specs/` | the **archive/merge-back**: a Z-green, matrix-passing `feat/X` merges to `main`, folding the change's deltas into `specs/<cap>/` |

Two contract rules are load-bearing across seams:

- **Contract, not algorithm (seam B).** A child issue carries *what*, never *how*. If a child
  carried the planner's internal-design reasoning, `/implement-feature`'s algorithm-blind
  test-writer would read it and blindness would break one tier up. This is enforced by
  construction (child issues render only from the structured contract) and by a review gate — not
  by a file-path hook, because "contract vs leaked algorithm" is a *semantic* judgment.
- **The inter-child seam is a first-class, planner-owned, locked artifact.** Children A and B are
  built in **isolated** `/implement-feature` runs; if each independently invents an incompatible
  seam, `Z` cannot integrate them. So the exact cross-child interface (signatures:
  consumes/produces, parameter and return types) is **frozen and review-gated before any issue is
  emitted** — this is the artifact that makes "`Z` talks to seams, not guts" actually true. The
  precise template is a `/plan-feature` internal, finalized against real capability specs; this
  doc only fixes that the seam *must* be a locked output.

---

## 5. Steering — the DAG plus one orientation artifact

**The steer is the DAG, not a resident supervisor.** Decompose → build each node → verify the
whole at `Z`; no process stays running. Composition (`X` is made of `A,B,C,Z`) is GitHub
sub-issues; ordering (`Z` blocked by `A,B,C`) is GitHub issue dependencies; **"X is done" ≡ "Z is
closed."** GitHub is the DAG substrate in v1.

The one addition to a purely stateless model is a **cheap orientation layer**: GitHub sub-issues +
dependency edges are *queryable* but not *readable-at-a-glance*, and integration often happens
weeks later in a fresh session. So `/plan-feature` emits a durable **`STATE.md`-style orientation
file** (the capability map annotated with per-node status) and **exits**. The steer is a *file plus
the DAG*, refreshed on demand — never a running process. A future stateless `/plan-status` that
regenerates that file from the GitHub DAG would hold no resident state, so it does not reopen the
"living supervisor" door.

---

## 6. Progressive rigor — the downgrade ratchet across tiers

Three tiers triple the cost of a heavyweight-only workflow, so each tier ships a **documented,
human-confirmed downgrade** — the field universally provides this escape hatch:

- **"this is one feature, not a system"** → skip `/design-system`;
- **"this capability is one node"** → skip `/plan-feature`, go straight to `/implement-feature`;
- the existing `/implement-feature` smell test (advisory-with-friction: it warns after the
  requirements gate and requires an explicit *"proceed anyway"*) is the **upgrade** direction of
  the same ratchet.

The ratchet is **one-way**: when in doubt, take the heavier path; **nothing downgrades mid-task**.
Each tier's exact downgrade triggers are owned by that tier's doc; this doc fixes only that every
tier must have one and that the ratchet does not reverse mid-task.

---

## 7. Execution principle — "design against real seams, not imagined ones"

The suite is built by **interleaving design and build, one tier per branch** (which dogfoods the
`feat/X`-is-the-shippable-unit rule: each tier is itself a shippable unit on its own branch).
Building a tier before finalizing the next tier's *interface* to it is the vertical-slice
principle applied to the suite itself.

When designing a downstream command, **split its design at the upstream-dependency seam**:

- **Stable core** — everything that does *not* depend on the upstream tier's output shape → design
  (and build) **now**, while the thinking is hot.
- **Cross-tier interface** — everything that consumes the upstream tier's real output → written
  **`PROVISIONAL — finalize against real <upstream> output`** and locked only after the upstream
  tier is built. **Never finalize a tier interface against an imagined output shape.**

The deferred part is tracked as a **blocked GitHub issue**, not a vague TODO — keeping GitHub the
honest SSOT of what still has to happen.

"Build," for these tiers, means **skill-authoring**: `SKILL.md` + `agents/*.md` + templates +
`guard.py` isolation rules + a purpose-built toy fixture + a **green dev-container dry run** — the
same bar as `/implement-feature`. `/implement-feature` cannot build these tiers: it builds Python;
these are Markdown/skill artifacts.

---

## 8. Shared invariants (inherited from `/implement-feature`, must survive one tier up)

- **Design & every review use a higher model/effort than implementation.** Planning is the
  highest-leverage design work in the suite, so it runs on the strong model.
- **Algorithm-blindness holds across tiers** (§4, seam B).
- **Green unit tests are not "done."** VERIFY drives the real code un-mocked; `Z` verifies the
  capability's behavior contract green, un-mocked — which is precisely what makes the
  archive/merge-back (§2) meaningful (you merge a delta only when the capability it claims is
  proven).
- **Bound every automated loop; surface to the human on no progress.**
- **Never commit before human approval; re-planning is human-gated; never commit on the default
  branch.**
- **Interactive conductors can't be pure subagents** (a subagent can't interview the human), so a
  planning conductor runs interactively on the strong model and *warns* on a weaker one; only
  *non-interactive* bias-sensitive gates (e.g. a decomposition red-team) run as isolated pinned
  subagents.

---

## 9. Falsifiable acceptance (per tier — "done ≠ the skill exists")

- **`/design-system`:** on a toy multi-capability request → a committed capability map (stable ids
  + dep DAG) + at least one durable `specs/<cap>/spec.md`; a **second** run adds a delta that
  merges cleanly (proves accumulation, §2).
- **`/plan-feature`:** produces the change against a capability + a real GitHub `{A,B,C,Z}`
  sub-issue DAG with dependency edges, **and** the red-team catches a **seeded horizontal
  decomposition** and a **seeded incompatible sibling seam**. If it passes either seeded defect,
  the gate is theatre.
- **`/implement-feature`:** unchanged (its existing green-dry-run bar).
- **Suite (end-to-end):** one threaded path — `/design-system` → pick a capability →
  `/plan-feature` → drive one child to green on `feat/X` → `Z` → merge/archive back into
  `specs/<cap>/`.

Each tier's *internal* acceptance detail is owned by that tier's doc; this doc fixes the
suite-level threaded path and the per-tier bars above.

---

## 10. Document ownership (boundary with the per-tier docs)

| Doc | Owns |
|---|---|
| **this doc** — `planning-suite-architecture.md` | the spine: substrate (§2), capability-id address (§3), inter-tier handoff contracts (§4), steering model (§5), progressive-rigor policy (§6), the "real seams" principle (§7), shared invariants (§8), suite + per-tier acceptance bars (§9) |
| `design-system.md` | `/design-system` tier internals — requirements + high-level design |
| `plan-feature.md` | `/plan-feature` tier internals — requirements + high-level design (stable core now; cross-tier interface provisional) |
| `developer-guide.md` + ADRs | `/implement-feature` — no new design doc; pending changes tracked in epic **#46** |

Keep this boundary honest: tier-specific mechanics (exact templates, gate structure, thresholds)
belong in the tier docs, not here. This doc changes only when the *shared* spine changes.

---

## Sources & credit

The suite borrows deliberately from prior art (cloned to `~/dev/agentic-sdlc-prior-art/`, read
from source):

- **[OpenSpec](https://github.com/Fission-AI/OpenSpec)** — the durable, capability-organized
  `specs/` + `changes/` substrate and the delta/archive lifecycle (§2), and spec-vs-design
  separation.
- **[addyosmani/agent-skills](https://github.com/addyosmani/agent-skills)** — the capability map
  with **stable kebab-case ids** as the address work is selected by (§3), one-way dependency
  direction, and "define the shared contract first, then parallelize" (§4).
- **[mattpocock/skills](https://github.com/mattpocock/skills)** — vertical tracer-bullet slices
  and the integrate-and-verify node (`Z`); `CONTEXT-MAP` for multi-context repos.
- **[superpowers](https://github.com/obra/superpowers)** — explicit `Consumes / Produces` seam
  signatures per task (§4), the spike/bounded/architectural rigor ratchet (§6), and
  finish-the-branch as its own step (the archive/merge-back, §2).
- **[gsd-core](https://github.com/open-gsd/gsd-core)** — `STATE.md` as the cheap orientation layer
  (§5) and Verify checking requirement/decision/goal coverage, not just "tests pass" (§8).

In-repo research this doc distills, under `docs/research/`: `2026-09-20-agentic-sdlc-gap-analysis.md`,
`2026-09-17-plan-feature-analysis-external.md`, and the two implement-feature gate proposals —
tracked for later action in epic **#46**.
