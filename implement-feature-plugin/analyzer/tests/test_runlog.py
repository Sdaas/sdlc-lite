"""Tests for the load-bearing run-log reader."""
from __future__ import annotations

import os

from analyzer.runlog import parse_runlog
from policy import bash_write_targets, confined_write_denied

from .conftest import call, gate, write_runlog


def test_heredoc_body_blockquotes_not_parsed_as_redirections():
    # The (ii) run exposed this: a reviewer writing its sanctioned handoff outbox via
    # `cat > … <<EOF` whose markdown body has `>` blockquote lines yielded phantom
    # redirect targets (`Canonical`, `Reviewer`) from inside the body.
    cmd = ("cat > /x/handoff/06-test-review-findings.md <<'EOF'\n"
           "# Findings\n> Canonical handoff file: `06`\n> Reviewer did not write.\nEOF")
    targets = bash_write_targets(cmd)
    assert targets == ["/x/handoff/06-test-review-findings.md"]
    # The outbox is inside the run's handoff dir -> the anchored confinement clears it.
    assert not any(confined_write_denied(t, "/x/handoff") for t in targets)


def test_real_redirection_before_heredoc_still_detected():
    assert bash_write_targets("cat > src/ref.py <<'EOF'\nx=1\nEOF") == ["src/ref.py"]


def test_second_redirection_after_heredoc_still_detected():
    cmd = "cat > /x/handoff/06.md <<'EOF'\n> body\nEOF\ncat > src/ref.py <<'E2'\ny\nE2"
    targets = bash_write_targets(cmd)
    assert "src/ref.py" in targets
    assert "body" not in targets


def _check(analysis, name):
    return next(c for c in analysis.checks if c.name == name)


# --- #31 R4: guard_decision -> per-agent grant/deny counts -----------------

def test_guard_decision_counted_per_agent(tmp_path):
    log = write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:implementer", "Read", "src/foo.py", guard_decision="allow"),
        call("implement-feature:implementer", "Write", "src/foo.py", guard_decision="allow"),
        call("implement-feature:test-writer", "Read", "handoff/03-design-internal.md",
             guard_decision="deny"),
    ])
    a = parse_runlog(str(log))
    impl = next(x for x in a.agents.values() if "implementer" in x.agent_type)
    tw = next(x for x in a.agents.values() if "test-writer" in x.agent_type)
    assert (impl.grants, impl.denies, impl.decision_unknown) == (2, 0, 0)
    assert (tw.grants, tw.denies, tw.decision_unknown) == (0, 1, 0)


def test_legacy_line_without_decision_is_unknown_not_guessed(tmp_path):
    # Pre-R4 lines have no guard_decision field: counted as unknown, never as allow.
    log = write_runlog(tmp_path / "rl.jsonl", [call("", "Read", "SKILL.md")])
    a = parse_runlog(str(log))
    cond = a.agents[""]
    assert (cond.grants, cond.denies, cond.decision_unknown) == (0, 0, 1)


def test_parse_counts_and_per_agent_activity(tmp_path):
    log = write_runlog(tmp_path / "rl.jsonl", [
        call("", "Read", "SKILL.md"),                                  # conductor
        call("", "Bash", "ls"),
        call("implement-feature:implementer", "Read", "src/foo.py"),
        call("implement-feature:implementer", "Write", "src/foo.py"),
    ])
    a = parse_runlog(str(log))
    assert a.total_entries == 4
    assert a.malformed_lines == 0
    assert a.window_start is not None and a.window_end is not None

    conductor = a.agents[""]
    assert conductor.label == "conductor"
    assert conductor.total_calls == 2
    assert conductor.tool_counts == {"Read": 1, "Bash": 1}

    impl = a.agents["implement-feature:implementer"]
    assert impl.label == "implementer"
    assert impl.reads == ["src/foo.py"]
    assert impl.writes == ["src/foo.py"]


def test_clean_run_passes_all_isolation_checks(tmp_path):
    log = write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:test-writer", "Read", "handoff/design-interface.md"),
        call("implement-feature:test-reviewer", "Read", "handoff/tests.py"),
        call("implement-feature:implementer", "Write", "src/foo.py"),
        call("implement-feature:verifier", "Bash", "pytest"),
        call("implement-feature:code-reviewer", "Read", "src/foo.py"),
    ])
    a = parse_runlog(str(log))
    assert a.all_passed
    assert _check(a, "distinct subagents observed").passed
    assert "all expected gates present" in _check(a, "distinct subagents observed").detail


def test_test_writer_reading_design_internal_is_a_violation(tmp_path):
    log = write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:test-writer", "Read", "handoff/design-internal.md"),
    ])
    a = parse_runlog(str(log))
    c = _check(a, "test-writer stayed algorithm-blind")
    assert not c.passed
    assert c.evidence == ["handoff/design-internal.md"]
    assert not a.all_passed


def test_implementer_writing_test_file_is_a_violation(tmp_path):
    log = write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:implementer", "Write", "tests/test_foo.py"),
        call("implement-feature:implementer", "Edit", "src/foo.py"),  # allowed
    ])
    a = parse_runlog(str(log))
    c = _check(a, "implementer did not touch tests")
    assert not c.passed
    assert c.evidence == ["tests/test_foo.py"]


def test_implementer_sed_inplace_on_test_file_is_detected(tmp_path):
    # #30 R2/detective: the in-place write FORM (`sed -i … tests/…`) is a Bash test-file
    # write the plain redirect scan misses. The detective extracts it via the policy SSOT
    # (bash_write_targets -> sed -i operand) and flags test-integrity, same as the guard.
    log = write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:implementer", "Bash", "sed -i 's/x/y/' tests/test_foo.py"),
    ])
    a = parse_runlog(str(log))
    c = _check(a, "implementer did not touch tests")
    assert not c.passed
    assert any("tests/test_foo.py" in e for e in c.evidence)


def test_any_agent_reading_secrets_is_a_violation(tmp_path):
    log = write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:verifier", "Read", "/repo/.env"),
    ])
    a = parse_runlog(str(log))
    c = _check(a, "no secret/.env access by any agent")
    assert not c.passed
    assert any(".env" in e for e in c.evidence)


def test_benign_bash_environ_is_not_a_secret_violation(tmp_path):
    # #16: a Bash command mentioning os.environ must NOT flip the verdict to VIOLATION.
    log = write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:test-reviewer", "Bash",
             "python3 -c \"import os; print(os.environ.get('X'))\""),
    ])
    a = parse_runlog(str(log))
    assert _check(a, "no secret/.env access by any agent").passed
    assert a.all_passed


def test_real_secret_read_via_bash_is_a_violation(tmp_path):
    log = write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:test-reviewer", "Bash", "cat ~/.ssh/id_rsa"),
    ])
    a = parse_runlog(str(log))
    assert not _check(a, "no secret/.env access by any agent").passed


def test_reviewer_writing_product_tree_is_a_violation(tmp_path):
    # #12: reviewer writes/edits or Bash-redirects into src/tests -> detected.
    log = write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:test-reviewer", "Write", "/repo/src/ref.py"),
        call("implement-feature:test-reviewer", "Bash", "cat > tests/test_x.py <<EOF\nx\nEOF"),
    ])
    a = parse_runlog(str(log))
    c = _check(a, "read-only critics stayed out of the product tree")
    assert not c.passed
    assert len(c.evidence) == 2


def test_confinement_generalizes_to_verifier_and_code_reviewer(tmp_path):
    # #29: the verifier and code-reviewer are write-confined exactly like the test-reviewer;
    # the detective now adjudicates all three read-only critics through the policy SSOT.
    log = write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:verifier", "Write", "/repo/src/patch.py"),
        call("implement-feature:code-reviewer", "Edit", "/repo/src/other.py"),
    ])
    a = parse_runlog(str(log))
    c = _check(a, "read-only critics stayed out of the product tree")
    assert not c.passed
    assert len(c.evidence) == 2
    assert any("verifier" in e for e in c.evidence)
    assert any("code-reviewer" in e for e in c.evidence)


def test_reviewer_outbox_and_probe_are_clean(tmp_path):
    # The run-log lives at <handoff>/rl.jsonl, so the derived handoff dir is tmp_path; the
    # sanctioned outbox is a file directly inside it. Anchored confinement clears both the
    # real outbox and a /tmp scratch probe.
    log = write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:test-reviewer", "Write",
             str(tmp_path / "06-test-review-findings.md")),
        call("implement-feature:test-reviewer", "Bash", "cat > /tmp/scratchpad/p.py <<EOF\nx\nEOF"),
        call("implement-feature:test-reviewer", "Bash", "python -m pytest -q"),
    ])
    a = parse_runlog(str(log))
    assert _check(a, "read-only critics stayed out of the product tree").passed


def test_reviewer_outbox_outside_handoff_dir_is_a_violation(tmp_path):
    # The verdict shift the dedup buys (#30 R1): the OLD loose rule cleared any path merely
    # containing "/handoff/". The anchored rule denies an outbox-looking path that is NOT
    # inside THIS run's handoff dir — a stale/other-run outbox no longer escapes.
    log = write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:test-reviewer", "Write",
             "/some/other/run/handoff/06-test-review-findings.md"),
    ])
    a = parse_runlog(str(log))
    assert not _check(a, "read-only critics stayed out of the product tree").passed


def test_relative_runlog_path_still_recognizes_own_outbox(tmp_path, monkeypatch):
    # #31b-iii regression: a live run's conductor passed a RELATIVE --workdir to
    # analyze_run.py (the CLI does not itself require --workdir to be absolute). Without
    # abspath() in _handoff_dir(), that produced a relative handoff_dir that could never
    # string-match the guard's ABSOLUTE logged write targets — misclassifying every
    # legitimate handoff-outbox write (Write/Edit targets are always absolute) as a
    # product-tree violation. 5 of 8 "violations" in that run were this false positive.
    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / "run"
    (run_dir / "handoff").mkdir(parents=True)
    log_abs = run_dir / "handoff" / "run-log.jsonl"
    write_runlog(log_abs, [
        call("implement-feature:test-reviewer", "Write",
             str(run_dir / "handoff" / "06-test-review-findings.md")),
    ])
    relative_path = os.path.relpath(log_abs, tmp_path)
    a = parse_runlog(relative_path)
    c = _check(a, "read-only critics stayed out of the product tree")
    assert c.passed, f"legitimate outbox write misclassified via relative path: {c.evidence}"


def test_reviewer_fd_dup_redirect_not_a_violation(tmp_path):
    # #12 regression: `2>&1` is fd duplication, not a write to a file named `&1`.
    log = write_runlog(tmp_path / "rl.jsonl", [
        call("implement-feature:test-reviewer", "Bash",
             "python -m pytest tests/ --collect-only -q 2>&1 | tail -20"),
    ])
    a = parse_runlog(str(log))
    c = _check(a, "read-only critics stayed out of the product tree")
    assert c.passed, f"fd-dup flagged as product write: {c.evidence}"


def test_malformed_lines_are_skipped_and_counted(tmp_path):
    p = tmp_path / "rl.jsonl"
    p.write_text(
        '{"agent_type":"","tool":"Read","target":"a","ts":"2026-09-09T07:40:01+00:00"}\n'
        "not json at all\n"
        "\n"  # blank line ignored, not counted as malformed
        '["a","list","not","a","dict"]\n',
        encoding="utf-8",
    )
    a = parse_runlog(str(p))
    assert a.total_entries == 1
    assert a.malformed_lines == 2


# --- M-06: the heterogeneous run-log (guard audit + conductor orchestration) ---
def test_orchestration_records_not_counted_as_tool_calls(tmp_path):
    # Before #22 leg B a conductor gate record was mis-parsed as a conductor "tool call" with
    # an empty tool name (inflating counts, printing a garbage ×N cell). It must now be counted
    # apart and excluded from the tool aggregation entirely.
    a = parse_runlog(str(write_runlog(tmp_path / "rl.jsonl", [
        gate("WRITE-TESTS", "test-writer"),
        call("implement-feature:test-writer", "Read", "handoff/x.md", guard_decision="allow"),
        gate("IMPLEMENT", "implementer", result="GREEN"),
    ])))
    assert a.total_entries == 1            # only the one real tool call
    assert a.orchestration_entries == 2    # both gate records, counted apart
    # No phantom empty-tool bucket, and no conductor AgentActivity from the gate records.
    tw = next(v for v in a.agents.values() if "test-writer" in v.agent_type)
    assert tw.tool_counts == {"Read": 1}
    assert "" not in a.agents             # gate `agent` field never made a conductor bucket


def test_orchestration_timestamps_still_bound_the_window(tmp_path):
    # A run that logged ONLY gate records (e.g. an aborted run before any tool call) still has
    # a usable window from their timestamps — needed to correlate the transcript.
    a = parse_runlog(str(write_runlog(tmp_path / "rl.jsonl", [
        gate("INTERVIEW", "conductor", mode="[C]"),
        gate("DESIGN", "conductor", mode="[C]"),
    ])))
    assert a.total_entries == 0 and a.orchestration_entries == 2
    assert a.window_start is not None and a.window_end is not None


def test_legacy_gate_record_with_guessed_model_still_not_a_tool_call(tmp_path):
    # A pre-m-09 gate record that still carries a guessed model/effort is STILL orchestration
    # (discriminated on `gate` + no `tool`), never a tool call — the fix is robust to old logs.
    a = parse_runlog(str(write_runlog(tmp_path / "rl.jsonl", [
        gate("TEST-REVIEW", "test-reviewer", model="claude-opus-4-8", effort="low"),
    ])))
    assert a.total_entries == 0 and a.orchestration_entries == 1
