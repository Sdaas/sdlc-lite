# Planning-suite restructure — working plan (branch-scoped)

> **Branch:** `docs/planning-suite-architecture`
> **Status:** design + documentation-restructure in progress. No code. **No commits yet.**
> **Resume with:** "read planning-suite-restructure-plan.md and continue." → **next action =
> standalone-cleanup pass on docs (4)+(5)** then GitHub reconcile + source deletion (see Progress).
> **Branch-scoped scratch:** `git rm` this file in the commit that finishes the restructure.
> Durable direction also in memory: `planning-suite-3tier.md`.

## Progress (as of 2026-09-20)

Working one step at a time; **user reviews + approves each doc before the next**. Naming
convention locked: **durable design docs are un-dated** (like `plan-feature.md`); the dated
`2026-09-20-planning-suite-architecture.md` is the research launch-pad (delete once absorbed).

- ✅ **Doc (3) DONE + approved** — `docs/design/planning-suite-architecture.md` (the durable spine:
  substrate, capability-id address, inter-tier handoff contracts, steering, progressive-rigor, the
  "real seams" principle, shared invariants, per-tier + suite acceptance). Framed as a hypothesis
  (one revision pass expected after design-system is built).
- ✅ **Doc (4) DONE + approved** — `docs/design/design-system.md` (tier internals: purpose,
  pipeline, artifact content, requirements-vs-decisions labelling, assumptions/horizon,
  progressive rigor, acceptance). It is **all stable-core** (most-upstream tier, no provisional
  parts). Added during review: a **§3.3 "reframe architecture-first requests" move** and a **§8.1
  sample eval scenario** (the kanban blurb + expected grilling behavior + expected artifacts).
- ✅ **Doc (5) DONE + approved** — `docs/design/plan-feature.md` (REPLACED the concept doc).
  Absorbed ADRs D3, D5 (strengthened w/ locked inter-child seam), D7, D8, D9; reframed D4→STATE.md
  orientation and D10→wrong-tier kick-up; dropped §6 non-goals overruled this session; added P1
  vertical-slice Rule; absorbed the desktop 12-point review (decomposition-tier pts 6/8/9/12).
  Provisional cross-tier parts (child-contract template; P2 inter-child seam format; seam-A inbox)
  flagged `PROVISIONAL — finalize against real /design-system output`. Old `plan-feature.md` +
  desktop doc now fully absorbed → deletable on this branch.
- ✅ **Doc (4) amended + approved** — added `/design-system` **§3.6 self-critique gate** (isolated
  red-team on capability map + specs, falsifiable seeded defects) and **§3.7 human review & refine
  loop** (bounded revise-until-approved; map approved first; nothing commits until approved);
  wired into §3 pipeline + §8 acceptance.
- 🔜 **NEXT — standalone-cleanup pass on (4)+(5)** (decided while reviewing (5); see "Standalone
  cleanup" below): the *durable set of three* (spine + (4) + (5)) is the standalone unit —
  **(Q1a)** scrub only dangling refs to soon-deleted docs, keep spine cross-refs; **(Q2)** keep
  decision rationale, cut backward-facing history; **(Q3-iii)** strip inline "(external review pt N)"
  citations, keep a short honest Sources & credit for *surviving* prior art only.
- Then: GitHub reconcile (#32), delete absorbed sources, `git rm` this plan file. See sequence.

## Standalone cleanup (decided 2026-09-20, reviewing (5))

The two tier docs will be the **buildable basis for the skills**, so they must not depend on files
about to be deleted. Decisions (grilled):
- **Q1 = (a):** standalone unit = the **three durable docs together** (spine + design-system +
  plan-feature). Keep cross-refs among them (spine owns shared content once — avoids drift). Remove
  only references to deleted docs (launch-pad `2026-09-20-planning-suite-architecture.md`, old
  `plan-feature.md`, Desktop original).
- **Q2 = keep rationale, cut history:** rewrite every "changed X from Y / today it works Z" into
  present-tense "the design is X, because W (rejected V)." No back-references; the *why* survives.
- **Q3 = (iii):** strip inline "(external review pt N)"-style citations from the body; keep a short
  "Sources & credit" for *surviving* prior art (the `~/dev/agentic-sdlc-prior-art/` repos + research
  docs kept under `docs/research/`, #46); drop refs to deleted docs.
- Open (next grilling round): fate of (5)'s **ADR-provenance table** (pure archaeology?) and the
  falsifiable **done-test** for the cleanup.

**Confirmed this session:** three-tier split is LOCKED — `/design-system` stops at capability
depth; detailed per-capability requirements + inter-child seams + A/B/C/Z DAG belong to
`/plan-feature <capability>` (progressive rigor, not a limitation).

## Prioritization (decided 2026-09-20)

- **`/implement-feature` is on hold ON THIS BRANCH — everything, including bugs.** Its
  gap-analysis backlog (the `2026-09-20-*` proposal/gap docs) is frozen; those docs need another
  detailed review round each before ANY become issues (avoid "50 issues, no plan"). Bug fixes to
  implement-feature happen on **separate branches**, not here.
- **Focus: `/design-system` then `/plan-feature`.** Return to the implement-feature gap-analysis
  + interview cleanup **only after BOTH new commands are built and dry-run green** (re-entry
  trigger = option **(c)**; long hold is accepted, and it lets real feedback on the shipped
  implement-feature accumulate meanwhile).
- **Mine, don't bury.** (4)/(5) actively **borrow** the thinking in the shelved docs — the
  interview-gate requirements rubric (intent hypothesis, split-detection, assumptions block,
  stop-test) and the design-review red-team rubric — **with credit**. implement-feature is NOT a
  sealed box.

---

## Goal

Turn sdlc-lite into an **opinionated agentic SDLC suite of planning tools**, documented so each
piece can be built individually, with research separated from durable design and duplicate/
incoherent docs cleaned up.

## Decided (locked this session)

1. **Three-tier suite:** `/design-system` → `/plan-feature` → `/implement-feature`.
   - `/design-system` (NEW): brainstorm → capabilities → lightweight architecture, DURABLE.
   - `/plan-feature`: decompose **one capability** into an `A/B/C/Z` GitHub-issue DAG (re-scoped
     from "plans one feature X"; old §6 non-goals overruled).
   - `/implement-feature`: build one node (unchanged).
2. **The spine = OpenSpec model:** a durable, **capability-organized `specs/`** source-of-truth
   that accumulates; each `/plan-feature` run is a change/delta that **merges back on archive**
   (= the `feat/X → main` merge, D8). Replaces per-feature `docs/plans/<X>/`.
   - The **stable capability id** (kebab-case) is the suite's shared address across all tiers.
3. **Steering = the DAG** (no resident supervisor; D4 stands) + a stateless `STATE.md`-style
   orientation file (D4 amendment).
4. **Doc structure to produce (durable, in `docs/design/`):**
   - **(3)** Umbrella suite architecture doc — owns: substrate + capability-id addressing +
     inter-tier handoff contracts + progressive-rigor policy + falsifiable acceptance per tier.
   - **(4)** `/design-system` — requirements + high-level design. Owns its tier internals only.
   - **(5)** `/plan-feature` — requirements + high-level design. Owns its tier internals only.
   - Borrow from the 5 prior-art tools **with credit**.
5. **Research → `docs/research/`** (reference material, non-authoritative — not a trash queue).

## Agreed safe sequence (order matters — nothing deleted/closed before replacements exist)

1. [x] **DONE + approved** — Wrote **(3)** suite architecture (durable) as
       `docs/design/planning-suite-architecture.md`; absorbs `2026-09-20-planning-suite-architecture.md`.
2. [~] **(4) DONE + approved; (5) NEXT.** Wrote **(4)** `/design-system` (durable) as
       `docs/design/design-system.md`. Still to do: **(5) stable-core** `/plan-feature` (durable;
       provisional cross-tier parts flagged per Q4). **Port the still-valid ADRs from
       `plan-feature.md` (D3, D5-strengthened, D7, D8, D9) and the reframed ones (D4→STATE.md,
       D10→wrong-tier), and absorb the desktop 12 points**, BEFORE deleting sources. Stable-core
       (5) on this branch means `plan-feature.md` + desktop are fully absorbed here → deletable
       on this branch.
3. [x] **DONE** — frozen `/implement-feature` material moved to `docs/research/`; tracked by a
       single backlog **epic #46** (no per-doc placeholder issues; each doc gets a review round
       later, then decomposes into template-conforming issues).
4. [ ] GitHub reconcile for the suite: **do not close #32 until replacements exist** — open a
       `/design-system` issue + a re-scoped `/plan-feature` issue (+ optional epic → doc (3)).
5. [ ] Move the two research docs → `docs/research/`.
6. [ ] Delete `plan-feature.md` + `~/Desktop/plan-feature-analysis.md` (now fully absorbed);
       `git rm` this plan file.

## Open decisions

- **Q1 — gate proposals → issues?** RESOLVED: **not yet.** They stay as docs (→ `docs/research/`),
  each needs another review round; issues only after the new tiers are built.
- **Q2 — #32 reconciliation:** LIVE. Given the focus shift, likely: re-scope #32 as the
  `/plan-feature` (re-scoped) tracker + open a `/design-system` issue when its build starts;
  don't file the frozen implement-feature backlog. May defer issue creation until design docs are
  reviewed (branch + this plan track the design work meanwhile).
- **Q3 — `/implement-feature` durable design doc?** DEFERRED (tier on hold).
- **Q4 — interleaving: RESOLVED.** Interleave design↔build per tier, branch-per-tier. Details
  below.

## Interleaving (Q4) — LOCKED

Rationale: `/plan-feature`'s **input is `/design-system`'s output** (capability specs). Vertical-
slice principle (P1) applied to the suite itself ⇒ build a tier before finalizing the next tier's
*interface* to it.

### PRINCIPLE — "design against real seams, not imagined ones" (capture in doc (3))

When designing a downstream command, split its design at the upstream-dependency seam:
- **Stable core** — everything that does NOT depend on the upstream tier's output shape → design
  (and build) **now**, while the thinking is hot.
- **Cross-tier interface** — everything that consumes the upstream tier's real output → written
  **`PROVISIONAL — finalize against real <upstream> output`** and locked only after the upstream
  tier is built. Never finalize a tier interface against an imagined output shape.

Applied to `/plan-feature`:
- **Core (now):** decomposition philosophy, **P1** vertical-slice invariant, red-team rubric,
  **D3/D7/D8/D9**, the `Z` model.
- **Provisional (defer):** the child-contract template that *consumes a capability spec*, the
  **P2** inter-child seam format.

### Two issues for `/plan-feature` (file at the plan-feature stage, not now)

- **Issue A — `/plan-feature` core**: the stable-core design + build.
- **Issue B — `/plan-feature` cross-tier interface (provisional)**: finalize the child-contract
  template + P2 seam against real capability specs; **blocked-by** design-system-built.
  Keeps GitHub SSOT honest — the deferred part is a tracked, blocked item, not a vague TODO.

### Sequence (branch-per-tier dogfoods D8: each tier = a shippable unit on its own branch)

1. THIS branch → **(3)** suite arch + **(4)** `/design-system` design + **(5) stable-core**
   `/plan-feature` design (provisional parts flagged) + cleanup → merge to main.
2. `feat/design-system` → **build** `/design-system` to a green dry run (capability map + one
   durable spec + delta-on-archive proven). Expect **one revision pass on (3)** here
   (architecture-as-hypothesis).
3. `feat/plan-feature` → **finalize (5)** against real specs + **build** to green (Issues A, B).

### Locked sub-decisions

- **(a)** (5): **draft stable-core now**, defer provisional cross-tier interface (principle above).
  ⇒ `plan-feature.md` + desktop doc CAN be absorbed+deleted on this branch (cleanup completes).
- **(b)** (3) is **durable but a hypothesis** — not frozen; one revision pass expected after
  design-system is built.
- **(c)** "build" = **skill-authoring** (SKILL.md / agents / templates / guard / toy fixture +
  green dev-container dry run), same bar as implement-feature. `/implement-feature` CANNOT build
  these (it builds python; these are markdown/skill artifacts).
- **(d)** branch topology as above (branch-per-tier).
- **desktop doc:** COPIED to `docs/research/2026-09-17-plan-feature-analysis-external.md`
  (2026-09-20); delete the `~/Desktop` original when ready.

## File inventory & fate

| File | Kind | Fate |
|---|---|---|
| `docs/design/planning-suite-architecture.md` | **doc (3) — durable spine** | ✅ **CREATED + approved** (un-dated = durable) |
| `docs/design/design-system.md` | **doc (4) — durable, `/design-system` tier** | ✅ **CREATED + approved** (incl. §3.3 reframe move + §8.1 eval scenario) |
| `docs/design/2026-09-20-planning-suite-architecture.md` | research/synthesis; **the launch pad** | absorbed by (3)(4); **delete once (5) also absorbs it** |
| `docs/design/plan-feature.md` | concept doc (12 ADRs) — **still in design/, active** | 🔜 absorb into (5) stable-core (REPLACE this file), then it IS doc (5) |
| `docs/research/2026-09-20-agentic-sdlc-gap-analysis.md` | research + impl-feature gap backlog | **MOVED** ✓ · tracked by epic #46 |
| `docs/research/2026-09-20-design-review-gate-proposal.md` | impl-feature proposal (Gate 2.5) | **MOVED** ✓ · epic #46 |
| `docs/research/2026-09-20-interview-gate-proposal.md` | impl-feature proposal (Gate 1) | **MOVED** ✓ (kept its `M` edit) · epic #46 |
| `docs/research/2026-09-17-plan-feature-analysis-external.md` | external 12-point review | **COPIED from Desktop** ✓ · absorb into (5), delete `~/Desktop` original |

## Repo state facts (as of 2026-09-20)

- Open issues: #45,#44,#43,#42,#40,#39,#37,#34,#32,#21,#20,#19,#9. #32 = "Add /plan-feature",
  enhancement, **no milestone (backlog)**, only GitHub record of the suite.
- Prior art cloned to `~/dev/agentic-sdlc-prior-art/` (OpenSpec, superpowers, agent-skills,
  skills, gsd-core) — read from source.
- Gap-analysis items already tracked: #40/#44 (mutmut), #34 (regression harness / eval-ish),
  #9 (resume-feature / resumability), #19 (toolchain install), #37 (match= check). Un-filed:
  test-quality doctrine, scoped re-review, finding severity, reviewer clauses, `/fix-bug`,
  `/ship`/finish-branch, full eval harness.

## Key pushback captured (so it survives a reset)

- Gate proposals are **not research** — filing them as issues before archiving prevents silent loss.
- Closing #32 without replacements **breaks the GitHub-SSOT rule**.
- "git has history" ≠ present rationale — port ADRs into (5) before deleting `plan-feature.md`.
- The spine (substrate + capability-id addressing + inter-tier contracts) lives in **(3)**, not (4)/(5).
- Keep (4)/(5) lean — requirements + high-level design for unbuilt commands; don't over-spec.
</content>
</invoke>
