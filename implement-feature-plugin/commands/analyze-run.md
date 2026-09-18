---
description: Analyze a past /implement-feature run — isolation-compliance verdicts, per-gate model/effort integrity (pinned vs actual), and token usage — from its artifact dir. Measurement only; never changes code or git.
---

# /implement-feature:analyze-run — post-run observability report

Run the deterministic analyzer over a finished (or in-flight) `/implement-feature` run and
present its Markdown report. This is **measurement, never orchestration** (P40): it reads
the run-log + session transcript and reports; it never calls a model, edits code, or
touches git.

## What it reports
- **Isolation compliance** — the guard's invariants held: test-writer stayed
  algorithm-blind, implementer never touched tests, test-reviewer never wrote the product
  tree, no agent read secrets, and the distinct subagents actually ran.
- **Per-gate model/effort integrity** — each isolated gate's **requested** pin (from its
  `agents/*.md` frontmatter) vs its **actual** model/effort (from the subagent transcript),
  with a verdict: a model mismatch is trust-voiding (**FAIL**), an effort deviation is a
  **WARN**. This is the evidence for the "reviews run on a higher model than implementation"
  invariant — and the proof each gate ran on its pinned model.
- **Per-gate token usage** — per-model token counts from the subagent transcripts.
- **Per-agent activity** — tool-call counts and files read/written.

## How to run it
The analyzer is a Python package bundled with this plugin under `implement-feature-plugin/`.
Resolve `<PLUGIN_ROOT>` = this plugin's install dir (the folder containing `analyzer/`), and
`<ARTIFACT_DIR>` = the run's `.implement-feature/<NN-slug-TS>/` dir (the value in
`.implement-feature/.active-run` for the current run, or any past run's dir):

```bash
PYTHONPATH="<PLUGIN_ROOT>" python3 -m analyzer.analyze_run --workdir "<ARTIFACT_DIR>"
```

- The run-log is derived as `<ARTIFACT_DIR>/handoff/run-log.jsonl`.
- Add `--no-transcript` for a fast isolation-only pass (skips token/cost; useful for the
  pre-approval breach check at Gate 9).
- Add `--out PATH` to also save the Markdown report to a file (parent dirs are created); it
  is still printed. Gate 11 uses this to persist `<ARTIFACT_DIR>/run-report.md`.
- `--runlog PATH` overrides `--workdir`; `--projects-dir` / `--slug` point the transcript
  reader at a non-default Claude Code projects dir.

If the user named a run/dir, use it. If they gave nothing and a run is active, read
`.implement-feature/.active-run` for the artifact dir. Present the report as-is; if it
shows an isolation **VIOLATION**, call it out plainly — but do **not** take any corrective
action automatically (the analyzer only measures; enforcement is the guard hook's job).
