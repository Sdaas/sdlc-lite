"""Observability analyzer for /implement-feature.

A DETERMINISTIC, after-the-fact reporter — measurement, never orchestration
(see the Developer Guide, ADR-5). It reads the two pieces of evidence a finished run leaves
behind and prints a Markdown report. It never calls a model, never makes a
decision, never drives a gate.

Two independent readers, deliberately decoupled:
  - runlog.py     LOAD-BEARING. Parses the guard hook's if-runlog.jsonl. Always
                  available; produces per-agent stats + isolation verdicts.
  - transcript.py BEST-EFFORT satellite. Parses the Claude Code session
                  transcript for per-agent model/token/cost. Its failure is
                  quarantined and reported loudly; it can never break runlog.py.

report.py assembles both into Markdown; analyze_run.py is the CLI entry point.
"""
