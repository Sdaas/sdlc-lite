"""Tests for the transcript content auditor (#30 R3) — the AUTHORITATIVE isolation signal.

Each test builds a real subagent transcript file whose tool output carries (or does not
carry) the protected artifact's content, then asserts the fingerprint scan's verdict. The
leak vectors mirror the on-disk shapes discovered in TRANSCRIPT-FORMAT.md §5: Bash
`stdout`, Read `file.content`, and the line-number-prefixed model-facing `tool_result`
block.
"""
from __future__ import annotations

import json
from pathlib import Path

from analyzer.auditor import audit_content_leaks
from analyzer.transcript import SubagentUsage, TranscriptAnalysis

# A distinctive line (>40 chars normalized) that only the internal design would contain.
SECRET_LINE = ("The internal algorithm uses a two-pointer sweep with a monotonic deque "
               "to bound the sliding window in O(n).")
DESIGN_INTERNAL = ("# Internal design\n\n" + SECRET_LINE + "\n\nStep 2: memoize the partial sums.\n")
DESIGN_INTERFACE = ("# Interface\n\nparse_duration(s: str) -> int  # '1h30m' -> seconds\n")


def _handoff(tmp_path: Path) -> str:
    """A run handoff dir with a protected internal design + an innocent interface design."""
    h = tmp_path / "handoff"
    h.mkdir(exist_ok=True)
    (h / "03-design-internal.md").write_text(DESIGN_INTERNAL, encoding="utf-8")
    (h / "02-design-interface.md").write_text(DESIGN_INTERFACE, encoding="utf-8")
    return str(h)


def _user_tool_result(*, content=None, tool_use_result=None) -> dict:
    rec: dict = {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": content if content is not None else ""},
    ]}}
    if tool_use_result is not None:
        rec["toolUseResult"] = tool_use_result
    return rec


def _assistant_tool_use(name: str, **inp) -> dict:
    return {"type": "assistant", "isSidechain": True, "message": {"content": [
        {"type": "tool_use", "id": "t1", "name": name, "input": inp},
    ]}}


def _write_sub(tmp_path: Path, records: list[dict], name: str = "agent-x.jsonl") -> str:
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return str(p)


def _transcript(label: str, session_file: str) -> TranscriptAnalysis:
    t = TranscriptAnalysis(session_file="main.jsonl", turns_in_window=0)
    t.subagents = [SubagentUsage(agent_label=label, session_file=session_file)]
    return t


# --- leak vectors ----------------------------------------------------------
def test_leak_via_bash_stdout_glob_is_authoritative(tmp_path):
    # The glob blind spot: `cat handoff/*.md` exposes no path, only the command — but the
    # file CONTENT lands in Bash stdout, which the content-fingerprint catches.
    sess = _write_sub(tmp_path, [
        _assistant_tool_use("Bash", command="cat handoff/*.md"),
        _user_tool_result(tool_use_result={"stdout": DESIGN_INTERNAL, "stderr": ""}),
    ])
    res = audit_content_leaks(_transcript("test-writer", sess), _handoff(tmp_path))
    assert not res.trusted
    assert len(res.findings) == 1
    f = res.findings[0]
    assert f.agent_label == "test-writer"
    assert f.artifact.endswith("03-design-internal.md")
    assert f.rule == "algorithm-blind"
    assert "two-pointer sweep" in f.matched_excerpt


def test_leak_via_read_file_content(tmp_path):
    sess = _write_sub(tmp_path, [
        _assistant_tool_use("Read", file_path="handoff/03-design-internal.md"),
        _user_tool_result(tool_use_result={
            "type": "text",
            "file": {"filePath": "handoff/03-design-internal.md", "content": DESIGN_INTERNAL}}),
    ])
    res = audit_content_leaks(_transcript("test-writer", sess), _handoff(tmp_path))
    assert not res.trusted
    # The explicit Read path corroborates (non-authoritative), naming the leaked file.
    assert "03-design-internal.md" in res.findings[0].corroboration


def test_leak_via_line_numbered_model_facing_block(tmp_path):
    # No toolUseResult; only the model-facing tool_result block, line-number-prefixed
    # (`cat -n` / Read style). Normalization must strip the `N\t` prefix to still match.
    numbered = "\n".join(f"{i+1}\t{ln}" for i, ln in enumerate(DESIGN_INTERNAL.splitlines()))
    sess = _write_sub(tmp_path, [_user_tool_result(content=numbered)])
    res = audit_content_leaks(_transcript("test-writer", sess), _handoff(tmp_path))
    assert not res.trusted
    assert res.findings[0].artifact.endswith("03-design-internal.md")


# --- clean / not-forbidden -------------------------------------------------
def test_clean_run_no_leak_is_trusted(tmp_path):
    # test-writer only ever saw the interface design — never the internal one.
    sess = _write_sub(tmp_path, [
        _assistant_tool_use("Read", file_path="handoff/02-design-interface.md"),
        _user_tool_result(tool_use_result={
            "type": "text", "file": {"filePath": "…", "content": DESIGN_INTERFACE}}),
    ])
    res = audit_content_leaks(_transcript("test-writer", sess), _handoff(tmp_path))
    assert res.trusted
    assert not res.findings
    assert "test-writer" in res.scanned_agents
    # It WAS checked against the internal design (proves the scan ran, not that it was skipped).
    assert any(p.endswith("03-design-internal.md") for p in res.protected_artifacts)


def test_role_allowed_to_see_artifact_is_not_a_leak(tmp_path):
    # The implementer legitimately reads the internal design — seeing its content is fine,
    # so the same tool output that condemns the test-writer is clean for the implementer.
    sess = _write_sub(tmp_path, [
        _user_tool_result(tool_use_result={"stdout": DESIGN_INTERNAL, "stderr": ""}),
    ])
    res = audit_content_leaks(_transcript("implementer", sess), _handoff(tmp_path))
    assert res.trusted
    assert not res.protected_artifacts  # nothing is content-protected FROM the implementer


# --- best-effort / defensive ----------------------------------------------
def test_no_transcript_is_trusted_empty(tmp_path):
    assert audit_content_leaks(None, _handoff(tmp_path)).trusted
    assert audit_content_leaks(None, _handoff(tmp_path)).findings == []


def test_no_handoff_dir_is_trusted_empty(tmp_path):
    sess = _write_sub(tmp_path, [_user_tool_result(tool_use_result={"stdout": DESIGN_INTERNAL})])
    assert audit_content_leaks(_transcript("test-writer", sess), None).trusted


def test_missing_subagent_file_does_not_crash(tmp_path):
    t = _transcript("test-writer", str(tmp_path / "nope.jsonl"))
    res = audit_content_leaks(t, _handoff(tmp_path))
    assert res.trusted  # unreadable transcript -> no finding, never an exception


def test_malformed_transcript_lines_are_skipped(tmp_path):
    p = tmp_path / "agent-x.jsonl"
    p.write_text("not json\n" + json.dumps(
        _user_tool_result(tool_use_result={"stdout": DESIGN_INTERNAL})) + "\n",
        encoding="utf-8")
    res = audit_content_leaks(_transcript("test-writer", str(p)), _handoff(tmp_path))
    assert not res.trusted  # the good line still catches the leak
