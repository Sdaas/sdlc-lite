---
description: Uncommitted changes in the working tree stop Gate 0 before the lock or the branch switch, naming the files and the commit-first or include choice
tags: [gate-0]
plugins: ["../.."]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
expected_outcome: A ⚠️ stop that names pyproject.toml and .gitignore, gives a git commit command for them, and offers to include them knowingly. No .active-run lock, no branch switch, no commit, no subagent.
---

/implement-feature add a to_roman(n) helper to romankit that converts an int from 1 to 3999 to its Roman numeral
