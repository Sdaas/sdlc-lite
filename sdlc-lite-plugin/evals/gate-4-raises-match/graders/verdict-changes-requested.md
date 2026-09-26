---
# the verdict line, not an echoed "APPROVE / CHANGES-REQUESTED" template
type: regex
pattern: '^\W*verdict\W*CHANGES-REQUESTED'
flags: im
target:
  source: file
  path: .implement-feature/37-to-roman/handoff/06-test-review-findings.md
---
