# `sdlc-lite` eval suite

T1 on the [verification ladder](../../dev-docs/verification-ladder.md): `claude plugin eval` cases
that check the plugin's **prose** still behaves after a change. How to author a case and read a
result: [`eval-tutorial.md`](../../dev-docs/eval-tutorial.md).

## Run it (dev container, repo root)

```bash
set -a; source .env; set +a
export CLAUDE_CODE_WALNUT_SPIRE=1          # plugin eval is early-access on the container's build

claude plugin eval sdlc-lite-plugin --ablation none \
  --scaffold --no-publish --allow-tools Bash Write Edit
```

- `--scaffold` — each case builds its tiny Python repo from `_fixtures/python-starter.sh`.
- `--allow-tools Bash Write Edit` — Gate 0 runs shell commands; keep this flag **last** (it is
  variadic). Bash needs the container's two `--security-opt` flags (`DEVCONTAINER.md`).
- Narrow a run with `--case '<glob>'` or `--tag <tag>`; pilot with `--runs 1`.
- `--ablation with-without` adds the no-plugin baseline arm and reports the delta.

Results land in `results/<timestamp>/` (`aggregate-result.json`, `report.html`) — gitignored.

## Cases

| Case | Tags | Asserts |
|---|---|---|
| `entry-slash-bare` | entry-point, gate-0 | `/implement-feature` starts the workflow; Gate 0 preflight runs and stops for confirmation |
| `entry-slash-namespaced` | entry-point, gate-0 | The same for `/sdlc-lite:implement-feature` |
| `routing-no-autoinvoke` | routing, entry-point | A natural request never auto-invokes the skill (should-not-fire) and points at the slash command |
| `gate-0-lock-stop` | gate-0 | An existing `.active-run` stops the run before the preflight |
| `gate-0-not-importable-stop` | gate-0 | An uninstalled src-layout package is a 🔴 stop; the conductor does not `pip install` it |
| `gate-1-interview-entry` | gate-1 | Resuming after the Gate 0 STOP opens the interview; no requirements file or subagent yet |
| `guard-secret-read-denied` | guard | The guard hook blocks reading `.env`; the secret never reaches the reply |

`gate-1-interview-entry/history/through-gate-0.jsonl` is a recorded real session — re-record it
when Gate 0's shape changes (`eval-tutorial.md` § 5).
