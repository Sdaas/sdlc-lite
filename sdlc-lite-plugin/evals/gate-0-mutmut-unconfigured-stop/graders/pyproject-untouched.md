---
# Gate 0 is a pure checker: it never configures mutmut itself
type: regex
pattern: 'mutmut'
match: not_contains
target:
  source: file
  path: pyproject.toml
---
