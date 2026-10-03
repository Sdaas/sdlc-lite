---
description: A repo with no mutmut config fails the Gate 0 preflight with a pointer to /sdlc-init, before any lock or edit
tags: [gate-0]
plugins: ["../.."]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
expected_outcome: The 🔴 preflight render telling the human to run /sdlc-init. No .active-run lock is written, pyproject.toml is not edited, no subagent is dispatched.
---

/implement-feature add a to_roman(n) helper to romankit that converts an int from 1 to 3999 to its Roman numeral
