---
# the finding ties the bare test to its missing message assertion, not to some other gap
type: regex
pattern: 'test_to_roman_non_int_raises_type_error[\s\S]{0,400}\b(match|message)|\b(match|message)[\s\S]{0,400}test_to_roman_non_int_raises_type_error'
flags: i
target:
  source: file
  path: .implement-feature/37-to-roman/handoff/06-test-review-findings.md
---
