# ADR-4 — Separate product from process by lifecycle

**Context**
- Using the repo root as the run's workdir collides once a second feature exists, and risks
  committing process artifacts.

**Decision**
- Shipping code and tests → the repo's own layout, isolated per feature by **branch**.
- Process artifacts → a per-run, gitignored `.implement-feature/<run>/`.

**Consequences**
- The guard hook does not inherit the conductor's environment, so config reaches it through a
  **pointer file** (`.implement-feature/.active-run`).
- The pointer doubles as the single-run lock.
