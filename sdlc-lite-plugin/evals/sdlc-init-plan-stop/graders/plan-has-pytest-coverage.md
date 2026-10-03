---
# the whole plan is shown, not just the mutmut table
type: regex
pattern: '\[tool\.pytest\.ini_options\][\s\S]*\[tool\.coverage\.run\][\s\S]{0,120}branch\s*=\s*true|\[tool\.coverage\.run\][\s\S]{0,120}branch\s*=\s*true[\s\S]*\[tool\.pytest\.ini_options\]'
target: last_message
---
