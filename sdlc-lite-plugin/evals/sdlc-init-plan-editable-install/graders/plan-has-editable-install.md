---
# #101 Expected: `python -m pip install -e .` is an action inside the single plan, before its approval ask
type: regex
pattern: 'python3? -m pip install -e \.[\s\S]*\b(approv\w*|apply|go ahead|proceed)\b'
flags: i
target: last_message
---
