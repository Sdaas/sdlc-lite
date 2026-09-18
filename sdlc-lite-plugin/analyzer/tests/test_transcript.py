"""Tests for the best-effort transcript satellite: parsing + both degradations."""
from __future__ import annotations

import datetime as dt

import pytest

from analyzer.transcript import (
    TranscriptAbsent,
    TranscriptFormatError,
    find_transcript,
    parse_subagents,
    parse_transcript,
)

from .conftest import assistant_turn, write_subagent, write_transcript

WIN_START = dt.datetime(2026, 9, 9, 7, 40, 0, tzinfo=dt.timezone.utc)
WIN_END = dt.datetime(2026, 9, 9, 7, 40, 9, tzinfo=dt.timezone.utc)


def test_parse_aggregates_main_vs_sidechain_by_model(tmp_path):
    tpath = write_transcript(tmp_path / "s.jsonl", [
        assistant_turn("claude-opus-4-8", i=1, input_tokens=100, output_tokens=40),
        assistant_turn("claude-opus-4-8", i=2, input_tokens=100, output_tokens=40),
        assistant_turn("claude-sonnet-5", sidechain=True, i=3, input_tokens=10, output_tokens=5),
    ])
    a = parse_transcript(tpath, WIN_START, WIN_END)
    assert a.turns_in_window == 3
    assert a.main["claude-opus-4-8"].turns == 2
    assert a.main["claude-opus-4-8"].input_tokens == 200
    assert a.main["claude-opus-4-8"].output_tokens == 80
    assert a.sidechain["claude-sonnet-5"].turns == 1
    assert "claude-opus-4-8" not in a.sidechain


def test_find_transcript_picks_overlapping_file(tmp_path):
    good = write_transcript(tmp_path / "good.jsonl", [assistant_turn("m", i=2)])
    # An unrelated session far outside the window.
    off = tmp_path / "off.jsonl"
    off.write_text(
        '{"type":"assistant","timestamp":"2020-01-01T00:00:00.000Z",'
        '"message":{"model":"m","usage":{"input_tokens":1,"output_tokens":1}}}\n',
        encoding="utf-8",
    )
    picked = find_transcript(tmp_path, WIN_START, WIN_END)
    assert picked == good


def test_find_transcript_absent_when_no_overlap(tmp_path):
    (tmp_path / "old.jsonl").write_text(
        '{"type":"assistant","timestamp":"2020-01-01T00:00:00.000Z",'
        '"message":{"model":"m","usage":{"input_tokens":1,"output_tokens":1}}}\n',
        encoding="utf-8",
    )
    with pytest.raises(TranscriptAbsent):
        find_transcript(tmp_path, WIN_START, WIN_END)


def test_find_transcript_absent_when_dir_missing(tmp_path):
    with pytest.raises(TranscriptAbsent):
        find_transcript(tmp_path / "nope", WIN_START, WIN_END)


def test_schema_drift_raises_format_error(tmp_path):
    # Assistant turns present, but NONE carry model/usage -> loud drift alarm.
    tpath = write_transcript(tmp_path / "drift.jsonl", [
        assistant_turn("whatever", i=1, with_usage=False),
        assistant_turn("whatever", i=2, with_usage=False),
    ])
    with pytest.raises(TranscriptFormatError) as exc:
        parse_transcript(tpath, WIN_START, WIN_END)
    assert "format has likely changed" in str(exc.value)


def test_no_assistant_turns_is_absent_not_drift(tmp_path):
    tpath = tmp_path / "empty.jsonl"
    tpath.write_text('{"type":"user","message":{}}\n', encoding="utf-8")
    with pytest.raises(TranscriptAbsent):
        parse_transcript(tpath, WIN_START, WIN_END)


# --- #31 R3: per-turn top-level `effort` extraction ------------------------

def test_effort_extracted_and_split_main_vs_sidechain(tmp_path):
    tpath = write_transcript(tmp_path / "s.jsonl", [
        assistant_turn("claude-opus-4-8", i=1, effort="high"),
        assistant_turn("claude-opus-4-8", i=2, effort="high"),
        assistant_turn("claude-opus-4-8", i=3, effort="medium"),
        assistant_turn("claude-sonnet-5", sidechain=True, i=4, effort="low"),
    ])
    a = parse_transcript(tpath, WIN_START, WIN_END)
    assert a.main_efforts == {"high": 2, "medium": 1}
    assert a.sidechain_efforts == {"low": 1}


def test_effort_absent_leaves_empty_not_invented(tmp_path):
    # No top-level effort field at all -> no buckets (verdict later degrades to UNKNOWN).
    tpath = write_transcript(tmp_path / "s.jsonl", [assistant_turn("claude-opus-4-8", i=1)])
    a = parse_transcript(tpath, WIN_START, WIN_END)
    assert a.main_efforts == {}
    assert a.sidechain_efforts == {}


def test_subagent_effort_captured_and_folded_into_sidechain(tmp_path):
    main = write_transcript(tmp_path / "abc.jsonl",
                            [assistant_turn("claude-opus-4-8", i=1, effort="medium")])
    write_subagent(main, "agent-1", [
        assistant_turn("claude-opus-5", i=2, effort="high"),
        assistant_turn("claude-opus-5", i=3, effort="high"),
    ], agent_type="sdlc-lite:code-reviewer")
    a = parse_transcript(main, WIN_START, WIN_END)
    labels = {s.agent_label: s for s in a.subagents}
    assert labels["code-reviewer"].efforts == {"high": 2}
    # Folded into the sidechain effort aggregate; the main thread keeps its own.
    assert a.sidechain_efforts == {"high": 2}
    assert a.main_efforts == {"medium": 1}


# --- #15: subagent transcripts under <uuid>/subagents/*.jsonl --------------

def test_subagents_parsed_and_attributed_and_folded_into_sidechain(tmp_path):
    main = write_transcript(tmp_path / "abc.jsonl", [assistant_turn("claude-opus-4-8", i=1)])
    write_subagent(main, "agent-1", [
        assistant_turn("claude-opus-5", i=2, input_tokens=100, output_tokens=40),
        assistant_turn("claude-opus-5", i=3, input_tokens=100, output_tokens=40),
    ], agent_type="sdlc-lite:code-reviewer")
    write_subagent(main, "agent-2",
                   [assistant_turn("claude-sonnet-5", i=4, input_tokens=10, output_tokens=5)],
                   agent_type="sdlc-lite:implementer")

    a = parse_transcript(main, WIN_START, WIN_END)
    # Per-subagent breakdown attributed via .meta.json (namespace stripped).
    labels = {s.agent_label: s for s in a.subagents}
    assert set(labels) == {"code-reviewer", "implementer"}
    assert labels["code-reviewer"].by_model["claude-opus-5"].turns == 2
    assert labels["code-reviewer"].by_model["claude-opus-5"].input_tokens == 200
    # Folded into the sidechain aggregate-by-model too.
    assert a.sidechain["claude-opus-5"].turns == 2
    assert a.sidechain["claude-sonnet-5"].turns == 1
    # Main thread is unaffected.
    assert a.main["claude-opus-4-8"].turns == 1


def test_subagent_label_falls_back_to_stem_without_meta(tmp_path):
    main = write_transcript(tmp_path / "abc.jsonl", [assistant_turn("claude-opus-4-8", i=1)])
    write_subagent(main, "agent-xyz", [assistant_turn("claude-sonnet-5", i=2)])  # no meta
    a = parse_transcript(main, WIN_START, WIN_END)
    assert [s.agent_label for s in a.subagents] == ["agent-xyz"]


def test_missing_subagents_dir_yields_empty(tmp_path):
    main = write_transcript(tmp_path / "abc.jsonl", [assistant_turn("claude-opus-4-8", i=1)])
    assert parse_subagents(main) == []
    a = parse_transcript(main, WIN_START, WIN_END)
    assert a.subagents == []


def test_malformed_subagent_file_is_skipped_not_raised(tmp_path):
    main = write_transcript(tmp_path / "abc.jsonl", [assistant_turn("claude-opus-4-8", i=1)])
    sdir = tmp_path / "abc" / "subagents"
    sdir.mkdir(parents=True)
    (sdir / "broken.jsonl").write_text("not json at all\n{also bad\n", encoding="utf-8")
    write_subagent(main, "good", [assistant_turn("claude-sonnet-5", i=2)],
                   agent_type="sdlc-lite:verifier")
    # Must not raise; the good subagent is still parsed, the main analysis intact.
    a = parse_transcript(main, WIN_START, WIN_END)
    assert [s.agent_label for s in a.subagents] == ["verifier"]
