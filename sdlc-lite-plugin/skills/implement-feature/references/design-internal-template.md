# Design — internal: <feature name>

> Canonical handoff file: **`03-design-internal.md`** (Gate 2 outbox; drafted at
> `handoff/draft/`, promoted on approval). The **algorithm and internal decisions**. Seen
> by the `implementer`, `test-reviewer`, and `code-reviewer` — but **NEVER handed to the
> `test-writer`** (that split is what keeps the tests algorithm-blind, P15).

## Approach
The chosen algorithm/strategy, in enough detail to implement. Note the key steps.

## Alternatives considered
What else was on the table and why it was rejected (1–2 lines each). Keeps the decision
auditable at review.

## Data structures & internal contracts
Internal types, helper functions, module layout under `src/`.

## Complexity & resource notes
Time/space characteristics; anything relevant to the non-functional ACs (scale/perf).

## Quality expectations
Feature-specific expectations beyond the standard Definition of Done — e.g. purity of a
core function, no I/O in a given layer, specific error-handling posture, security posture
for the boundaries in the inventory.

## Risks / tricky bits
Where a wrong implementation is most likely; what the reviews should scrutinize.
