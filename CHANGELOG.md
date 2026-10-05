# Changelog

What changed in each `sdlc-lite` release, newest first. Install and update steps: [README](README.md).
The GitHub Release for each version carries the same text.

## 0.1.0 — 2026-10-05

The first release that sets your repo up for you and leaves your environment alone.

### New features

- **`/sdlc-init` sets up a Python repo for `/implement-feature`.** It shows the tools that are
  missing or too old and the config that is missing. After one approval, it installs the tools into
  the active environment, adds the config, and runs a mutation-testing smoke test. It never
  commits. A second run changes nothing.
- **Gate 0 stops on a repo that is not set up.** It checks all seven tool versions and the mutmut
  config, then tells you to run `/sdlc-init`.
- **The conductor measures coverage and mutation testing itself.** Gate 7 writes the results to
  `quality/` in the run directory. The code reviewer only reads them.
- **Every isolated gate uses a pinned, dated model.** The test reviewer and the code reviewer use
  `claude-opus-5-5`. The test writer, the implementer and the verifier use `claude-sonnet-5-5`.

### Fixed bugs

- Outside an `/implement-feature` run, the guard hook no longer writes `if-runlog.jsonl` into your
  project root.
- A gate no longer leaves `.coverage` files or a `mutants/` directory in your project.
- A read-only reviewer can no longer run `pip install` or `pip uninstall` and change your Python
  environment.
- When a run is already in progress, the workflow now always stops first and asks you about the lock.
- A plain request for help no longer starts the workflow. Only `/implement-feature` starts it.

### Install

```bash
claude plugin marketplace add Sdaas/claude-plugins
claude plugin install sdlc-lite@sdaas
```

Then type `/reload-plugins` in your Claude Code session, and run `/sdlc-init` in your repo. Full
setup: [README](https://github.com/Sdaas/sdlc-lite#one-time-setup).

### Update from 0.0.9

```bash
claude plugin marketplace update sdaas
claude plugin update sdlc-lite
```

Then type `/reload-plugins` in your Claude Code session, or restart it. Run `/sdlc-init` once in
each repo where you use the plugin. Without it, Gate 0 stops and asks you to run it.

### All changes

[Closed issues in the 0.1.0 milestone](https://github.com/Sdaas/sdlc-lite/issues?q=milestone%3A0.1.0+is%3Aclosed),
including the internal process and tooling work.
