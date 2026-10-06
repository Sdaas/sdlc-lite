---
# regression guard (#102): a clean committed tree gets no uncommitted-changes stop — green before and after the fix
type: regex
pattern: 'Uncommitted changes'
flags: i
match: not_contains
target: last_message
---
