"""Tests for the repo-local `/review-repo` measurement (#86) and its 3 areas (#92).

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
import subprocess
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


def _good(n_area=3, n_cons=1):
    return [(AREA, [_turn(), _turn()])] * n_area + [(CONSOLIDATOR, [_turn()])] * n_cons


def _agents_root(tmp_path: Path, effort=EFFORT, skip=()) -> Path:
    """A stand-in `.claude/` with both agent files; `effort=None` drops the effort line,
    `skip` leaves a file out."""
    root = tmp_path / "dotclaude"
    (root / "agents").mkdir(parents=True, exist_ok=True)
    for name in (AREA, CONSOLIDATOR):
        if name in skip:
            continue
        effort_line = f"effort: {effort}\n" if effort is not None else ""
        (root / "agents" / f"{name}.md").write_text(
            f"---\nname: {name}\nmodel: {MODEL}\n{effort_line}---\nbody\n")
    return root


def _run(tmp_path, projects, phase="final", agents_root=None, session=SID, report_text=None,
         extra=()):
    report = tmp_path / "review-20261004.md"
    if report_text is not None:
        report.write_text(report_text)
    rc = _measure().main([
        "--session", session, "--phase", phase, "--report", str(report),
        "--projects-dir", str(projects),
        "--agents-root", str(agents_root or _agents_root(tmp_path)), *extra,
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
    assert len(rows) == 4
    assert all(MODEL in r and EFFORT in r for r in rows)


# 3
def test_wrong_model_is_invalid(tmp_path):
    agents = _good()
    agents[1] = (AREA, [_turn(), _turn(model="claude-opus-5")])
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
    agents[1] = (AREA, [_turn(), _turn(effort=None)])
    rc, text = _run(tmp_path, _session(tmp_path, agents), report_text="# Review\n")
    assert rc == 1 and INVALID_HEAD in _head(text)


# 6 — counts are exact; other agent types are ignored
def test_missing_area_agent_is_invalid(tmp_path):
    rc, text = _run(tmp_path, _session(tmp_path, _good(n_area=2)), report_text="# Review\n")
    assert rc == 1 and INVALID_HEAD in _head(text)


def test_extra_area_agent_is_invalid(tmp_path):
    rc, text = _run(tmp_path, _session(tmp_path, _good(n_area=4)), report_text="# Review\n")
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
    agents[2] = (AREA, [_turn(effort="medium")])
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
    agents = [(AREA, [_turn(effort="medium")])] * 3 + [(CONSOLIDATOR, [_turn(effort="medium")])]
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


# --- #92: three areas, owned by measure.py, and the changed-since mode ---

def test_every_tracked_file_maps_to_exactly_one_area():
    """AC 1 tripwire on the real repo: no tracked file is unassigned, and every area has files."""
    m = _measure()
    files = subprocess.run(["git", "-C", str(REPO), "ls-files"], capture_output=True, text=True,
                           check=True).stdout.split()
    assert len(m.AREAS) == 3
    unassigned = [f for f in files if m.area_of(f) is None]
    assert unassigned == []
    used = {m.area_of(f) for f in files}
    assert used == {a[0] for a in m.AREAS}


def test_spot_mappings():
    m = _measure()
    assert m.area_of("sdlc-lite-plugin/policy.py") == "A"
    assert m.area_of("sdlc-lite-plugin/skills/implement-feature/SKILL.md") == "A"
    for f in ("sdlc-lite-plugin/hooks/hooks.json", "sdlc-lite-plugin/analyzer/receipt.py",
              "sdlc-lite-plugin/toolchain/setup_check.py", "sdlc-lite-plugin/tests/test_x.py"):
        assert m.area_of(f) == "A", f
    for f in (".claude-plugin/marketplace.json", "release-verify.sh", "test-fixtures/x/a.py"):
        assert m.area_of(f) == "B", f
    assert m.area_of("README.md") == "B"
    assert m.area_of("sdlc-lite-plugin/evals/smoke/prompt.md") == "B"
    assert m.area_of("dev-docs/adr/0001-x.md") == "C"
    assert m.area_of("review-20261004.md") == "C"
    assert m.area_of(".claude/skills/review-repo/SKILL.md") == "C"
    assert m.area_of("foo.txt") is None


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    """A tiny git repo with files in every area, tagged `base`, then a change to ONE of area A's
    two files."""
    repo = tmp_path / "repo"
    for f in ("sdlc-lite-plugin/policy.py", "sdlc-lite-plugin/agentdefs.py", "README.md",
              "CLAUDE.md"):
        (repo / f).parent.mkdir(parents=True, exist_ok=True)
        (repo / f).write_text("x\n")
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "base")
    _git(repo, "tag", "base")
    (repo / "sdlc-lite-plugin/policy.py").write_text("y\n")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "change A")
    return repo


def _plan_sections(out: str) -> dict[str, tuple[str, list[str]]]:
    """Plan output -> {area key: (its `Area X ...` header line, the indented file lines under it)}."""
    sections: dict[str, tuple[str, list[str]]] = {}
    key = None
    for line in out.splitlines():
        if line.startswith("Area "):
            key = line.split()[1]
            sections[key] = (line, [])
        elif line.startswith("  ") and key is not None:
            sections[key][1].append(line.strip())
        elif line.strip():
            key = None
    return sections


def test_plan_full_run_lists_three_areas(tmp_path, capsys):
    repo = _repo(tmp_path)
    rc, text = _run(tmp_path, tmp_path / "none", phase="plan", session="-",
                    extra=("--repo", str(repo)))
    out = capsys.readouterr().out
    assert rc == 0 and text is None  # plan writes nothing
    sec = _plan_sections(out)
    assert sorted(sec) == ["A", "B", "C"]
    assert all("not reviewed" not in sec[k][0] for k in sec)
    assert sorted(sec["A"][1]) == ["sdlc-lite-plugin/agentdefs.py", "sdlc-lite-plugin/policy.py"]
    assert sec["B"][1] == ["README.md"] and sec["C"][1] == ["CLAUDE.md"]


def test_plan_since_lists_only_changed_areas(tmp_path, capsys):
    repo = _repo(tmp_path)
    rc, text = _run(tmp_path, tmp_path / "none", phase="plan", session="-",
                    extra=("--repo", str(repo), "--since", "base"))
    out = capsys.readouterr().out
    assert rc == 0 and text is None  # plan writes nothing
    sec = _plan_sections(out)
    assert "not reviewed" not in sec["A"][0]
    # the changed area hands out its WHOLE file list, not only the changed file
    assert sorted(sec["A"][1]) == ["sdlc-lite-plugin/agentdefs.py", "sdlc-lite-plugin/policy.py"]
    for k in "BC":
        assert "not reviewed" in sec[k][0] and sec[k][1] == []
    assert "README.md" not in out  # an unchanged area's files are not handed out


def test_since_final_expects_only_changed_areas(tmp_path):
    repo = _repo(tmp_path)
    extra = ("--repo", str(repo), "--since", "base")
    rc, text = _run(tmp_path, _session(tmp_path, _good(n_area=1)), report_text="# Review\n",
                    extra=extra)
    assert rc == 0 and "INVALID" not in text


def test_since_final_with_all_three_areas_is_invalid(tmp_path):
    repo = _repo(tmp_path)
    extra = ("--repo", str(repo), "--since", "base")
    rc, text = _run(tmp_path, _session(tmp_path, _good()), report_text="# Review\n", extra=extra)
    assert rc == 1 and INVALID_HEAD in _head(text)


def test_since_nothing_changed_is_invalid(tmp_path, capsys):
    repo = _repo(tmp_path)
    extra = ("--repo", str(repo), "--since", "HEAD")
    rc, _ = _run(tmp_path, tmp_path / "none", phase="plan", session="-", extra=extra)
    assert rc == 1
    assert "nothing to review" in capsys.readouterr().out
    rc, text = _run(tmp_path, _session(tmp_path, _good(n_area=0, n_cons=0)), phase="areas",
                    extra=extra)
    assert rc == 1 and INVALID_HEAD in _head(text)


def test_since_bad_ref_is_invalid_without_raising(tmp_path):
    repo = _repo(tmp_path)
    extra = ("--repo", str(repo), "--since", "no-such-ref")
    rc, text = _run(tmp_path, _session(tmp_path, _good()), report_text="# Review\n", extra=extra)
    assert rc == 1 and INVALID_HEAD in _head(text) and "no-such-ref" in text


def test_plan_bad_ref_fails_without_raising(tmp_path, capsys):
    repo = _repo(tmp_path)
    rc, text = _run(tmp_path, tmp_path / "none", phase="plan", session="-",
                    extra=("--repo", str(repo), "--since", "no-such-ref"))
    assert rc == 1 and text is None
    assert "no-such-ref" in capsys.readouterr().out


def test_prose_follows_three_areas_and_since():
    """Tripwire: the skill and both agent files no longer speak of nine areas; the skill takes
    an optional since-ref and names the Not reviewed list."""
    skill = (MEASURE.parent / "SKILL.md").read_text()
    agents = [(REPO / ".claude" / "agents" / f"{n}.md").read_text() for n in (AREA, CONSOLIDATOR)]
    for text in [skill, *agents]:
        assert not re.search(r"\bnine\b|\b9 (area|parallel)|area 9\b", text, re.I)
    assert "--since" in skill and "--phase plan" in skill
    assert "since-ref" in skill.split("---")[1]  # argument-hint in the frontmatter
    assert "Not reviewed" in agents[1]


def _commit_all(repo: Path, msg: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", msg)


def test_since_deleted_file_marks_its_area(tmp_path, capsys):
    repo = _repo(tmp_path)
    _git(repo, "tag", "after-a")
    (repo / "README.md").unlink()
    _commit_all(repo, "delete B's only file")
    _run(tmp_path, tmp_path / "none", phase="plan", session="-",
         extra=("--repo", str(repo), "--since", "after-a"))
    sec = _plan_sections(capsys.readouterr().out)
    assert "not reviewed" not in sec["B"][0]


def test_since_rename_across_areas_marks_both_areas(tmp_path, capsys):
    repo = _repo(tmp_path)
    _git(repo, "tag", "after-a")
    (repo / "dev-docs").mkdir()
    _git(repo, "mv", "README.md", "dev-docs/moved.md")  # B -> C
    _commit_all(repo, "rename across areas")
    _run(tmp_path, tmp_path / "none", phase="plan", session="-",
         extra=("--repo", str(repo), "--since", "after-a"))
    sec = _plan_sections(capsys.readouterr().out)
    assert "not reviewed" not in sec["B"][0]  # the old path's area counts too
    assert "not reviewed" not in sec["C"][0]


def test_since_ref_starting_with_dash_is_not_a_git_option(tmp_path, capsys):
    repo = _repo(tmp_path)
    out_file = tmp_path / "leak.txt"
    rc, _ = _run(tmp_path, tmp_path / "none", phase="plan", session="-",
                 extra=("--repo", str(repo), f"--since=--output={out_file}"))
    assert rc == 1 and not out_file.exists()
