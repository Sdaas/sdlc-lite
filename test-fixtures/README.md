# Test fixtures — standard repos for T3 dry runs

A fixture is a small, **committed** Python package that `/implement-feature` runs against in the dev
container ([`DEVCONTAINER.md`](../dev-docs/DEVCONTAINER.md)). Tier context:
[`verification-ladder.md`](../dev-docs/verification-ladder.md).

## Why committed, not generated

- **Non-empty:** an existing module + tests shows whether new code lands correctly beside real code.
  An empty folder lets the conductor invent the layout.
- **Byte-identical across runs:** generating per run (`uv init`, …) adds a "what did the generator do
  today" confound. The script only copies.

## Layout — `python-starter/<slug>/`

| File | What |
|---|---|
| `pyproject.toml` | src-layout; package from slug (`roman-numeral` → `src/roman_numeral/`) |
| `src/<pkg>/greet.py` + `tests/test_greet.py` | shared, deliberately boring module: `greet(name) -> f"Hello, {name}!"`, `ValueError` on empty/whitespace. Identical in every fixture |
| `BRIEF.md` | the literal one-line request, verbatim, so a receipt difference means the workflow changed, not the wording |

## Fixtures

| Slug | Feature | Status |
|---|---|---|
| `roman-numeral` | int ↔ Roman numeral, both directions, rejects malformed input | available |
| `parse-duration` | from the earliest dry runs | planned |
| `async-cached-json-fetcher` | from the earliest dry runs ([finding](../dev-docs/findings/dry-run-fault-injection-findings.md)) | planned |

## Run one

1. On the Mac, from the repo root:
   ```bash
   test-fixtures/setup-fixture.sh roman-numeral
   ```
   It creates `/workspaces/<slug>-run/` in the container: copy → `git init` on `main` + baseline commit
   (forces the run onto a feature branch, ADR-7) → `pip install -e .` (Gate 0 import check). It
   refuses if the dir exists; remove a stale one by hand.
2. Start Claude in the scratch repo:
   ```bash
   devcontainer exec --workspace-folder . bash -c "cd /workspaces/roman-numeral-run && claude --model opus"
   ```
3. Type `/implement-feature` followed by `BRIEF.md`'s content.
4. Read handoff files at each STOP:
   [`DEVCONTAINER.md` → Reading a fixture run's files](../dev-docs/DEVCONTAINER.md#reading-a-fixture-runs-files-from-the-mac).

## Planned

- **#21** — rebuild the container fresh per run; wraps `setup-fixture.sh`.
- **#34** — an agent drives the gates unattended, judged by the receipt, using `BRIEF.md` as its prompt.
