# ADR-10 — Secrets match on path components, tool-split

**Context**
- Substring-matching `.env`/`key`/`credentials` against a Bash command falsely denies
  `python -c "os.environ.get('X')"`.
- One false hit flips the analyzer's whole-run verdict to VIOLATION and buries real signal.

**Decision**
- File-target tools: the target is a path → match by path component (over-broad is fine).
- Bash: tokenize; flag only tokens that clearly name a secret *file*, never a bare identifier.

**Consequences**
- Guard and analyzer share the identical predicate, tool split included, via `policy.py`.
