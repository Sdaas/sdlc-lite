---
# step 7 (the branch switch) must not run before the human chooses
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*git\s+(switch\s+-c|checkout\s+-b)'
min: 0
max: 0
---
