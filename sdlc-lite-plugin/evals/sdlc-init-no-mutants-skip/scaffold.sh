#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_fixtures/python-starter.sh"
python_starter flat configured

# #101: the repo's only function is one mutmut 3 makes no mutant for — the 0.1.0 acceptance repo's
cat > romankit/__init__.py <<'PY'
"""romankit — small text helpers."""


def word_count(text: str) -> int:
    """Return the number of whitespace-separated words in text."""
    return len(text.split())
PY
cat > tests/test_romankit.py <<'PY'
from romankit import word_count


def test_word_count() -> None:
    assert word_count("the quick brown fox") == 4
PY
git add -A
git -c user.name=eval -c user.email=eval@example.invalid commit -q -m "word_count only"
