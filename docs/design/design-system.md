# `/design-system` — requirements & high-level design

> **Status:** durable design, but a **hypothesis** — one revision pass expected after the tier is
> built to a green dry run (architecture-as-hypothesis).
> **Scope:** this doc owns the **internals** of the `/design-system` tier — its purpose, its
> pipeline, and the content of the artifacts it writes. The **spine** it plugs into (the durable
> `specs/` substrate, the stable capability-id address, inter-tier handoff contracts,
> progressive-rigor policy, shared invariants, suite acceptance) lives in
> `planning-suite-architecture.md` and is **not** re-specified here — only referenced.
> **Stable-core note:** `/design-system` is the **most upstream** tier, so it has no
> upstream-dependency seam and therefore **no provisional cross-tier parts** — the whole design is
> stable-core.

---

## 1. Purpose & role

`/design-system` is the tier that **understands and models a system**, durably, before any feature
is decomposed or built. Its deliverable is a **shared mental model of the system and its
capabilities from which implementation can be safely decomposed** — not code, not a heavyweight
PRD.

```
  /design-system   ──►   /plan-feature   ──►   /implement-feature
  (THIS doc)             (one capability       (one node)
                          → A/B/C/Z DAG)
```

It sits **upstream** of `/plan-feature`: it produces the durable capability specs that
`/plan-feature` selects (by stable id) and decomposes. It is the tier none of the earlier
single-command analyses covered — the external `/plan-feature` review's points 1, 2, 3, 5, 7, 10,
11 were, in aggregate, pressure to grow one command *upward* into system-level thinking; that
pressure is the signal that a separate tier was needed, and this is it.

**When NOT to use it (the downgrade).** Per the suite's progressive-rigor ratchet
(`planning-suite-architecture.md` §6), a human may confirm *"this is one feature, not a system"*
and skip straight to `/plan-feature` or `/implement-feature`. `/design-system` earns its cost only
when there is a **system of multiple capabilities** to model — not a single bounded feature.

---

## 2. What it produces (tier outputs)

Two durable, committed artifacts, both landing in the capability-organized `specs/` substrate
defined by the spine (`planning-suite-architecture.md` §2):

| Output | What it is | Consumed by |
|---|---|---|
| **capability map** | the load-bearing index: `\| capability id \| responsibility \| depends on \|` table + a dependency **DAG** | `/plan-feature` (selects a capability by id); the human (orientation) |
| **per-capability `spec.md`** | one durable behavior contract per capability — observable behavior + scenarios + labelled assumptions/decisions | `/plan-feature` (seam A inbox); regressed against forever after |

Plus the durable **lightweight architecture** (§3.4) and **system-intent** model (§3.1) as the
reasoning that produced the map. Planner-private brainstorming stays gitignored (per spine); the
durable artifacts are **synthesized aggressively, kept small** — "what humans need to understand
and review," never a transcript of everything the agent thought (external review point 10).

The address every output carries is the **stable capability id** (kebab-case, chosen once, never
renamed) — defined by the spine, §3; this tier is where ids are *born*.

---

## 3. The pipeline (interactive conductor → durable substrate)

`/design-system` mirrors the suite's declarative pattern — a `SKILL.md` score, pinned-model
agent-defs for any non-interactive gate, and the shared guard hook; no hand-written orchestration.
The conductor is **human-interactive** (brainstorming, capability boundaries, decisions), so by
the shared invariant it runs interactively on the strong model and **warns on a weaker one**; the
one non-interactive bias-sensitive gate — a **self-critique** pass on the drafted artifacts (§3.6)
— runs as an isolated pinned subagent.

The pipeline is a DAG you can enter anywhere sensible (dependencies are enablers, not gates), but
the intended flow is — note the two gates that stand between a draft and the durable substrate:

```
  brainstorm ─► system intent ─► capabilities ─► architecture ─► self-critique ─► human review & refine ─► durable specs/
   (§3.5)        (§3.1)           (§3.2)          (§3.4)          (§3.6)           (§3.7 · loops back)        (§2)
```

### 3.1 System intent (the shared mental model)

A lightweight model — closer to a shared understanding than a contract (external review point 1).
Sections:

```
System intent
  ├── Problem / purpose      — why are we building this?
  ├── Users / actors         — who or what is it for?
  ├── Core capabilities      — what can the system actually do? (→ §3.2)
  ├── System boundaries      — what is inside vs outside?
  ├── Important constraints  — the binding ones
  ├── Non-goals              — deliberately not attempted
  └── Open questions         — what remains uncertain (→ §5)
```

This is **not a PRD.** The architecture (§3.4) later explains *one plausible way* to realize these
capabilities; the capabilities can stay stable while the architecture changes.

### 3.2 Capabilities (first-class — the load-bearing abstraction)

Capabilities answer *"what can this system actually do?"* — distinct from requirements (*what must
happen?*) and architecture (*how might it support it?*). They are **first-class, not inferred from
requirements** (external review point 2). Worked shape (loan-covenant example):

```
ingest loan documents · identify & normalize covenants · ingest financial reports ·
extract financial facts · evaluate covenant conditions · explain violations · support human review
```

Each becomes a row in the **capability map** with a stable id, a one-to-two-sentence
responsibility, and its dependencies (one-way, **no cycles** — if two capabilities each need the
other, they are one capability). Keep it a map, not a database/ontology/taxonomy.

### 3.3 Interview convergence (borrowed, with credit)

The interview must **converge, not exhaust questions** (external review point 7). It borrows the
already-drafted interview rubric from the implement-feature interview-gate proposal
(`docs/research/2026-09-20-interview-gate-proposal.md`), lifted to the system level:

- **Intent hypothesis first** (its §2.1): before scoping, state one sentence of what the human
  actually wants + an honest confidence; below ~70%, list what's missing. Guards against modelling
  a well-scoped *wrong* system.
- **"Minimum coherent system" anchor** (external review point 7; the system-level analog of the
  implement-feature smallest-viable anchor): establish the smallest coherent system first, then
  explore structure; actively name deferred capabilities and non-goals.
- **Split detection** (its §2.4): a request that is genuinely several systems triggers a split
  conversation and STOP; split along user-visible/capability lines, **never by technical layer**.
- **Stop test** (its §2.5): done requires both an empty question-frontier *and* being able to
  predict the human's answers to the next questions; otherwise STOP and say what's foundationally
  missing.
- **Reframe architecture-first / technology-first requests.** A common real input arrives
  *inverted* — it leads with the tech stack and deployment (e.g. "React UI, Python backend,
  Postgres, deploy to Cloud Run *and* EC2") and states the actual capabilities thinly or not at
  all. This is the exact anti-pattern the tier exists to correct: such statements are **design
  decisions, not requirements** (§4), and the conductor must **pull the request back to
  capabilities and intent first** — surfacing each embedded tech/deploy choice, asking *why* it's
  binding, and tagging deferrable ones on the decision horizon (§6) — before modelling anything. A
  well-formed-*looking* request is not the same as a capability-first one.

### 3.4 Lightweight architecture (a decision-support model, not a spec)

The architecture captures only what is needed to explain the system's shape and enable sensible
decomposition (external review point 3):

**Includes:** major components · responsibilities · important boundaries · key data/control flows ·
externally visible interfaces · significant decisions · important trade-offs · unresolved
architectural questions.

**Explicitly excludes** (these belong downstream, when a child enters `/implement-feature`):
class-by-class design · detailed database schema · API specification · implementation algorithm ·
exhaustive technology inventory.

It answers *"what are the important pieces and how do they relate?"* — not *"how exactly will every
piece be implemented?"*

### 3.5 Behavior/implementation split at this tier

Each capability `spec.md` states **observable behavior + scenarios** (Given/When/Then for stateful
or sequenced behavior; a plain assertion for pure input→output — the conditional GWT rule from the
interview-gate proposal §3.2). The *how* stays out — the same interface/internal wall
`/implement-feature` enforces internally, applied one tier up (spine §2, property 2).

### 3.6 Self-critique gate (non-interactive, isolated)

Before the drafted artifacts are shown to the human, an **isolated pinned subagent** attacks them —
so the human reviews an *already-critiqued* draft, not a first pass. It mirrors `/plan-feature`'s
red-team gate (`plan-feature.md` §4), lifted to the system level, and is the reason the interview
must *converge* (§3.3): the interview stops when the frontier is empty; the self-critique is what
tests whether that "empty" was real. Its rubric:

- **Capability coherence** — is each row a genuine **capability** (*what the system can do*), or a
  technical layer / a requirement restated / an implementation detail in disguise? (external review
  pt 2, and the §3.5 behavior/impl wall). A `database` or `API` "capability" **fails** here.
- **Missing capabilities & boundaries** — is anything the intent (§3.1) implies absent from the
  map? Is the inside/outside boundary honest?
- **Dependency sanity** — one-way only, **no cycles** (§3.2); no capability mis-directed against the
  intent.
- **False certainty** — does any **assumption masquerade as an observed fact** (§4)? False
  certainty is the tier's chief danger (external review pt 5); the gate demands each be labelled and
  evidence-bearing (§5).
- **Scope creep** — has completeness bias grown the system past the **minimum coherent system**
  (§3.3, external review pt 7)? Capabilities beyond it must be named as deferred, not smuggled in.
- **Leaked how** — does any `spec.md` state *how* instead of observable behavior (§3.5)?

The gate is **falsifiable** (mirrors the suite bars, spine §9): it must catch a **seeded
technical-layer "capability"** (a layer posing as a capability) and a **seeded false-certainty
assumption** (a guess written as fact). If it passes either, the gate is theatre. Its findings are
handed to the human alongside the draft in §3.7 — it advises; it does not auto-edit or gate commit.

### 3.7 Review & refine loop (human-gated)

The durable artifacts are produced through an explicit, **bounded** revise-until-approved cycle —
not emitted one-way. This is the tier's analog of `/implement-feature`'s human-approval gates and
honors the shared invariant "never commit before human approval" (spine §8):

```
  draft artifact ─► self-critique (§3.6) ─► present draft + findings to human ─► human critiques
        ▲                                                                             │
        └─────────────────── conductor revises ◄──────────────────────────────────────┘
                         (bounded: surface to the human on no progress)
```

- **Artifact by artifact, in dependency order.** The **capability map is approved first** — it is
  the load-bearing object (§2); per-capability `spec.md`s, the architecture, and the assumptions
  block (§5) are drafted and reviewed only against an approved map, so a late map change doesn't
  invalidate downstream specs.
- **The human drives.** Each round the conductor presents the draft *plus* the self-critique
  findings, applies the human's corrections, and re-presents — it does not decide the artifact is
  done on its own.
- **The loop is bounded.** After a small number of passes with no convergence the conductor
  **stops and surfaces** it (shared invariant: bound every loop, surface on no progress) rather
  than churning — often the signal that a §5 open question is actually *blocking* and needs a
  decision, or that the request is really several systems (§3.3 split detection).
- **Nothing lands until approved.** Only human-approved artifacts are committed to the durable
  `specs/` substrate (§2); planner-private drafting stays gitignored until then.

---

## 4. Requirements vs. decisions vs. assumptions (visible labelling)

Agentic systems tend to turn their own suggestions into apparent requirements. So every statement
in the durable artifacts is **labelled** as one of (external review point 4):

- **human requirement** — something the system must satisfy
- **observed fact** — established by reading the repo/environment (cite the source)
- **design decision** — one chosen way of satisfying a requirement
- **assumption** — taken as true for now, evidence-bearing (§5)
- **open question** — not yet settled (§5)

Lightweight prefixes/headings suffice — no elaborate metadata.

---

## 5. Assumptions, open questions & risks (first-class output)

False certainty is the major danger of AI-generated architecture (external review point 5). The
tier must be able to say *"we don't know yet."* It writes an **evidence-bearing assumptions
block** — the shape lifted from the interview-gate proposal §3.1 (GSD's `assumptions-analyzer`
output shape, without a dedicated subagent):

| Assumption | Why (evidence — cite a path, or "asked the human") | If wrong | Confidence |
|---|---|---|---|
| … | … | … | Confident / Likely / Unclear |

Plus open questions and risks. Crucially, **not every uncertainty must be resolved before
proceeding** — each unresolved item is classified by *what it blocks*:

- **blocks planning** (must resolve before decomposition),
- **blocks a particular capability** (resolve before that capability is planned/built), or
- **safely open** (can defer).

This feeds the decision horizon (§6).

---

## 6. Decision horizon (don't over-optimize for complete architecture)

The tier is allowed to say *"this is enough architecture to start building"* rather than *"resolve
every architectural question first"* (external review point 11). Every architectural decision is
tagged on a horizon:

```
Must decide before decomposition   Should decide before implementation   Can defer until implementation
```

This keeps the tier pragmatic — enough certainty to make good boundaries, not certainty about
everything.

---

## 7. Progressive rigor (this tier's downgrade)

Per the spine's one-way ratchet (`planning-suite-architecture.md` §6), `/design-system` ships a
**lite vs. full** posture (OpenSpec's escape hatch):

- **Full** — multi-capability system: the whole pipeline (§3) → capability map + specs.
- **Lite** — a small or well-understood system: intent + a minimal capability map, skipping the
  heavier architecture pass.
- **Skip** — the human confirms "this is one feature, not a system" and drops to `/plan-feature`
  or `/implement-feature`.

The ratchet is one-way: when in doubt, take the heavier path; **nothing downgrades mid-run.** The
smell-test *upgrade* direction (a feature that turns out to be a system) is the same ratchet run
the other way.

---

## 8. Falsifiable acceptance (tier-internal)

The suite-level threaded path is in the spine (§9); this tier's own falsifiable bar — *"done ≠ the
skill exists"* — is:

> In the dev container, `/design-system` takes a **toy multi-capability** request → the
> **self-critique gate catches a seeded technical-layer "capability" and a seeded false-certainty
> assumption** (§3.6) → the artifacts pass through the **human review & refine loop** (§3.7) →
> producing a committed **capability map** (stable ids + dependency DAG) + at least one durable
> `specs/<cap>/spec.md`; a **second** run then adds a **delta that merges cleanly** into `specs/`
> — proving the substrate *accumulates* (spine §2, the property everything hangs on).

"Build" here means skill-authoring to that green dry run (`SKILL.md` + any `agents/*.md` +
templates + `guard.py` rules + a purpose-built toy fixture), the same bar as `/implement-feature`.
Expect **one revision pass on `planning-suite-architecture.md`** during this build — the spine is a
hypothesis until a real capability spec exists.

### 8.1 Sample eval scenario (realistic, multi-capability)

A **realistic** case (distinct from the small toy fixture used for the automated green dry run
above) — used to check that the built conductor actually *grills* rather than accepting a request
at face value. Kept here so the design and its eval baseline travel together.

**Sample prompt (given verbatim, deliberately architecture-first and capability-thin):**

> "I need to build a web-app that keeps a to-do list kanban-style. Users can create tasks, move
> them between columns, and attach one or more documents to a task. UI in React. Backend in
> Python. Persistence in Postgres, attachments in Google Cloud Storage. All dev in a dev
> container. Deployment is variable — first GCP Cloud Run (Mumbai region), second AWS EC2 with
> Docker. On first run the user sets up an admin via Google sign-in; other users sign up with
> Google but the admin must authorize them. Users can create and move tasks, not delete them.
> Admin is god at the application tier but cannot have direct access to the deployment environment
> or the database."

**Expected conductor behavior (a pass only if it does most of these — grilling, Socratic probing,
push-back):**

- **Reframes the request** (§3.3) — recognizes it as architecture-first/capability-thin and pulls
  it back to intent + capabilities before modelling anything.
- **Opens with an intent hypothesis + confidence**, not with "OK, React + Postgres it is."
- **Relabels** the tech/deploy choices as *design decisions*, not requirements (§4), and asks
  *why* each is binding — e.g. **"why Postgres?"**
- **Catches the dual-deploy scope smell** — "Cloud Run *and* EC2" is a portability NFR smuggled in
  as a feature; probes *want vs. should-want* and offers to defer the second target.
- **Anchors the minimum coherent system** (§3.3) and names the deferred capabilities.
- **Drills the privilege-separation one-liner** — "admin is god at the app tier but no DB/infra
  access": distinguishes *no shell/console access* (ops/IAM) from *cannot exfiltrate via the app
  they control* (a deep data-model constraint). The highest-leverage design risk in this prompt.
- **Demands non-goals + open questions** (§3.1, §5) — the prompt supplies none.
- **Pushes deployment specifics out** (§6) — Mumbai region / EC2 instance type / dev container are
  tagged *"defer until implementation"*, not modelled now.
- **Applies split detection sensibly** (§3.3) — this is one coherent system, so it should *not*
  force a split, but should confirm that judgment rather than assume it.

**Expected artifacts:**

- a **capability map** with stable ids + a dependency DAG — plausibly `identity-management`,
  `task-management`, `attachments`, plus a cross-cutting `access-control` / privilege-separation
  concern;
- at least one durable per-capability **`spec.md`** (behavior contract + scenarios + labelled
  assumptions/decisions/open-questions);
- a **lightweight architecture** (decision-support level — not schemas, not API specs, not a region
  choice);
- an **assumptions / open-questions / risks** block classified by what each blocks (§5), and a
  **decision-horizon** tagging of the deferred choices (§6).

**Explicitly NOT expected from this tier** (arrives later via `/plan-feature <capability>`):
detailed per-capability requirements, the locked inter-*child* seams, and the A/B/C/Z build DAG.

---

## Sources & credit

- **External `/plan-feature` review** (`docs/research/2026-09-17-plan-feature-analysis-external.md`)
  — the seven system-level points that define this tier: system intent (pt 1), capabilities-first
  (pt 2), lightweight decision-support architecture (pt 3), requirements-vs-decisions labelling
  (pt 4), assumptions/open-questions as first-class (pt 5), converging interview + minimum coherent
  system (pt 7), durable-but-small artifacts (pt 10), decision horizon (pt 11).
- **Interview-gate proposal** (`docs/research/2026-09-20-interview-gate-proposal.md`) — the intent
  hypothesis + stop test + split detection (§3.3) and the evidence-bearing assumptions block (§5),
  lifted from the implement-feature tier to the system level.
- **Design-review-gate proposal** (`docs/research/2026-09-20-design-review-gate-proposal.md`) — the
  red-team rubric behind the self-critique gate (§3.6), lifted to the system level (epic #46); the
  `/plan-feature` decomposition red-team (`plan-feature.md` §4) is its sibling.
- **OpenSpec** — lite vs. full spec (§7) and spec-as-behavior-contract (§3.5).
- **addyosmani/agent-skills** — the capability map with stable ids (§3.2, spine §3) and
  `interview-me` discipline (§3.3).
- **superpowers** — `brainstorming`'s "decompose into sub-projects, each with its own spec → plan →
  implementation cycle" (§3.2 split) and the rigor ratchet (§7).
- **mattpocock/skills** — `CONTEXT-MAP` for multi-context repos (the capability-map precedent).
- **gsd-core** — the `assumptions-analyzer` output shape (§5), captured without a dedicated agent.

_Out of scope for this doc (owned elsewhere): the substrate mechanics, capability-id addressing
rules, inter-tier handoff contracts, and shared invariants → `planning-suite-architecture.md`;
decomposition, the A/B/C/Z DAG, and the red-team → `plan-feature.md`._
