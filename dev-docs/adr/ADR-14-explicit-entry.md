# ADR-14 — One name, one surface; and a workflow is entered explicitly

**Context**
- With `commands/<x>.md` beside `skills/<x>/`, the command is injected instead of `SKILL.md` on all
  three load paths; the conductor improvises lookalike gates, still printing `Preflight passed`
  ([finding](../findings/2026-09-23-skill-suppression-findings.md), #55).
- Auto-invocation is real: *"add a `to_roman(n)` helper, built test-first with staged approvals"*
  loaded the whole skill unasked.

**Decision**
- **A command and a skill never share a name.** The `commands/implement-feature.md` shim was deleted;
  a skill registers its own slash command from `name:`.
- **This plugin's skills are explicit-entry only**, enforced by the guard:

```
you type /implement-feature  ──►  CLI injects SKILL.md as a user message ──► Gate 0
                                  (no tool call ──► no PreToolUse ──► guard never runs)

model decides from phrasing  ──►  Skill tool call ──► PreToolUse ──► guard DENIES
                                  ──► model tells the user to type /implement-feature
```

- `policy.skill_invoke_decision()` denies any `sdlc-lite:`-prefixed id and any bare id in
  `policy.PLUGIN_SKILL_NAMES` (#56). Other bare ids stay allowed.

**Consequences**
- Plugin-wide: a future skill inherits the rule.
- **Fragile:** relies on Claude Code expanding a typed slash command without the `Skill` tool. If that
  changes, the guard loudly denies the human's command. Re-measure when skill/command resolution
  changes.
- Regression checks: `tests/test_entry_points.py` (structural; also keeps `PLUGIN_SKILL_NAMES` in sync
  with `skills/`) and the 8-cell conformance matrix,
  [`DEVCONTAINER.md` → Entry-point check](../DEVCONTAINER.md#entry-point-check--verify-entry-pointspy).
