"""Tests for the #31 per-agent trust receipt (schema skeleton)."""
from __future__ import annotations

from analyzer.receipt import (
    FAIL,
    PASS,
    UNKNOWN,
    WARN,
    build_receipt,
    classify_effort,
    classify_model,
)
from analyzer.runlog import parse_runlog

from .conftest import assistant_turn, call, write_runlog, write_subagent, write_transcript

SLUG = "proj"


# --- verdict classifiers ---------------------------------------------------

def test_classify_model_pass_fail_unknown():
    assert classify_model("claude-opus-4-8", "claude-opus-4-8") == PASS
    assert classify_model("claude-opus-4-8", "claude-sonnet-5") == FAIL  # mismatch is trust-voiding
    assert classify_model(UNKNOWN, "claude-opus-4-8") == UNKNOWN         # skeleton state
    assert classify_model("claude-opus-4-8", UNKNOWN) == UNKNOWN         # transcript blind


def test_classify_effort_widened_both_directions_warn():
    assert classify_effort("medium", "medium") == PASS
    assert classify_effort("high", "medium") == WARN   # downgrade
    assert classify_effort("medium", "high") == WARN   # upgrade (widened policy: both directions)
    assert classify_effort(UNKNOWN, "medium") == UNKNOWN
    assert classify_effort("medium", UNKNOWN) == UNKNOWN


# --- build_receipt ---------------------------------------------------------

def _transcript(tmp_path):
    projects = tmp_path / "projects"
    (projects / SLUG).mkdir(parents=True)
    main = write_transcript(projects / SLUG / "s.jsonl",
                            [assistant_turn("claude-opus-4-8", i=1, effort="medium")])
    write_subagent(main, "agent-1",
                   [assistant_turn("claude-opus-5", i=2, effort="high")],
                   agent_type="implement-feature:code-reviewer")
    from analyzer.transcript import parse_transcript
    return parse_transcript(main, None, None)


def test_receipt_fills_actual_from_transcript_and_grants_from_runlog(tmp_path):
    runlog = parse_runlog(str(write_runlog(tmp_path / "rl.jsonl", [
        call("", "Read", "SKILL.md", guard_decision="allow"),
        call("implement-feature:code-reviewer", "Read", "src/foo.py", guard_decision="allow"),
        call("implement-feature:code-reviewer", "Write", "/etc/passwd", guard_decision="deny"),
    ])))
    receipts = {r.label: r for r in build_receipt(runlog, _transcript(tmp_path))}

    cond = receipts["conductor"]
    assert cond.actual_model == "claude-opus-4-8"
    assert cond.actual_effort == "medium"
    assert (cond.grants, cond.denies) == (1, 0)

    cr = receipts["code-reviewer"]
    assert cr.actual_model == "claude-opus-5"
    assert cr.actual_effort == "high"
    assert (cr.grants, cr.denies) == (1, 1)


def test_receipt_verdicts_unknown_in_skeleton_state(tmp_path):
    runlog = parse_runlog(str(write_runlog(tmp_path / "rl.jsonl", [
        call("", "Read", "SKILL.md", guard_decision="allow"),
    ])))
    r = build_receipt(runlog, _transcript(tmp_path))[0]  # conductor
    # Requested side unfilled (#22) and files-seen unfilled (#30) => honest UNKNOWN.
    assert r.requested_model == UNKNOWN and r.requested_effort == UNKNOWN
    assert r.files_content_seen == UNKNOWN
    assert r.model_verdict == UNKNOWN and r.effort_verdict == UNKNOWN


def test_receipt_conductor_first_then_alphabetical(tmp_path):
    runlog = parse_runlog(str(write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:verifier", "Bash", "pytest", guard_decision="allow"),
        call("implement-feature:implementer", "Read", "x.py", guard_decision="allow"),
        call("", "Read", "SKILL.md", guard_decision="allow"),
    ])))
    labels = [r.label for r in build_receipt(runlog, None)]
    assert labels[0] == "conductor"
    assert labels[1:] == sorted(labels[1:])


def test_receipt_carries_transcript_source_file_for_cross_check(tmp_path):
    runlog = parse_runlog(str(write_runlog(tmp_path / "rl.jsonl", [
        call("", "Read", "SKILL.md", guard_decision="allow"),
    ])))
    receipts = {r.label: r for r in build_receipt(runlog, _transcript(tmp_path))}
    assert receipts["conductor"].transcript_file.endswith("s.jsonl")
    assert receipts["code-reviewer"].transcript_file.endswith("agent-1.jsonl")


def test_receipt_without_transcript_actual_columns_unknown_grants_intact(tmp_path):
    # No transcript at all (absent/drift/disabled) -> actual model/effort UNKNOWN, but the
    # run-log-derived grant/deny survive (R5: never a silent PASS).
    runlog = parse_runlog(str(write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:implementer", "Read", "x.py", guard_decision="allow"),
        call("implement-feature:implementer", "Read", "y.py", guard_decision="allow"),
    ])))
    r = build_receipt(runlog, None)[0]
    assert r.actual_model == UNKNOWN and r.actual_effort == UNKNOWN
    assert (r.grants, r.denies) == (2, 0)


# --- #30 R4: the content audit fills the 'Files seen' column ----------------

def _runlog_tw(tmp_path):
    return parse_runlog(str(write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:test-writer", "Read", "handoff/x.md", guard_decision="allow"),
    ])))


def test_files_column_leak_is_fail(tmp_path):
    from analyzer.auditor import AuditResult, LeakFinding
    audit = AuditResult(
        findings=[LeakFinding(agent_label="test-writer", artifact="/r/handoff/03-design-internal.md",
                              rule="algorithm-blind", matched_excerpt="…", session_file="s.jsonl")],
        scanned_agents=["test-writer"],
        protected_artifacts=["/r/handoff/03-design-internal.md"])
    r = {x.label: x for x in build_receipt(_runlog_tw(tmp_path), None, audit)}["test-writer"]
    assert r.files_verdict == FAIL
    assert r.files_content_seen == "LEAK: 03-design-internal.md"


def test_files_column_scanned_clean_is_pass_none(tmp_path):
    from analyzer.auditor import AuditResult
    audit = AuditResult(scanned_agents=["test-writer"],
                        protected_artifacts=["/r/handoff/03-design-internal.md"])
    r = {x.label: x for x in build_receipt(_runlog_tw(tmp_path), None, audit)}["test-writer"]
    assert r.files_verdict == PASS
    assert r.files_content_seen == "none"


def test_files_column_unscanned_agent_is_unknown(tmp_path):
    # The auditor never scans the conductor (not an isolated gate) -> honest UNKNOWN, not PASS.
    from analyzer.auditor import AuditResult
    runlog = parse_runlog(str(write_runlog(tmp_path / "rl.jsonl", [
        call("", "Read", "SKILL.md", guard_decision="allow"),
        call("implement-feature:test-writer", "Read", "handoff/x.md", guard_decision="allow"),
    ])))
    audit = AuditResult(scanned_agents=["test-writer"])
    cond = {x.label: x for x in build_receipt(runlog, None, audit)}["conductor"]
    assert cond.files_verdict == UNKNOWN and cond.files_content_seen == UNKNOWN


def test_files_column_no_audit_is_unknown(tmp_path):
    # audit=None (no transcript) -> UNKNOWN, never a silent PASS.
    r = build_receipt(_runlog_tw(tmp_path), None, None)[0]
    assert r.files_verdict == UNKNOWN and r.files_content_seen == UNKNOWN
