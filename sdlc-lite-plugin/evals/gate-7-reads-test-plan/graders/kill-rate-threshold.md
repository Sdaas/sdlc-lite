---
# result: the findings compare the kill rate against the plan's 85% (not the standards' 80% anchor)
type: regex
pattern: '(kill|mutation)[\s\S]{0,200}\b85\s*%|\b85\s*%[\s\S]{0,200}(kill|mutation)'
flags: i
target:
  source: file
  path: .implement-feature/37-to-roman/handoff/08-code-review-findings.md
---
