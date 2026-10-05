---
# #101: "no mutants" is not a failure — the reply carries no red / failure marker
type: regex
pattern: '🔴|❌'
match: not_contains
target: last_message
---
