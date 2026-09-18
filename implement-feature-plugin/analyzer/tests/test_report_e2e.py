"""End-to-end tests for build_report: the transcript quarantine in action."""
from __future__ import annotations

from analyzer.analyze_run import build_report, main

from .conftest import assistant_turn, call, write_runlog, write_subagent, write_transcript

SLUG = "proj"

SECRET_LINE = ("The internal algorithm memoizes partial sums over a monotonic deque to "
               "bound the sliding window in O(n).")
DESIGN_INTERNAL = "# Internal design\n\n" + SECRET_LINE + "\n"


def _bash_leak_record(content: str) -> dict:
    """A subagent `user` record whose Bash stdout carries a leaked file's content — the
    on-disk shape of a `cat handoff/*.md` glob leak (TRANSCRIPT-FORMAT.md §5)."""
    return {"type": "user", "toolUseResult": {"stdout": content, "stderr": ""},
            "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": content}]}}


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


# --- #30 R4/R5: the content audit, end to end ------------------------------

def test_content_audit_present_and_clean_when_no_leak(tmp_path):
    # A test-writer that only ever saw the interface design -> content audit is clean.
    runlog = _runlog(tmp_path)
    projects = tmp_path / "projects"
    (projects / SLUG).mkdir(parents=True)
    main_t = write_transcript(projects / SLUG / "s.jsonl", [assistant_turn("claude-opus-4-8", i=1)])
    # The forbidden artifact exists in the handoff dir (= the run-log's dir) but never leaks.
    (tmp_path / "03-design-internal.md").write_text(DESIGN_INTERNAL, encoding="utf-8")
    write_subagent(main_t, "agent-1",
                   [assistant_turn("claude-opus-5", i=2),
                    _bash_leak_record("some innocent test output, nothing forbidden")],
                   agent_type="implement-feature:test-writer")
    out = build_report(runlog, projects, SLUG)
    assert "Content isolation audit (authoritative" in out
    assert "No forbidden content reached any isolated gate" in out
    assert "UNTRUSTED" not in out


def test_adversarial_glob_leak_flips_run_to_untrusted(tmp_path):
    # THE acceptance case: a test-writer's `cat handoff/*.md` dumps the internal design into
    # its Bash stdout. The run-log/guard are blind to the glob; the content audit catches it.
    runlog = str(write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:test-writer", "Bash", "cat handoff/*.md", guard_decision="allow"),
    ]))
    projects = tmp_path / "projects"
    (projects / SLUG).mkdir(parents=True)
    main_t = write_transcript(projects / SLUG / "s.jsonl", [assistant_turn("claude-opus-4-8", i=1)])
    (tmp_path / "03-design-internal.md").write_text(DESIGN_INTERNAL, encoding="utf-8")
    write_subagent(main_t, "agent-1",
                   [assistant_turn("claude-opus-5", i=2), _bash_leak_record(DESIGN_INTERNAL)],
                   agent_type="implement-feature:test-writer")
    out = build_report(runlog, projects, SLUG)
    assert "CONTENT LEAK DETECTED" in out
    assert "THIS RUN IS UNTRUSTED" in out
    assert "03-design-internal.md" in out
    # And the receipt's Files-seen column carries the FAIL through to the headline table.
    assert "LEAK: 03-design-internal.md" in out


def test_content_audit_unknown_without_transcript(tmp_path):
    # No transcript -> the content audit is UNKNOWN (unproven), never a silent pass.
    out = build_report(_runlog(tmp_path), tmp_path / "projects", SLUG)  # projects absent
    assert "Content isolation audit (authoritative" in out
    assert "UNKNOWN — not run" in out
    assert "unproven, not passed" in out


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
