---
# result: no pytest.raises(T) without match= (a one-argument call closing on the same line);
# `pytest.raises(T) as ei` + an assert on the message is a valid alternative and is allowed
type: regex
pattern: 'pytest\.raises\(\s*\w+\s*\)(?!\s*as\b)'
target:
  source: file
  path: tests/test_roman.py
match: not_contains
---
