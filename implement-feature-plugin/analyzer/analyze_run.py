"""CLI entry point for the /implement-feature observability analyzer.

    # from inside implement-feature-plugin/ — primary handle is the run's artifact dir:
    python -m analyzer.analyze_run --workdir /path/to/.implement-feature/<run>/
    # or point straight at a run-log:
    python -m analyzer.analyze_run --runlog /path/to/run-log.jsonl

This is the ONLY place that orchestrates the two readers and quarantines the
best-effort transcript satellite. Order of operations:

  1. Parse the run-log (load-bearing). If this file is missing/unreadable, that
     is a hard, user-facing error — there is nothing to report without it.
  2. Render the run-log section (always).
  3. Attempt the transcript section inside try/except:
        TranscriptAbsent      -> soft "skipped" note
        TranscriptFormatError -> loud "format changed, update parser" alarm
        any OTHER exception   -> ALSO the loud path (unknown failure is treated
                                 as drift; silent degradation is worse than loud).

Nothing here calls a model or drives a gate — measurement only (P40).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import agentdefs

from . import report
from .auditor import audit_content_leaks
from .receipt import build_receipt
from .runlog import parse_runlog
from .transcript import (
    TranscriptAbsent,
    TranscriptAnalysis,
    TranscriptFormatError,
    find_transcript,
    parse_transcript,
)


def _default_runlog() -> str:
    return (os.environ.get("IF_RUNLOG")
            or (os.path.join(os.environ["CLAUDE_PROJECT_DIR"], "if-runlog.jsonl")
                if os.environ.get("CLAUDE_PROJECT_DIR") else None)
            or "if-runlog.jsonl")


def _default_projects_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))) / "projects"


def _slug_for(cwd: Path) -> str:
    """Claude Code names a project dir by its abs path with '/' -> '-'."""
    return str(cwd.resolve()).replace("/", "-")


def build_report(runlog_path: str, projects_root: Path | None, slug: str | None,
                 use_transcript: bool = True) -> str:
    # 1-2. Run-log: load-bearing, always rendered.
    runlog = parse_runlog(runlog_path)
    sections = [report.render_runlog(runlog)]

    # 3. Transcript: quarantined best-effort satellite. On any degradation the analysis
    #    stays None so the receipt below still renders (with UNKNOWN actual columns).
    tanalysis: TranscriptAnalysis | None = None
    if not use_transcript:
        sections.append(report.render_transcript_unavailable(
            "absent", "transcript analysis disabled (--no-transcript)."))
    else:
        try:
            projects_root = projects_root or _default_projects_dir()
            slug = slug or _slug_for(Path.cwd())
            project_dir = projects_root / slug
            tpath = find_transcript(project_dir, runlog.window_start, runlog.window_end)
            tanalysis = parse_transcript(tpath, runlog.window_start, runlog.window_end)
            sections.append(report.render_transcript(tanalysis))
        except TranscriptAbsent as e:
            sections.append(report.render_transcript_unavailable("absent", str(e)))
        except TranscriptFormatError as e:
            sections.append(report.render_transcript_unavailable("drift", str(e)))
        except Exception as e:  # noqa: BLE001 - deliberate: any unknown transcript
            # failure must route to the LOUD path; silent degradation is worse.
            tanalysis = None
            sections.append(report.render_transcript_unavailable(
                "drift", f"unexpected {type(e).__name__}: {e}"))

    # 4. Content isolation audit (#30 R3/R4) — the AUTHORITATIVE isolation signal: scan each
    #    subagent transcript's tool OUTPUT for the content of any artifact its role was
    #    forbidden to see. Needs the transcript (tool output), so it is None without one —
    #    which renders as UNKNOWN (unproven), never a silent pass. The protected artifacts
    #    live in the run's handoff dir (the dir holding the run-log).
    handoff_dir = os.path.dirname(runlog_path)
    audit = audit_content_leaks(tanalysis, handoff_dir) if tanalysis is not None else None
    sections.append(report.render_content_audit(audit))

    # 5. The trust receipt — ALWAYS rendered (the headline of the audit). Grant/deny come
    #    from the run-log; actual model/effort from the transcript when available, else
    #    UNKNOWN; REQUESTED model/effort from the agent-def pins (#22, the SSOT); the 'Files
    #    seen' column from the content audit (FAIL on a leak). load_pins() never raises.
    pins = agentdefs.load_pins()
    sections.append(report.render_receipt(
        build_receipt(runlog, tanalysis, audit, pins), runlog.path))

    return report.assemble(sections)


def _runlog_from_workdir(workdir: str) -> str:
    """A run's artifact dir holds its run-log at <workdir>/handoff/run-log.jsonl (#10)."""
    return str(Path(workdir) / "handoff" / "run-log.jsonl")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Analyze an /implement-feature run.")
    p.add_argument("--workdir", default=None,
                   help="the run's artifact dir (.implement-feature/<run>/); the run-log is "
                        "derived as <workdir>/handoff/run-log.jsonl. Primary handle.")
    p.add_argument("--runlog", default=None,
                   help="explicit path to run-log.jsonl (overrides --workdir; default: "
                        "$IF_RUNLOG or ./if-runlog.jsonl)")
    p.add_argument("--projects-dir", default=None,
                   help="Claude Code projects dir (default: ~/.claude/projects)")
    p.add_argument("--slug", default=None,
                   help="project slug under projects-dir (default: derived from cwd)")
    p.add_argument("--no-transcript", action="store_true",
                   help="skip the best-effort transcript/token analysis")
    p.add_argument("--out", default=None,
                   help="also write the Markdown report to this path (parent dirs are "
                        "created); the report is still printed to stdout. Gate 11 uses "
                        "this to persist <artifact_dir>/run-report.md.")
    args = p.parse_args(argv)

    # Resolve the run-log: explicit --runlog wins, else derive from --workdir, else default.
    runlog = args.runlog or (_runlog_from_workdir(args.workdir) if args.workdir
                             else _default_runlog())
    args.runlog = runlog

    if not Path(args.runlog).is_file():
        print(f"error: run-log not found: {args.runlog}", file=sys.stderr)
        print("(nothing to report without the run-log; pass --workdir DIR or --runlog PATH)",
              file=sys.stderr)
        return 2

    projects_root = Path(args.projects_dir) if args.projects_dir else None
    text = build_report(args.runlog, projects_root, args.slug,
                        use_transcript=not args.no_transcript)
    print(text)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
