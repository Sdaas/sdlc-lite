# Design — public interface: <feature name>

> Canonical handoff file: **`02-design-interface.md`** (Gate 2 outbox; drafted at
> `handoff/draft/`, promoted on approval). The **public contract only** — everything
> observable from outside the feature, and NOTHING about the algorithm. This file is
> shared with the algorithm-blind `test-writer`, so tests encode the contract, not the
> implementation. If a detail would tell the reader *how* it works internally, it belongs
> in `03-design-internal.md`, not here.

## Public surface
For each public function / class / endpoint:
- **Signature** — name, parameters (name + type), return type.
- **Purpose** — one line, behavioral (what the caller gets), not algorithmic.

## Inputs & outputs
- Accepted input domain (valid ranges, shapes, preconditions).
- Output shape/meaning for valid input.

## Error & edge behavior (observable)
- What happens on invalid input, empty input, boundary values — the *observable* result
  (raises `X`, returns `Y`), not the internal branch that produces it.

## Invariants & guarantees (observable)
- Properties a caller can rely on (e.g. "output is sorted", "idempotent", "pure — no
  side effects", ordering, determinism).

## Traceability
- Which acceptance criteria (from `01-requirements.md`) this surface satisfies.
