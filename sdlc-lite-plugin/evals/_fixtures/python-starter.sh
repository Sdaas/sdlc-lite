#!/usr/bin/env bash
# Shared scaffold for the eval suite: a tiny Python repo, committed on `main`.
#
# Sourced by each case's scaffold.sh, which runs in the empty sandbox workspace
# (`claude plugin eval --scaffold`). Not a case itself: it has no prompt.md.
#
#   python_starter <layout> [config]
#     layout  flat        romankit/ at the repo root — importable from the cwd
#             src         src/romankit/, never installed — `import romankit` fails
#     config  (default)   [tool.mutmut] only — what Gate 0 requires (#19)
#             nomutmut    no tool config at all — an unconfigured repo
#             configured  everything /sdlc-init writes: the three tool tables + .gitignore
set -euo pipefail

python_starter() {
  local layout="$1" config="default" pkg_dir arg
  shift
  for arg in "$@"; do
    case "$arg" in
      nomutmut|configured) config="$arg" ;;
      *) echo "python_starter: unknown option '$arg'" >&2; return 1 ;;
    esac
  done

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

  if [ "$config" != nomutmut ]; then
    cat >> pyproject.toml <<EOF

[tool.mutmut]
source_paths = ["$pkg_dir/"]
EOF
  fi

  if [ "$config" = configured ]; then
    cat >> pyproject.toml <<EOF

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.coverage.run]
source = ["$pkg_dir"]
branch = true
EOF
    cat > .gitignore <<'EOF'
# sdlc-lite (/sdlc-init)
mutants/
.coverage*
*.egg-info/
.implement-feature/
if-runlog.jsonl
EOF
  fi

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
