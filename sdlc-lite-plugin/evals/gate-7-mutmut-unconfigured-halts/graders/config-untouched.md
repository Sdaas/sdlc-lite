---
# no workaround: the user's config is not edited
type: regex
pattern: 'mutmut'
match: not_contains
target:
  source: file
  path: pyproject.toml
---
