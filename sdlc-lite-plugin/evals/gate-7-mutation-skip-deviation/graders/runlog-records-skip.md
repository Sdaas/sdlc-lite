---
type: regex
pattern: '"gate"\s*:\s*"CODE-REVIEW/measure"[^\n]{0,400}SKIPPED[^\n]{0,300}(equivalent|symbol pairs|known-values)'
flags: i
target:
  source: file
  path: .implement-feature/37-to-roman/handoff/run-log.jsonl
---
