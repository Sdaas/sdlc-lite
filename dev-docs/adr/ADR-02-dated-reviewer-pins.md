# ADR-2 — Reviewers pin a *dated* model; producers pin the floating alias

**Context**
- A floating `opus` alias silently changes the reviewer when a new Opus ships, so the same code
  can get a different review months apart.
- Implementation benefits from the newest model and is not reproducibility-sensitive.

**Decision**
- `test-reviewer` and `code-reviewer` pin the dated `claude-opus-4-8`.
- `test-writer`, `implementer`, `verifier` pin `sonnet`.

**Consequences**
- A dated pin must be bumped deliberately and re-verified (#63).
- Evidence the pin is honored, and how to tie a transcript to its run:
  [`model-pinning-findings.md`](../findings/model-pinning-findings.md) §2, §5.
