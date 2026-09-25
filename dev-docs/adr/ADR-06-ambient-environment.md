# ADR-6 — A shipped workflow uses the ambient environment, never the author's

**Context**
- The plugin ships to other users. A hardcoded author would attribute a customer's commits to the
  plugin's author.

**Decision**
- Gate 10 takes `user.name`/`user.email` from ambient git config (no `--author`, no `git config`).
- If none is set, it stops and asks the human.

**Consequences**
- General rule: the tool inherits the host's identity, secrets, toolchain, and conventions.
