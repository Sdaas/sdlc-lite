---
description: Typing /implement-feature starts the workflow, which runs Gate 0 and stops for confirmation
tags: [smoke, entry-point, gate-0]
plugins: ["../.."]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
expected_outcome: The Gate 0 summary with a passed preflight, ending on the STOP that asks the human to confirm layout, model plan and branch. No subagent is dispatched.
---

/implement-feature add a to_roman(n) helper to romankit that converts an int from 1 to 3999 to its Roman numeral
