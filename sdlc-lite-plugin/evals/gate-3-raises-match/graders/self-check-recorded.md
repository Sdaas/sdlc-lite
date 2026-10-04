---
# mechanism, as a deliverable: the writer pasted its `grep -n "pytest.raises("` output under a
# `## Self-check` heading in 05-test-intent.md — real `N:` / `file:N:` hits inside that section,
# not prose (#63). A typed-in fake would pass here; grep-self-check (trace) is the cross-check.
type: regex
pattern: '^## Self-check[^\n]*\n(?:(?!\n## )[\s\S])*?(?:^|:)\d+:[^\n]*pytest\.raises\('
flags: m
target:
  source: file
  path: .implement-feature/37-to-roman/handoff/05-test-intent.md
---
