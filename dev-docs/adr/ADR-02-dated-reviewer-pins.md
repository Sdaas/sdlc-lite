# ADR-2 — Every isolated gate pins a dated model

**Context**
- A floating alias silently changes a gate when a new model ships, so the same code can get a
  different review months apart. An alias can also lag: `sonnet` still resolved to
  `claude-sonnet-5` when `claude-sonnet-5-5` was out.

**Decision**
- `test-reviewer` and `code-reviewer` pin `claude-opus-5-5`.
- `test-writer`, `implementer`, `verifier` pin `claude-sonnet-5-5`.
- The agent frontmatter is the single source of truth.

**Consequences**
- Every bump is deliberate and re-verified with a T3 dry run whose receipt shows the exact ids (#63).
- Evidence the pin is honored, and how to tie a transcript to its run:
  [`model-pinning-findings.md`](../findings/model-pinning-findings.md) §2, §5.
