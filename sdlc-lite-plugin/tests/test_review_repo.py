"""Tests for the repo-local `/review-repo` measurement (#86).

`.claude/skills/review-repo/measure.py` proves the full-repo review ran every agent on
`claude-opus-5-5` at effort `high`. It checks the transcript against FIXED required values
(not just the pins), so a drifted pin cannot pass. These tests build fake session
transcripts in `tmp_path` (layout: analyzer/TRANSCRIPT-FORMAT.md) and also read the REAL
`.claude/agents/*.md` as a tripwire.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import agentdefs

REPO = Path(__file__).resolve().parents[2]
MEASURE = REPO / ".claude" / "skills" / "review-repo" / "measure.py"

MODEL, EFFORT = "claude-opus-5-5", "high"
AREA, CONSOLIDATOR = "repo-area-reviewer", "repo-review-consolidator"
INVALID_HEAD = "INVALID — not Opus 5.5 / high"
SID = "11111111-2222-3333-4444-555555555555"


def _measure():
    spec = importlib.util.spec_from_file_location("review_repo_measure", MEASURE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _turn(model=MODEL, effort=EFFORT) -> str:
    rec = {"type": "assistant",
           "message": {"model": model, "usage": {"input_tokens": 1, "output_tokens": 1}}}
    if effort is not None:
        rec["effort"] = effort
    return json.dumps(rec)


def _session(tmp_path: Path, agents: list[tuple[str, list[str]]]) -> Path:
    """projects/<slug>/<SID>.jsonl + <SID>/subagents/agent-N.jsonl (+ .meta.json)."""
    projects = tmp_path / "projects"
    proj = projects / "-workspaces-sdlc-lite"
    sdir = proj / SID / "subagents"
    sdir.mkdir(parents=True)
    (proj / f"{SID}.jsonl").write_text(_turn("claude-opus-5-5", "medium") + "\n")
    for i, (agent_type, turns) in enumerate(agents):
        (sdir / f"agent-{i}.jsonl").write_text("\n".join(turns) + "\n")
        (sdir / f"agent-{i}.meta.json").write_text(json.dumps({"agentType": agent_type}))
    return projects


def _good(n_area=9, n_cons=1):
    return [(AREA, [_turn(), _turn()])] * n_area + [(CONSOLIDATOR, [_turn()])] * n_cons


def _agents_root(tmp_path: Path, effort=EFFORT, skip=()) -> Path:
    """A stand-in `.claude/` with both agent files; `effort=None` drops the effort line,
    `skip` leaves a file out."""
    root = tmp_path / "dotclaude"
    (root / "agents").mkdir(parents=True)
    for name in (AREA, CONSOLIDATOR):
        if name in skip:
            continue
        effort_line = f"effort: {effort}\n" if effort is not None else ""
        (root / "agents" / f"{name}.md").write_text(
            f"---\nname: {name}\nmodel: {MODEL}\n{effort_line}---\nbody\n")
    return root


def _run(tmp_path, projects, phase="final", agents_root=None, session=SID, report_text=None):
    report = tmp_path / "review-20261004.md"
    if report_text is not None:
        report.write_text(report_text)
    rc = _measure().main([
        "--session", session, "--phase", phase, "--report", str(report),
        "--projects-dir", str(projects),
        "--agents-root", str(agents_root or _agents_root(tmp_path)),
    ])
    return rc, report.read_text() if report.exists() else None


def _head(text: str) -> str:
    return next(line for line in text.splitlines() if line.strip())


# 1 — tripwire on the real agent files
def test_real_agent_files_pin_opus_5_5_high():
    pins = agentdefs.load_pins(str(REPO / ".claude"))
    for name in (AREA, CONSOLIDATOR):
        assert name in pins, f"missing .claude/agents/{name}.md"
        assert (pins[name].model, pins[name].effort) == (MODEL, EFFORT)


# 2
def test_all_agents_correct_is_valid(tmp_path):
    rc, text = _run(tmp_path, _session(tmp_path, _good()), report_text="# Review\n\nbody\n")
    assert rc == 0
    assert "VALID" in _head(text) and "INVALID" not in text
    assert "# Review\n\nbody" in text  # the consolidator's report is kept below the block
    # The block reports the actual model and effort of every agent: one row each.
    rows = [line for line in text.splitlines() if line.startswith(f"| {AREA} |")
            or line.startswith(f"| {CONSOLIDATOR} |")]
    assert len(rows) == 10
    assert all(MODEL in r and EFFORT in r for r in rows)


# 3
def test_wrong_model_is_invalid(tmp_path):
    agents = _good()
    agents[3] = (AREA, [_turn(), _turn(model="claude-opus-5")])
    rc, text = _run(tmp_path, _session(tmp_path, agents), report_text="# Review\n")
    assert rc == 1 and INVALID_HEAD in _head(text)
    # The offending agent's row names the model it actually ran and is marked FAIL.
    assert any(r.startswith(f"| {AREA} |") and re.search(r"claude-opus-5(?!-)", r)
               and "FAIL" in r for r in text.splitlines())


# 4
def test_wrong_effort_is_invalid(tmp_path):
    agents = _good()
    agents[-1] = (CONSOLIDATOR, [_turn(effort="medium")])
    rc, text = _run(tmp_path, _session(tmp_path, agents), report_text="# Review\n")
    assert rc == 1 and INVALID_HEAD in _head(text)
    assert any(r.startswith(f"| {CONSOLIDATOR} |") and "medium" in r and "FAIL" in r
               for r in text.splitlines())


# 5
def test_missing_effort_is_invalid(tmp_path):
    agents = _good()
    agents[0] = (AREA, [_turn(effort=None)])
    rc, text = _run(tmp_path, _session(tmp_path, agents), report_text="# Review\n")
    assert rc == 1 and INVALID_HEAD in _head(text)


def test_mixed_effort_inside_one_agent_is_invalid(tmp_path):
    agents = _good()
    agents[2] = (AREA, [_turn(), _turn(effort="medium")])
    rc, text = _run(tmp_path, _session(tmp_path, agents), report_text="# Review\n")
    assert rc == 1 and INVALID_HEAD in _head(text)


def test_one_turn_without_effort_inside_one_agent_is_invalid(tmp_path):
    agents = _good()
    agents[4] = (AREA, [_turn(), _turn(effort=None)])
    rc, text = _run(tmp_path, _session(tmp_path, agents), report_text="# Review\n")
    assert rc == 1 and INVALID_HEAD in _head(text)


# 6 — counts are exact; other agent types are ignored
def test_missing_area_agent_is_invalid(tmp_path):
    rc, text = _run(tmp_path, _session(tmp_path, _good(n_area=8)), report_text="# Review\n")
    assert rc == 1 and INVALID_HEAD in _head(text)


def test_extra_area_agent_is_invalid(tmp_path):
    rc, text = _run(tmp_path, _session(tmp_path, _good(n_area=10)), report_text="# Review\n")
    assert rc == 1 and INVALID_HEAD in _head(text)


def test_final_phase_without_consolidator_is_invalid(tmp_path):
    rc, text = _run(tmp_path, _session(tmp_path, _good(n_cons=0)), report_text="# Review\n")
    assert rc == 1 and INVALID_HEAD in _head(text)


def test_other_agent_types_are_ignored(tmp_path):
    agents = _good() + [("general-purpose", [_turn(model="claude-sonnet-5-5", effort="low")])]
    rc, text = _run(tmp_path, _session(tmp_path, agents), report_text="# Review\n")
    assert rc == 0 and "INVALID" not in text


# 7
def test_areas_phase_valid_without_consolidator(tmp_path):
    rc, text = _run(tmp_path, _session(tmp_path, _good(n_cons=0)), phase="areas")
    assert rc == 0
    assert text is None  # no stub: the consolidator creates the report next


def test_areas_phase_invalid_writes_stub_report(tmp_path):
    agents = _good(n_cons=0)
    agents[5] = (AREA, [_turn(effort="medium")])
    rc, text = _run(tmp_path, _session(tmp_path, agents), phase="areas")
    assert rc == 1
    assert text is not None and INVALID_HEAD in _head(text)


# Pre-flight: `--phase pins` checks only the agent files, before any agent is spawned.
def test_pins_phase_correct_pins_is_valid_without_a_transcript(tmp_path, capsys):
    rc, text = _run(tmp_path, tmp_path / "no-projects", phase="pins", session="not-started")
    assert rc == 0
    assert text is None  # no report yet: nothing was reviewed
    out = capsys.readouterr().out
    assert "VALID" in _head(out) and "INVALID" not in out


def test_pins_phase_wrong_pin_is_invalid(tmp_path, capsys):
    rc, text = _run(tmp_path, tmp_path / "no-projects", phase="pins", session="not-started",
                    agents_root=_agents_root(tmp_path, effort="medium"))
    assert rc == 1
    assert text is None
    assert INVALID_HEAD in _head(capsys.readouterr().out)


def test_pins_phase_one_model_pin_drifted_is_invalid(tmp_path, capsys):
    root = _agents_root(tmp_path)
    cons = root / "agents" / f"{CONSOLIDATOR}.md"
    cons.write_text(cons.read_text().replace(f"model: {MODEL}", "model: opus"))
    rc, text = _run(tmp_path, tmp_path / "no-projects", phase="pins", session="not-started",
                    agents_root=root)
    assert rc == 1 and text is None
    assert INVALID_HEAD in _head(capsys.readouterr().out)


# 8
def test_drifted_pin_is_invalid_even_when_transcript_is_correct(tmp_path):
    rc, text = _run(tmp_path, _session(tmp_path, _good()),
                    agents_root=_agents_root(tmp_path, effort="medium"),
                    report_text="# Review\n")
    assert rc == 1 and INVALID_HEAD in _head(text)


def test_pin_and_transcript_both_medium_is_invalid(tmp_path):
    """The required values are fixed, not read from the pins: a pin dropped to `medium`
    with a run that obeyed it must still be INVALID (the planned wrong-pin run)."""
    agents = [(AREA, [_turn(effort="medium")])] * 9 + [(CONSOLIDATOR, [_turn(effort="medium")])]
    rc, text = _run(tmp_path, _session(tmp_path, agents),
                    agents_root=_agents_root(tmp_path, effort="medium"),
                    report_text="# Review\n")
    assert rc == 1 and INVALID_HEAD in _head(text)


def test_pin_without_effort_is_invalid(tmp_path):
    rc, text = _run(tmp_path, _session(tmp_path, _good()),
                    agents_root=_agents_root(tmp_path, effort=None), report_text="# Review\n")
    assert rc == 1 and INVALID_HEAD in _head(text)


def test_missing_agent_file_is_invalid(tmp_path):
    rc, text = _run(tmp_path, _session(tmp_path, _good()),
                    agents_root=_agents_root(tmp_path, skip=(CONSOLIDATOR,)),
                    report_text="# Review\n")
    assert rc == 1 and INVALID_HEAD in _head(text)


# 9
def test_unknown_session_is_invalid(tmp_path):
    rc, text = _run(tmp_path, _session(tmp_path, _good()), session="no-such-session",
                    report_text="# Review\n")
    assert rc == 1 and INVALID_HEAD in _head(text)
