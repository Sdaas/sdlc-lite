# ADR-7 — Never commit on the default branch (non-overridable)

**Context**
- The workflow commits code; clobbering `main` must be impossible.

**Decision**
- Gate 0 recommends stay-vs-new-branch by triviality.
- If HEAD is the default branch, a new `feature/<NN-slug>` branch is **required**. Gate 10 re-checks.

**Consequences**
- The human may override the triviality call, never this invariant.
