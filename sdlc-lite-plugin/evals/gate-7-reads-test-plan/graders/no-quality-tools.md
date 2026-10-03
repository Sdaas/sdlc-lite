---
# #40: the reviewer grades the results files; running mutmut or coverage itself writes into the repo.
# trace, not tool_used: the calls are the subagent's.
type: regex
pattern: '\\?"command\\?"\s*:\s*\\?"[^\n]{0,300}(mutmut\s+(run|results)|pytest[^\n]{0,200}--cov)'
match: not_contains
target: trace
---
