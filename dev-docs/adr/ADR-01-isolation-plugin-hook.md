# ADR-1 — Isolation is enforced by a plugin PreToolUse hook

**Context**
- `disallowedTools: Write` does not confine reads.
- A critic that keeps `Bash` can still write (`cat >`, heredocs).
- `blockReadsOutsideWorkingDirectories` works but is all-or-nothing.

**Decision**
- A plugin-shipped PreToolUse hook, keyed on `agent_type`, enforces read-confinement and secrets
  protection.

**Consequences**
- One place does audit, secrets, and per-agent blindness.
- It fires for subagents and in headless runs; a project-settings hook did not.
- Each agent's role instruction stays as a backstop.
