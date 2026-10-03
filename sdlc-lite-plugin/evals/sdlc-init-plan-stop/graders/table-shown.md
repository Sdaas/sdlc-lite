---
# the reply itself carries the found / floor / action table, row-shaped (name · found · floor · action)
# from the first pin to the last — not a summary sentence, not only the tool output
type: regex
pattern: '\bfound\b[^\n]*\bfloor\b[\s\S]*\bruff[ \t|`*✅]+[\d.]+[ \t|`*✅]+[\d.]+[ \t|`*✅]+ok\b[\s\S]*\bpytest-asyncio[ \t|`*✅]+[\d.]+[ \t|`*✅]+[\d.]+[ \t|`*✅]+ok\b'
flags: i
target: last_message
---
