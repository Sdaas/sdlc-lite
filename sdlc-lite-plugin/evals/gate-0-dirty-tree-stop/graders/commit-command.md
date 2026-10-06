---
# option (a): the exact command — a git add naming both files (one is untracked, so `commit -am` is not enough), then git commit
type: regex
pattern: 'git\s+add\s[^\n]*(pyproject\.toml[^\n]*\.gitignore|\.gitignore[^\n]*pyproject\.toml)[^\n]*(&&|\n)[^\n]*git\s+commit'
target: last_message
---
