---
description: On an unconfigured repo, /sdlc-init shows the toolchain table and the proposed config as a diff, then stops for approval without writing
tags: [sdlc-init]
plugins: ["../.."]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
expected_outcome: A found / floor / action table for the pinned packages and a diff adding [tool.mutmut] with source_paths (plus the pytest/coverage tables and .gitignore lines), ending on a request for approval. pyproject.toml is unchanged, no .gitignore is created, nothing is installed or committed.
---

/sdlc-init
