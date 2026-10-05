---
description: On a configured but uninstalled src-layout repo, not being importable alone triggers the single plan, which includes the editable install; nothing is run before approval (#101)
tags: [sdlc-init]
plugins: ["../.."]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
expected_outcome: The plan lists python -m pip install -e . as its install action (every package ok, no config missing), then stops for approval. Nothing is installed, written or committed.
---

/sdlc-init
