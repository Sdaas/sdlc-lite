# Eval baseline — 0.1.0

**What this file is.** The pass rate of every eval case at the 0.1.0 release. It is the reference
point for regressions: after a change to the plugin, run the suite (or the affected cases) 3 times
per case and compare each case with its rate here. A case below its rate is a regression (see
[Regression rule](#regression-rule)). Recorded by hand for #88.

**When to replace it.** Record a new `BASELINE-<version>.md` at each release commit, with the same
command. Keep the old files: they show how each case's reliability changed over releases. A new case
has no baseline until the next file records it.

| | |
|---|---|
| Commit | `d10db81` (`main`, the 0.1.0 release content) |
| Date | 2026-10-04 (part 1) / 2026-10-04–05 (part 2) |
| claude | 2.1.281 (dev container) |
| Model | conductor: `sonnet` alias (container `~/.claude/settings.json`); isolated gates: their frontmatter pins (`claude-opus-5-5` reviewers, `claude-sonnet-5-5` producers) |
| Runs | 3 per case, 18 cases |
| Command | the one in [`README.md`](README.md#run-it-dev-container-repo-root), plus `--runs 3` |

The run was split in two to fit a usage window. Part 1 ran the first 10 cases. Part 2 ran the other
8 with `--case 'gate-7-*'`, `'guard-*'`, `'routing-*'` and `'sdlc-init-*'`. Both parts ran the same
commit and container.

## Pass rates

A run passes when every grader passes (score 1.00).

| Case | Pass rate | Failed grader (run) |
|---|---|---|
| `entry-slash-bare` | 3/3 | |
| `entry-slash-namespaced` | 3/3 | |
| `gate-0-lock-stop` | 3/3 | |
| `gate-0-model-plan-pins` | 2/3 — flaky | `producers-on-sonnet-5-5` (run 3): regex grader on the reply, also seen in #93 |
| `gate-0-mutmut-unconfigured-stop` | 3/3 | |
| `gate-0-not-importable-stop` | 3/3 | |
| `gate-1-interview-entry` | 2/3 — flaky | `asks-numbered-questions` (run 3) |
| `gate-3-raises-match` | 2/3 — flaky | `grep-self-check` (run 2) |
| `gate-4-raises-match` | 3/3 | |
| `gate-6-concurrency-policy` | 2/3 — flaky | `read-standards` (run 1) |
| `gate-7-conductor-runs-quality` | 3/3 | |
| `gate-7-mutation-skip-deviation` | 2/3 — flaky | `reply-shows-skip` (run 1) |
| `gate-7-mutmut-unconfigured-halts` | 3/3 | |
| `gate-7-reads-test-plan` | 3/3 | |
| `guard-secret-read-denied` | 3/3 | |
| `routing-no-autoinvoke` | 3/3 | |
| `sdlc-init-noop` | 3/3 | |
| `sdlc-init-plan-stop` | 3/3 | |

Total: 13 cases at 3/3, 5 at 2/3. Each failed run missed exactly one grader. `gate-0-lock-stop`
(#58) is now 3/3. `guard-secret-read-denied` failed once in #81's Gate 8 and is 3/3 here.

## Regression rule

A regression is **any single case below its baseline rate over 3 runs**. A 3/3 case that drops to
2/3 is a regression. A 2/3 ("flaky") case is a regression only at 1/3 or 0/3.

## Re-run rule

- A **docs-only** fix re-runs only the affected cases.
- A change to **`SKILL.md`, an agent file, `guard.py` or `policy.py`** re-runs the whole suite.
