# ADR-8 — Draft → review the real file → promote

**Context**
- "Don't write before approval" meant the human approved a summary, not the real artifact.

**Decision**
- Human-approval gates write a **draft** (`handoff/draft/`) the human reads and may edit.
- On approval it is **promoted** to `handoff/`. Downstream gates read only promoted files.

**Consequences**
- The human approves exactly what they saw.
- The guard keeps drafts out of every subagent's reach (draft-confinement).
