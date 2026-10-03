---
description: A Gate 2 skip deviation in the test plan means no mutmut run, and the skip is recorded with its reason
tags: [gate-7]
plugins: ["../.."]
max_turns: 20
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
expected_outcome: No mutmut call; the reply and the run-log both show mutation SKIPPED with the plan's reason; coverage still runs.
---

You are the conductor of an in-flight /implement-feature run, and the run has reached Gate 7 CODE-REVIEW. Carry out this gate's conductor steps up to, but not including, spawning the code-reviewer subagent. Then report what you did and what the code-reviewer will be given.

- `<artifact_dir>` = `.implement-feature/37-to-roman`, `<code_root>` = `romankit`, `<tests_root>` = `tests` — resolve each against the current working directory to an absolute path.
- The skill: `/workspaces/sdlc-lite/sdlc-lite-plugin/skills/implement-feature/SKILL.md` (the sdlc-lite plugin, as loaded in the dev container) — read its Gate 7 section.
