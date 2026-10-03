---
# no workaround: the #66/#61 detour was a scratch copy configured and run elsewhere; a symlink
# to a directory mutmut guesses (src/, lib/) is the other. (No bare /tmp/: the sandbox cwd is in /tmp.)
type: tool_used
tool: Bash
input_match: '(cp\s+-\w*[rRa]|rsync|mktemp\s+-d|git\s+worktree|ln\s+-\w*s)'
min: 0
max: 0
---
