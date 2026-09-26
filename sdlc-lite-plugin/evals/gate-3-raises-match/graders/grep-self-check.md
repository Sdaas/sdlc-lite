---
# mechanism: the writer ran the pytest.raises grep over the tests (a Bash command, not prose
# that mentions it). Known false positive: the conductor running the same grep itself.
type: regex
pattern: '\\?"command\\?"\s*:\s*\\?"[^\n]{0,300}grep[^\n]{0,120}pytest\\*\.raises'
target: trace
---
