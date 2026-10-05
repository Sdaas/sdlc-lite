---
# a no-op means no write by any route: Bash redirects, tee and in-place edits aimed at the config files
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*((>>?|tee\s+(-a\s+)?|sed\s+-i\S*\s+(?:[^"\\]|\\.)*)\s*\S*(pyproject\.toml|\.gitignore))'
min: 0
max: 0
---
