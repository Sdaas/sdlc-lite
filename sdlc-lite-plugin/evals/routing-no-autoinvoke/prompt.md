---
description: A plain feature request that sounds like the workflow must NOT auto-invoke it
tags: [smoke, routing, entry-point]
plugins: ["../.."]
max_turns: 12
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
expected_outcome: The model does not call the Skill tool for implement-feature. Whether it helps with the request or mentions /implement-feature is not graded.
---

Add a to_roman(n) helper to romankit that converts an int from 1 to 3999 to its Roman numeral. Test-first please, and have it reviewed before anything is committed.
