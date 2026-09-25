# Architecture decision records

Each ADR is Context / Decision / Consequences. Read the relevant one before a structural change.
Cite them as `ADR-N`. Evidence lives in [`../findings/`](../findings/).

| ADR | Decision in one line |
|---|---|
| [ADR-1](ADR-01-isolation-plugin-hook.md) | Isolation is enforced by a plugin PreToolUse hook, not by removing tools. |
| [ADR-2](ADR-02-dated-reviewer-pins.md) | Reviewers pin dated `claude-opus-4-8`; producers pin `sonnet`. |
| [ADR-3](ADR-03-interface-internal-design-split.md) | Test-writer gets the interface design, never the internal (algorithm) design. |
| [ADR-4](ADR-04-product-vs-process.md) | Product in the repo on a branch; process artifacts in gitignored `.implement-feature/`. |
| [ADR-5](ADR-05-measure-never-orchestrate.md) | Code may measure or enforce, never orchestrate; monitoring fails loud. |
| [ADR-6](ADR-06-ambient-environment.md) | Use the host's git identity and environment, never the author's. |
| [ADR-7](ADR-07-never-commit-default-branch.md) | Never commit on the default branch; not overridable. |
| [ADR-8](ADR-08-draft-review-promote.md) | Human approves the real draft file, which is then promoted. |
| [ADR-9](ADR-09-minimal-scope-interview.md) | Interview confirms a minimal scope first, then grills within it. |
| [ADR-10](ADR-10-secrets-path-components.md) | Secrets match on path components, split by tool. |
| [ADR-11](ADR-11-intent-and-effect.md) | One `policy.py`, two legs: guard (intent) + transcript auditor (effect). |
| [ADR-12](ADR-12-model-effort-integrity.md) | Gates dispatch bare so pins hold; the receipt verifies model and effort. |
| [ADR-13](ADR-13-one-plugin-two-channels.md) | One plugin; dev and release are two marketplaces in two repos. |
| [ADR-14](ADR-14-explicit-entry.md) | No command shares a skill's name; skills are entered only by a typed slash command. |
