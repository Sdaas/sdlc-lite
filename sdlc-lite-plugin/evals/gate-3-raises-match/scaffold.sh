#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_fixtures/python-starter.sh"
source "$(dirname "$0")/../_fixtures/roman-handoff.sh"
python_starter flat
roman_handoff gate-3
