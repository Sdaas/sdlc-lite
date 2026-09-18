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
    model_matches,
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


def test_model_matches_alias_accepts_any_same_family_tier():
    # An alias pin (no version digits) is satisfied by any resolved dated id in its family —
    # the transcript ALWAYS reports a resolved id, which an alias can never string-equal (#22).
    assert model_matches("sonnet", "claude-sonnet-4-5-20250929") is True
    assert model_matches("opus", "claude-opus-4-8") is True
    assert model_matches("sonnet", "claude-opus-4-8") is False   # wrong family


def test_model_matches_dated_pin_demands_exact_id():
    # A dated/explicit pin (has version digits) demands an EXACT id — a silent tier drift
    # within the same family is a mismatch, honoring the dated pin's reproducibility intent.
    assert model_matches("claude-opus-4-8", "claude-opus-4-8") is True
    assert model_matches("claude-opus-4-8", "claude-opus-5") is False  # same family, drifted
    assert model_matches("claude-opus-4-8", "claude-sonnet-4-5") is False


def test_classify_model_alias_pin_is_pass_against_resolved_id():
    # The producers pin the `sonnet` alias; the transcript reports a resolved id -> PASS, not
    # the false FAIL a naive string-equality would give.
    assert classify_model("sonnet", "claude-sonnet-4-5-20250929") == PASS
    assert classify_model("claude-opus-4-8", "claude-opus-5") == FAIL  # dated drift


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
                   agent_type="sdlc-lite:code-reviewer")
    from analyzer.transcript import parse_transcript
    return parse_transcript(main, None, None)


def test_receipt_fills_actual_from_transcript_and_grants_from_runlog(tmp_path):
    runlog = parse_runlog(str(write_runlog(tmp_path / "rl.jsonl", [
        call("", "Read", "SKILL.md", guard_decision="allow"),
        call("sdlc-lite:code-reviewer", "Read", "src/foo.py", guard_decision="allow"),
        call("sdlc-lite:code-reviewer", "Write", "/etc/passwd", guard_decision="deny"),
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


def test_receipt_pins_fill_requested_and_drive_verdicts(tmp_path):
    # #22: with the agent-def pins supplied, the requested columns fill and the verdicts
    # compare pin vs transcript. The fixture's code-reviewer ran on claude-opus-5 while pinned
    # to the DATED claude-opus-4-8 -> model FAIL (drift); effort high==high -> PASS. The
    # conductor has no pin -> requested stays UNKNOWN (honest 'nothing to check').
    from agentdefs import AgentPin
    pins = {"code-reviewer": AgentPin(model="claude-opus-4-8", effort="high")}
    runlog = parse_runlog(str(write_runlog(tmp_path / "rl.jsonl", [
        call("", "Read", "SKILL.md", guard_decision="allow"),
        call("sdlc-lite:code-reviewer", "Read", "src/foo.py", guard_decision="allow"),
    ])))
    receipts = {r.label: r for r in
                build_receipt(runlog, _transcript(tmp_path), None, pins)}

    cr = receipts["code-reviewer"]
    assert cr.requested_model == "claude-opus-4-8" and cr.actual_model == "claude-opus-5"
    assert cr.model_verdict == FAIL                       # dated pin drifted
    assert cr.requested_effort == "high" and cr.effort_verdict == PASS

    cond = receipts["conductor"]
    assert cond.requested_model == UNKNOWN and cond.model_verdict == UNKNOWN


def test_receipt_alias_pin_passes_against_resolved_id(tmp_path):
    # A producer pinned to the `sonnet` alias, whose transcript reports a resolved dated id,
    # must read PASS (the alias/dated-aware match), never a false FAIL.
    from agentdefs import AgentPin
    projects = tmp_path / "projects"
    (projects / SLUG).mkdir(parents=True)
    main = write_transcript(projects / SLUG / "s.jsonl",
                            [assistant_turn("claude-opus-4-8", i=1, effort="medium")])
    write_subagent(main, "impl", [assistant_turn("claude-sonnet-4-5-20250929", i=2,
                                                  effort="medium")],
                   agent_type="sdlc-lite:implementer")
    from analyzer.transcript import parse_transcript
    t = parse_transcript(main, None, None)
    runlog = parse_runlog(str(write_runlog(tmp_path / "rl.jsonl", [
        call("sdlc-lite:implementer", "Read", "x.py", guard_decision="allow"),
    ])))
    pins = {"implementer": AgentPin(model="sonnet", effort="medium")}
    r = {x.label: x for x in build_receipt(runlog, t, None, pins)}["implementer"]
    assert r.requested_model == "sonnet" and r.actual_model == "claude-sonnet-4-5-20250929"
    assert r.model_verdict == PASS and r.effort_verdict == PASS


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
        call("sdlc-lite:verifier", "Bash", "pytest", guard_decision="allow"),
        call("sdlc-lite:implementer", "Read", "x.py", guard_decision="allow"),
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
        call("sdlc-lite:implementer", "Read", "x.py", guard_decision="allow"),
        call("sdlc-lite:implementer", "Read", "y.py", guard_decision="allow"),
    ])))
    r = build_receipt(runlog, None)[0]
    assert r.actual_model == UNKNOWN and r.actual_effort == UNKNOWN
    assert (r.grants, r.denies) == (2, 0)


# --- #30 R4: the content audit fills the 'Files seen' column ----------------

def _runlog_tw(tmp_path):
    return parse_runlog(str(write_runlog(tmp_path / "rl.jsonl", [
        call("sdlc-lite:test-writer", "Read", "handoff/x.md", guard_decision="allow"),
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
        call("sdlc-lite:test-writer", "Read", "handoff/x.md", guard_decision="allow"),
    ])))
    audit = AuditResult(scanned_agents=["test-writer"])
    cond = {x.label: x for x in build_receipt(runlog, None, audit)}["conductor"]
    assert cond.files_verdict == UNKNOWN and cond.files_content_seen == UNKNOWN


def test_files_column_no_audit_is_unknown(tmp_path):
    # audit=None (no transcript) -> UNKNOWN, never a silent PASS.
    r = build_receipt(_runlog_tw(tmp_path), None, None)[0]
    assert r.files_verdict == UNKNOWN and r.files_content_seen == UNKNOWN
