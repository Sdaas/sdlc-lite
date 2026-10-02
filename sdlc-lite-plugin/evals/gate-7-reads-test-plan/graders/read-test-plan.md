---
# mechanism: a Read (or Bash cat/grep) of the test plan, not prose that names it. Known false
# positive: the conductor reading it itself; the brief does not name it, so it has no reason to.
type: regex
pattern: '\\?"(?:file_path|command)\\?"\s*:\s*\\?"[^\n]{0,300}04-test-plan\.md'
target: trace
---
