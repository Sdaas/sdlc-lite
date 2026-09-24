#!/usr/bin/env bash
# Shared scaffold for the eval suite: a tiny Python repo, committed on `main`.
#
# Sourced by each case's scaffold.sh, which runs in the empty sandbox workspace
# (`claude plugin eval --scaffold`). Not a case itself: it has no prompt.md.
#
#   python_starter flat   # romankit/ at the repo root — importable from the cwd
#   python_starter src    # src/romankit/, never installed — `import romankit` fails
set -euo pipefail

python_starter() {
  local layout="$1" pkg_dir

  case "$layout" in
    flat) pkg_dir="romankit" ;;
    src)  pkg_dir="src/romankit" ;;
    *)    echo "python_starter: unknown layout '$layout'" >&2; return 1 ;;
  esac

  mkdir -p "$pkg_dir" tests

  cat > pyproject.toml <<EOF
[project]
name = "romankit"
version = "0.1.0"
requires-python = ">=3.10"

[tool.setuptools.packages.find]
where = ["$( [ "$layout" = src ] && echo src || echo . )"]
EOF

  cat > "$pkg_dir/__init__.py" <<'EOF'
"""romankit — small helpers for Roman numerals."""


def is_roman_char(c: str) -> bool:
    """True if c is a single Roman-numeral character."""
    return len(c) == 1 and c in "IVXLCDM"
EOF

  cat > tests/test_romankit.py <<'EOF'
from romankit import is_roman_char


def test_is_roman_char() -> None:
    assert is_roman_char("X")
    assert not is_roman_char("A")
EOF

  git init -q -b main
  git add -A
  git -c user.name=eval -c user.email=eval@example.invalid commit -q -m "initial romankit"
}
