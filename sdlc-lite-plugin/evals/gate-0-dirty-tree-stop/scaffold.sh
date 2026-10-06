#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_fixtures/python-starter.sh"
python_starter flat

# What /sdlc-init leaves behind, uncommitted by design (#102)
cat >> pyproject.toml <<'TOML'

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.coverage.run]
source = ["romankit"]
branch = true
TOML
cat > .gitignore <<'IGN'
# sdlc-lite (/sdlc-init)
mutants/
.coverage*
*.egg-info/
.implement-feature/
if-runlog.jsonl
IGN
