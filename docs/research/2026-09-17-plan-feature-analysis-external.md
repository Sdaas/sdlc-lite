I inspected the current `sdlc-lite` repository, the existing `/implement-feature` skill, Issue #32, and the companion `docs/design/plan-feature.md`. One important correction to my earlier analysis: **`/plan-feature` is still proposed, not implemented**, so the report below evaluates the design as currently specified and its fit with the existing `/implement-feature` architecture. ([GitHub][1])

# Analysis of `/plan-feature`

## Scope

The purpose of `/plan-feature` should be to provide the missing **understand-and-decompose step** between an ambiguous or structurally complex feature request and the existing `/implement-feature` workflow.

The current design correctly identifies the problem: `/implement-feature` is deliberately optimized for bounded features that can be held in one agent's working context. Larger work creates a different problem: the system has not yet been understood sufficiently to identify the right pieces, their relationships, their boundaries, and how the pieces can subsequently be implemented independently. Issue #32 therefore proposes `/plan-feature` as an upstream planning capability that produces a system-design document, a requirement-to-test coverage matrix, and a DAG of GitHub issues that can subsequently be handed to `/implement-feature`.

The important scope boundary is that `/plan-feature` should **not become another implementation workflow, project-management system, or autonomous agent swarm**. Its job is to transform uncertainty into a sufficiently coherent plan that implementation can safely proceed in smaller units. The current design explicitly preserves those boundaries: human-gated planning, GitHub as the DAG substrate, no autonomous child execution, and `/implement-feature` remaining the implementation engine.

There is, however, a useful refinement to the conceptual scope.

`/plan-feature` should not be thought of merely as:

> "Break a large feature into smaller issues."

Its deeper purpose is:

> **Understand what we are trying to build, establish a lightweight model of the system and its capabilities, and then identify an implementable set of slices that collectively deliver that intent.**

That distinction matters because decomposition is only valuable if the thing being decomposed is understood correctly.

The existing `/implement-feature` architecture provides a strong foundation for this. It already separates requirements, interface design, internal design, and test planning; keeps sensitive/internal reasoning out of downstream test-writing; uses explicit human approval gates; and treats the resulting artifacts as curated handoffs rather than passing raw conversational context between agents.

---

## What it does well

The strongest aspect of the current design is that it correctly identifies **uncertainty of structure plus decomposability**, rather than raw feature size, as the reason to invoke a heavyweight planning step. This is an excellent abstraction. A large but obvious CRUD change does not necessarily need a planner, while a seemingly small feature with several uncertain components may. The design explicitly makes this distinction.

The second strong decision is the separation between `/plan-feature` and `/implement-feature`. Planning and implementation have different objectives, different human interactions, different quality bars, and different outputs. Keeping `/plan-feature` upstream rather than turning `/implement-feature` into a branching mega-workflow preserves the clarity of both commands.

The proposed **DAG with a terminal Z integration-and-verification issue** is also strong. It gives the plan a concrete operational representation without requiring a resident orchestration agent. The idea that X is the shippable unit and that A/B/C are implementation slices which ultimately converge through Z is particularly useful for agentic development.

The **contract-not-algorithm** principle is perhaps the most important architectural decision in the proposal. A child issue should tell `/implement-feature` what the child must accomplish and what interface it exposes, but should not prescribe its internal implementation. This preserves the algorithm-blind test-writing and independent design process already established by `/implement-feature`.

The treatment of **non-functional requirements as something that also needs decomposition** is another strength. Performance, security, resilience, and similar properties cannot simply be left in a top-level requirements document. Allocating testable slices where possible while retaining genuinely global properties for Z gives the planner a way to reason about system-level qualities without pretending that every NFR belongs to one child.

The current proposal also has an excellent **feedback philosophy**. The plan is explicitly treated as a hypothesis: implementation may discover that the decomposition was wrong, and the system should surface that fact to a human rather than silently allowing the DAG to become fiction.

Finally, the design is consistent with the philosophy already embedded in `/implement-feature`: human ownership of consequential decisions, bounded workflows, explicit approval, isolated reasoning where appropriate, and evidence-based completion rather than simply generating documents. The existing implementation workflow is unusually deliberate about these boundaries.

---

## Key gaps / opportunities

### 1. Make "system intent" an explicit input/output of planning

The biggest opportunity is to strengthen the **front end of `/plan-feature`**, not the DAG mechanics.

Today the proposal moves from functional/NFR requirement elicitation into a system-design document and then into decomposition. That is sound, but it risks allowing the system-design document to become an implementation-oriented architecture document without first capturing the higher-level model of what the system is actually trying to accomplish.

The missing conceptual layer is lightweight **system intent**:

* Why are we building this?
* Who or what is it for?
* What are the important capabilities?
* What is inside and outside the system?
* What are the major constraints?
* What is deliberately not being attempted?
* What remains uncertain?

This should not become a formal PRD.

The desired artifact should be closer to a **shared mental model** than a contract.

For example:

```text
System intent
  ├── Problem / purpose
  ├── Users / actors
  ├── Core capabilities
  ├── System boundaries
  ├── Important constraints
  ├── Non-goals
  └── Open questions
```

The architecture then explains one plausible way to realize those capabilities.

This distinction is important because the architecture may change while the capabilities remain stable.

**POV:** add a lightweight "System Intent" section to the planning artifact rather than creating a separate heavyweight methodology or mandatory standalone document.

---

### 2. Make capabilities first-class, not just inferred from requirements

The strongest missing abstraction is **capability**.

Requirements answer questions such as:

> What must happen?

Architecture answers:

> How might the system support it?

Capabilities answer:

> What can this system actually do?

For example, a loan-covenant system might have capabilities such as:

* ingest loan documents
* identify and normalize covenants
* ingest financial reports
* extract relevant financial facts
* evaluate covenant conditions
* explain potential violations
* support human review

Those capabilities can subsequently be decomposed into features.

This creates a useful hierarchy:

```text
System intent
      ↓
Capabilities
      ↓
Features
      ↓
Implementation slices
      ↓
Code
```

Architecture should sit alongside this rather than replacing it:

```text
                 System Intent
                       │
              ┌────────┴────────┐
              ▼                 ▼
        Capabilities       Architecture
              │                 │
              └────────┬────────┘
                       ▼
                    Features
                       ▼
                /plan-feature
                       ▼
                  A / B / C / Z
```

**POV:** add a small capabilities section to the system-design artifact. Do not introduce a capability-management database, ontology, or elaborate taxonomy. A numbered list with a one- or two-sentence description is sufficient.

---

### 3. Make the architecture explicitly lightweight and decision-oriented

The current design says "system-design document", but that term can easily grow into a traditional architecture document. That would work against the stated goal.

The architecture should capture only what is necessary to explain the system's shape and enable sensible decomposition:

* major components
* responsibilities
* important boundaries
* key data/control flows
* externally visible interfaces
* significant architectural decisions
* important trade-offs
* unresolved architectural questions

It should explicitly avoid becoming:

* class-by-class design
* detailed database schema
* API specification
* implementation algorithm
* exhaustive technology inventory

Those belong downstream when a particular child enters `/implement-feature`.

**POV:** define the architecture artifact as a **decision-support model**, not a specification. It should answer "what are the important pieces and how do they relate?" rather than "how exactly will every piece be implemented?"

---

### 4. Separate "requirements" from "design decisions"

The current proposal combines requirement elicitation and system design effectively, but the resulting artifacts should make the distinction visible.

A requirement is something the system must satisfy.

A design decision is one way of satisfying it.

For example:

```text
Requirement:
The system must retain the original loan document.

Design decision:
Store source documents in object storage and retain immutable references.
```

This separation is important because agentic systems tend to turn their own suggestions into apparent requirements.

**POV:** explicitly label statements as one of:

* human requirement
* observed fact
* design decision
* assumption
* open question

This does not need elaborate metadata. Even lightweight headings or prefixes would substantially improve traceability.

---

### 5. Introduce "assumptions and unresolved questions" as first-class planning output

A major danger of AI-generated architecture is **false certainty**.

The current design is excellent at interviewing the human until requirements are explicit, but the planner also needs to be able to say:

> "We don't know yet."

For example:

```text
Open question:
Can the financial reports be trusted as the authoritative source?

Assumption:
For v1, the financial report is assumed to contain the required values.

Risk:
If the assumption is false, covenant evaluation may produce incorrect results.
```

This is particularly important for an agentic SDLC because downstream agents should know which parts of the plan are settled and which are provisional.

**POV:** add a small "Assumptions / Open Questions / Risks" section. Do not require every uncertainty to be resolved before decomposition; instead, identify whether each unresolved item blocks planning, blocks a particular child, or can safely remain open.

---

### 6. Improve the mapping between capabilities, requirements, and child issues

The current requirement → test matrix is valuable, but there is an opportunity to add one semantic level:

```text
Capability
    ↓
Requirement
    ↓
Child issue
    ↓
Acceptance test
```

This makes the plan much easier for a human to reason about.

It also makes the DAG more than a collection of tickets: the DAG becomes a concrete implementation of the capability model.

The planner should be able to answer:

> "Which pieces of the DAG collectively deliver capability C3?"

and:

> "Which requirement is not covered by any child?"

The current design already moves toward this with its requirement→issue/test coverage concept. The recommendation is therefore not a new mechanism so much as a **better semantic organization of information that the planner is already producing**.

**POV:** retain the requirement→test matrix, but extend its conceptual role to include capability and child-issue traceability.

---

### 7. Make the planning interview converge rather than simply exhaust questions

The existing `/implement-feature` interview has a particularly valuable lesson: it explicitly anchors the smallest viable scope before grilling, because an unconstrained interview tends to grow the feature through completeness bias.

That principle should carry directly into `/plan-feature`.

The planner should first establish:

> "What is the smallest coherent system we are actually trying to build?"

Then explore its structure.

The objective should not be to discover every conceivable feature. It should be to understand enough of the system to establish a useful architecture and capability model.

**POV:** make "minimum coherent system" an explicit early planning gate. The planner should actively identify deferred capabilities and non-goals.

---

### 8. Add an explicit "decomposition confidence" check

The current red-team review attacks gaps, overlaps, and internal-design leakage. That is good. A complementary question should be:

> **Do these child issues represent the natural seams of the system, or did we simply divide the work into convenient chunks?**

A bad decomposition can have perfect requirement coverage and still be architecturally wrong.

For example, splitting a system into:

```text
database
API
LLM
UI
```

may be technically convenient but not necessarily represent useful implementation units.

A stronger decomposition might be:

```text
document ingestion
covenant extraction
financial fact extraction
covenant evaluation
review / explanation
```

The latter corresponds more closely to capabilities and system behavior.

**POV:** have the red-team reviewer explicitly challenge the **semantic coherence of the decomposition**: are the children meaningful units of capability or merely technical layers/files/components?

---

### 9. Preserve the "contract, not algorithm" rule, but make contracts capability-aware

The current child contract is intentionally limited to interface, dependencies, acceptance and NFR slices. That is the right level for `/implement-feature`.

Add one small piece of context:

> **Capability served by this child.**

For example:

```text
Capability:
Extract covenants from a loan document

Child:
Identify covenant clauses

Contract:
Input: normalized document
Output: candidate covenant clauses
...
```

This gives the implementing agent a reason for the work without leaking the planner's internal implementation strategy.

**POV:** add capability identity/context to the child contract, but do not add internal architecture or implementation instructions.

---

### 10. Keep the system artifacts durable; keep planner-private reasoning ephemeral

The existing design wisely distinguishes committed planning artifacts from gitignored planner-private reasoning.

This distinction should become even more important if the system-intent/capability model is introduced.

The durable artifact should contain:

> what humans need to understand and review.

It should not contain:

> everything the planning agent thought while arriving there.

This is consistent with the existing `/implement-feature` philosophy of curated handoffs rather than raw transcripts.

**POV:** make the durable artifacts intentionally small. The planning agent should synthesize aggressively rather than dumping its reasoning into `docs/plans`.

---

### 11. Do not over-optimize the planner for "complete architecture"

The planner should be allowed to say:

> "This is enough architecture to start building."

rather than:

> "We need to resolve every architectural question before implementation."

Some decisions are naturally discovered during implementation.

A useful distinction is:

```text
Must decide before decomposition
Should decide before implementation
Can defer until implementation
```

This would make `/plan-feature` substantially more pragmatic.

**POV:** introduce a lightweight decision horizon rather than trying to eliminate architectural uncertainty completely.

---

### 12. Use implementation as an architectural feedback mechanism

The current design already has the excellent concept of a decomposition-defect feedback path.

Extend that idea slightly:

**the architecture itself is also a hypothesis.**

If implementation reveals that:

* a capability cannot be isolated,
* two children have an unexpected dependency,
* Z requires internal knowledge,
* a supposedly independent capability is not actually independent,

then that is evidence that the system model needs revision.

The re-plan mechanism should therefore be able to say:

> "The decomposition was wrong"

or:

> "The architecture/capability model was wrong."

**POV:** don't build automatic re-planning. Keep the existing human-gated approach. But make the feedback vocabulary broad enough to identify whether the problem was requirements, architecture, capability boundaries, or decomposition.

---

## What not to change

### Do not change the fundamental role of `/plan-feature`

Do not turn it into a second `/implement-feature`.

Its job is to **understand and decompose**, not to write production code. The separation between planning and implementation is one of the strongest aspects of the current design.

### Do not replace the DAG model

The GitHub DAG with A/B/C children and terminal Z is a good operational representation of the plan. It converts an architectural understanding into executable work without requiring a persistent autonomous supervisor.

### Do not remove Z

The terminal integration-and-verification node is important because the children collectively constitute the feature. It provides a concrete place where system-level requirements are re-verified.

The principle:

> **X is not done until the integrated system is verified**

should remain.

### Do not leak implementation algorithms into child issues

This should remain a hard architectural invariant.

The planner may reason about implementation internally, but the child handed to `/implement-feature` should remain a contract. This preserves the existing test-writer algorithm-blindness and allows `/implement-feature` to perform its own design work.

### Do not turn the artifacts into heavyweight enterprise documentation

This is probably the biggest danger.

Avoid evolving:

```text
SYSTEM.md
ARCHITECTURE.md
CAPABILITIES.md
REQUIREMENTS.md
NFR.md
ADR-001.md
ADR-002.md
...
```

into a documentation bureaucracy.

A small `docs/plans/<X>/` package containing a concise system model, architecture, capability/requirement mapping and DAG is enough.

### Do not make every decision mandatory

The current philosophy should remain:

> enough certainty to proceed safely, not certainty about everything.

The planner should distinguish unknowns that genuinely block progress from decisions that can be deferred.

### Do not introduce agent swarms

The current explicit rejection of autonomous parallel child execution is sensible. The value of `/plan-feature` is creating **good boundaries**, not creating a swarm that hides those boundaries.

### Do not automatically re-plan

The existing human-gated re-planning principle should remain.

A plan is a hypothesis. Implementation can falsify it. The system should surface that fact and let the human decide what happens next.

### Do not turn `/plan-feature` into a roadmap/project-management tool

It should continue to answer:

> "How do we understand and build this feature?"

not:

> "What should this company build over the next 12 months?"

### Do not weaken the existing `/implement-feature` contract

The current `/implement-feature` workflow has a deliberately strong architecture around curated handoffs, human approval, interface/internal separation, isolated subagents, and verification. `/plan-feature` should feed that system rather than requiring it to be redesigned.

---

## Recommended end state

The evolution I would aim for is:

```text
                       /plan-feature
                             │
                    ┌────────▼────────┐
                    │  Human interview │
                    │  + investigation │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ System Intent   │
                    │                 │
                    │ Why / Who       │
                    │ Capabilities    │
                    │ Boundaries      │
                    │ Constraints     │
                    │ Non-goals       │
                    │ Open questions  │
                    └────────┬────────┘
                             │
                  ┌──────────▼──────────┐
                  │ Lightweight         │
                  │ Architecture        │
                  │                     │
                  │ Components          │
                  │ Flows               │
                  │ Boundaries          │
                  │ Decisions           │
                  └──────────┬──────────┘
                             │
                             ▼
                  Requirements / NFRs
                             │
                             ▼
                 Capability → Requirement
                             │
                             ▼
                    A ─── B ─── C
                     \    |    /
                      \   |   /
                       ▼  ▼  ▼
                         Z
                             │
                             ▼
                    /implement-feature
```

The key change is **not to add more planning ceremony**.

It is to make the existing planner slightly more explicit about the thing it is actually trying to establish:

> **a coherent, lightweight model of the system and its capabilities from which implementation can be safely decomposed.**

That would make `/plan-feature` substantially more than a "large feature splitter" while preserving its original essence. It would become the bridge between **open-ended product/system thinking** and the very disciplined implementation workflow that `sdlc-lite` already has.

The design principle I would use to judge every proposed addition is:

> **Does this help the human and the agent understand the system well enough to make good boundaries, or does it merely add documentation?**

If it is the latter, leave it out.

[1]: https://github.com/Sdaas/sdlc-lite/blob/main/docs/design/plan-feature.md "sdlc-lite/docs/design/plan-feature.md at main · Sdaas/sdlc-lite · GitHub"
