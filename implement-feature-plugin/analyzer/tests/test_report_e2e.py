"""End-to-end tests for build_report: the transcript quarantine in action."""
from __future__ import annotations

from analyzer.analyze_run import build_report, main

from .conftest import assistant_turn, call, write_runlog, write_subagent, write_transcript

SLUG = "proj"


def _runlog(tmp_path):
    return str(write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:test-writer", "Read", "handoff/design-interface.md",
             guard_decision="allow"),
        call("implement-feature:implementer", "Write", "src/foo.py", guard_decision="allow"),
    ]))


def test_transcript_present_renders_token_table(tmp_path):
    runlog = _runlog(tmp_path)
    projects = tmp_path / "projects"
    (projects / SLUG).mkdir(parents=True)
    write_transcript(projects / SLUG / "s.jsonl", [
        assistant_turn("claude-opus-4-8", i=1),
        assistant_turn("claude-sonnet-5", sidechain=True, i=2),
    ])
    out = build_report(runlog, projects, SLUG)
    assert "Run-log analysis" in out
    assert "Token / cost analysis" in out
    assert "claude-opus-4-8" in out
    assert "TRANSCRIPT ANALYSIS UNAVAILABLE" not in out


def test_subagent_breakdown_rendered_in_report(tmp_path):
    runlog = _runlog(tmp_path)
    projects = tmp_path / "projects"
    (projects / SLUG).mkdir(parents=True)
    main = write_transcript(projects / SLUG / "s.jsonl", [assistant_turn("claude-opus-4-8", i=1)])
    write_subagent(main, "agent-1", [assistant_turn("claude-opus-5", i=2)],
                   agent_type="implement-feature:code-reviewer")
    out = build_report(runlog, projects, SLUG)
    assert "Per-subagent (isolated gates)" in out
    assert "code-reviewer" in out
    assert "claude-opus-5" in out
    assert "Subagent transcripts found: **1**" in out


def test_receipt_rendered_with_actual_columns_from_transcript(tmp_path):
    runlog = _runlog(tmp_path)
    projects = tmp_path / "projects"
    (projects / SLUG).mkdir(parents=True)
    write_transcript(projects / SLUG / "s.jsonl",
                     [assistant_turn("claude-opus-4-8", i=1, effort="medium")])
    out = build_report(runlog, projects, SLUG)
    assert "Per-agent trust receipt" in out
    assert "UNKNOWN → claude-opus-4-8" in out   # requested still UNKNOWN (#22), actual filled
    assert "UNKNOWN → medium" in out


def test_missing_transcript_degrades_softly_runlog_intact(tmp_path):
    runlog = _runlog(tmp_path)
    projects = tmp_path / "projects"  # never created -> absent
    out = build_report(runlog, projects, SLUG)
    assert "Run-log analysis" in out
    assert "Skipped — no transcript found" in out
    assert "TRANSCRIPT ANALYSIS UNAVAILABLE" not in out  # soft, not loud
    # R5: the receipt still renders, with actual columns degraded to UNKNOWN (never PASS).
    assert "Per-agent trust receipt" in out
    assert "❔" in out


def test_transcript_drift_degrades_loudly_runlog_intact(tmp_path):
    runlog = _runlog(tmp_path)
    projects = tmp_path / "projects"
    (projects / SLUG).mkdir(parents=True)
    # Assistant turns with no model/usage in the window -> format drift.
    write_transcript(projects / SLUG / "s.jsonl", [
        assistant_turn("x", i=1, with_usage=False),
    ])
    out = build_report(runlog, projects, SLUG)
    assert "Run-log analysis" in out                       # load-bearing intact
    assert "TRANSCRIPT ANALYSIS UNAVAILABLE" in out         # loud alarm
    assert "transcript.py" in out                           # points at the fix


def test_no_transcript_flag_skips_cleanly(tmp_path):
    out = build_report(_runlog(tmp_path), None, None, use_transcript=False)
    assert "Run-log analysis" in out
    assert "--no-transcript" in out


def test_out_flag_saves_report_and_still_prints(tmp_path, capsys):
    runlog = _runlog(tmp_path)
    out_path = tmp_path / "run-report.md"
    rc = main(["--runlog", runlog, "--no-transcript", "--out", str(out_path)])
    assert rc == 0
    printed = capsys.readouterr().out
    assert "Run-log analysis" in printed          # still printed to stdout
    assert out_path.is_file()                      # and persisted to --out
    assert out_path.read_text().strip() == printed.strip()


def test_out_flag_creates_missing_parent_dirs(tmp_path):
    runlog = _runlog(tmp_path)
    out_path = tmp_path / "nested" / "dir" / "run-report.md"
    assert main(["--runlog", runlog, "--no-transcript", "--out", str(out_path)]) == 0
    assert out_path.is_file()
    assert "Run-log analysis" in out_path.read_text()
