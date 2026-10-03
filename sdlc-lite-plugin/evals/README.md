# `sdlc-lite` eval suite

T1 on the [verification ladder](../../dev-docs/verification-ladder.md): `claude plugin eval` cases
that check the plugin's **prose** still behaves after a change. How to author a case and read a
result: run `claude plugin eval --help` and ask Claude. Environment problems (container, Bash grant,
`~/.docker`): [`DEVCONTAINER.md`](../../dev-docs/DEVCONTAINER.md#running-plugin-eval-problems-and-fixes).

## Run it (dev container, repo root)

```bash
set -a; source .env; set +a

claude plugin eval sdlc-lite-plugin --ablation none \
  --scaffold --no-publish --trust-plugin --allow-tools Bash Write Edit
```

- `--scaffold` — each case builds its tiny Python repo from `_fixtures/python-starter.sh` (with `[tool.mutmut]` by default; `nomutmut` and `configured` vary it). "Not a git repo" cannot be staged at T1 — the harness's sandbox home above the workspace is itself a git repo; the gate-3/4/6/7 cases add an in-flight run's handoff files from `_fixtures/roman-handoff.sh`.
- `--allow-tools Bash Write Edit` — Gate 0 runs shell commands; keep this flag **last** (it is
  variadic). Bash needs the container's two `--security-opt` flags (`DEVCONTAINER.md`).
- Narrow a run with `--case '<glob>'` or `--tag <tag>`; pilot with `--runs 1`.
- `--ablation with-without` adds the no-plugin baseline arm and reports the delta.

Results land in `results/<timestamp>/` (`aggregate-result.json`, `report.html`) — gitignored.

## Cases

| Case | Tags | Asserts |
|---|---|---|
| `entry-slash-bare` | smoke, entry-point, gate-0 | `/implement-feature` starts the workflow; Gate 0 preflight runs and stops for confirmation |
| `entry-slash-namespaced` | entry-point, gate-0 | The same for `/sdlc-lite:implement-feature` |
| `routing-no-autoinvoke` | smoke, routing, entry-point | A natural request never auto-invokes the skill (should-not-fire); the reply itself is ungraded, so one mechanism grader by design (#76) |
| `gate-0-lock-stop` | gate-0 | An existing `.active-run` stops the run before the preflight |
| `gate-0-not-importable-stop` | gate-0 | An uninstalled src-layout package is a 🔴 stop; the conductor does not `pip install` it |
| `gate-0-mutmut-unconfigured-stop` | gate-0 | No `[tool.mutmut]` is a 🔴 preflight stop pointing to `/sdlc-init`, before the lock; Gate 0 edits nothing (#19) |
| `gate-1-interview-entry` | gate-1 | Resuming after the Gate 0 STOP opens the interview; no requirements file or subagent yet |
| `gate-3-raises-match` | gate-3 | The test-writer greps its own `pytest.raises` calls; none is bare against a documented message contract |
| `gate-4-raises-match` | gate-4 | The test-reviewer greps for `pytest.raises` and returns CHANGES-REQUESTED on a bare one against a documented message (step order and the no-contract case are not graded) |
| `gate-6-concurrency-policy` | gate-6 | The verifier applies the standards' concurrency policy: a pure feature's report says "no concurrency surface" |
| `gate-7-reads-test-plan` | gate-7 | The code-reviewer reads `04-test-plan.md` (not named in its brief) and reports the kill rate against its 85% threshold, grading the conductor's `quality/` results and never running `mutmut` or `--cov` itself (#40). The test-plan read passed pre-fix (#61) |
| `gate-7-conductor-runs-quality` | gate-7 | Before the CODE-REVIEW dispatch the conductor runs coverage and mutmut into `quality/`; no `.coverage*` or `mutants/` is left in the product tree (#40, #75) |
| `gate-7-mutmut-unconfigured-halts` | gate-7 | Running the full gate, an unconfigured mutmut halts Gate 7 with a `[tool.mutmut]` / `/sdlc-init` pointer: no config edit, no `pip install`, no code-reviewer (#40) |
| `gate-7-mutation-skip-deviation` | gate-7 | A `skip — <reason>` kill-rate in the test plan: no mutmut call; the reply and run-log show `mutation: SKIPPED` with the reason (#40) |
| `sdlc-init-plan-stop` | sdlc-init | On an unconfigured repo `/sdlc-init` shows the found / floor / action table and the config as a diff, then stops: nothing written, installed or committed (#19) |
| `sdlc-init-noop` | smoke, sdlc-init | On a set-up repo `/sdlc-init` changes nothing: no edit, the mutmut smoke test runs and leaves no `mutants/`, "nothing to change" (#19) |
| `guard-secret-read-denied` | smoke, guard | The guard hook blocks reading `.env`; the secret never reaches the reply |

`gate-1-interview-entry/history/through-gate-0.jsonl` is a recorded real session — re-record it
when Gate 0's shape changes. See "Case rules" below.

## Case rules

1. **Write the prompt as a user would type it. Never name the skill.** Use "Add a --json flag to
   the exporter", not "run /implement-feature". The case must prove that routing works.
2. **Write the case before the prose it checks. Run it. It must fail.** This is the "red" step of
   [`verification-ladder.md`](../../dev-docs/verification-ladder.md) § 6.
3. **Test a "must not fire" case with this grader:**

   ```markdown
   ---
   type: tool_used
   tool: Skill
   input_match: '"skill"\s*:\s*"(?:[\w-]+:)?implement-feature"'
   min: 0
   max: 0
   arm: both
   ---
   ```

   `max: 0` alone never passes, because `min` defaults to 1. Without `arm: both`, `--ablation
   with-without` drops `Skill` graders from the score. The negative case would then be unscored.
4. **A case seeded with `history_file` has a Δ of about 0.** The recorded transcript already holds
   the skill text, so the no-plugin arm still has it. Judge such a case on its with-plugin score.
   Each run also writes `history/<session-uuid>.jsonl`. `.gitignore` excludes it. Do not commit it.
   Re-record the history file when the gates before it change.

## Tags

| Tag | Meaning |
|---|---|
| `gate-0` … `gate-11` | The gate the case exercises |
| `routing` | Whether the workflow starts (or correctly does not) |
| `entry-point` | The explicit-entry contract: slash spellings, no auto-invocation |
| `guard` | Guard-hook behavior |
| `sdlc-init` | The `/sdlc-init` skill |
| `smoke` | Cheap cases that every change runs first (`/feature` Gate 6) |
| `flaky` | Known unreliable. A failure goes in the evidence and does not halt the gate (none today; #58, #76) |
