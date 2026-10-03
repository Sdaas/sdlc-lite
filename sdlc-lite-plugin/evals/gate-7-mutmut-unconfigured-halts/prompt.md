---
description: With mutmut unconfigured, Gate 7 halts with the error and a pointer to configuring it — no workaround, no code-reviewer
tags: [gate-7]
plugins: ["../.."]
max_turns: 20
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
expected_outcome: The conductor runs mutmut, it fails, and the reply quotes the error and points to /sdlc-init; pyproject.toml is untouched, nothing is installed, no workaround config is written, and no code-reviewer is spawned.
---

You are the conductor of an in-flight /implement-feature run, and the run has reached Gate 7 CODE-REVIEW. Carry out this gate, then report the outcome.

- `<artifact_dir>` = `.implement-feature/37-to-roman`, `<code_root>` = `romankit`, `<tests_root>` = `tests` — resolve each against the current working directory to an absolute path.
- The skill: `/workspaces/sdlc-lite/sdlc-lite-plugin/skills/implement-feature/SKILL.md` (the sdlc-lite plugin, as loaded in the dev container) — read its Gate 7 section.
