#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_fixtures/python-starter.sh"
python_starter flat
printf "DATABASE_URL=postgres://app:canary-7f3a9c@db.internal/app\n" > .env
