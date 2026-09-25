# ADR-3 — The interface/internal design split makes the test-writer algorithm-blind

**Context**
- A test-writer who knows the algorithm derives tests from it; a wrong implementation that shares
  those assumptions still passes.

**Decision**
- `02-design-interface.md` (public contract) → given to the test-writer.
- `03-design-internal.md` (algorithm) → withheld, enforced by the guard hook.

**Consequences**
- Tests encode the **contract**, so they can fail a bad implementation.
- Rejected alternatives live in the internal design, where the code-reviewer checks against them.
- Rule of thumb: blind the producer, inform the critic.
