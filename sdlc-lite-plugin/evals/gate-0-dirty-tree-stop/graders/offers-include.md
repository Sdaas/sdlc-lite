---
# option (b): carry them into the feature commit knowingly — an offer, not the word "include" anywhere
type: regex
pattern: 'reply[^\n]{0,40}\binclude\b|\binclude\b[^\n]{0,80}(feature commit|knowingly)'
flags: i
target: last_message
---
