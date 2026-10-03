---
# approval first: no tool table reaches pyproject.toml before the human says yes (Bash writes too)
type: regex
pattern: '\[tool\.(mutmut|pytest|coverage)'
match: not_contains
target:
  source: file
  path: pyproject.toml
---
