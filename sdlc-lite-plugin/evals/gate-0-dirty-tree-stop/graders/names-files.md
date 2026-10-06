---
# the stop's headline names both files — not satisfied by the commit command line alone
type: regex
pattern: 'Uncommitted changes[^\n]*(pyproject\.toml[^\n]*\.gitignore|\.gitignore[^\n]*pyproject\.toml)'
flags: i
target: last_message
---
