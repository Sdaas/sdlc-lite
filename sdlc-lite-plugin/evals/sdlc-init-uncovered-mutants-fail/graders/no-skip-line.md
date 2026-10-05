---
# mutants exist, so this is not "nothing to mutate" — calling it skipped would hide a real failure
type: regex
pattern: '\bskipped\b'
flags: i
match: not_contains
target: last_message
---
