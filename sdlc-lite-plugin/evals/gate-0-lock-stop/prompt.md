---
description: A run already in flight (.active-run present) stops Gate 0 at its first action
tags: [gate-0, flaky]
plugins: ["../.."]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
expected_outcome: The conductor reports the in-flight run by its artifact dir and stops, asking the human to finish or abandon it. The preflight never runs.
---

/implement-feature add a to_roman(n) helper to romankit that converts an int from 1 to 3999 to its Roman numeral
