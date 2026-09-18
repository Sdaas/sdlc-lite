"""Tests for the PreToolUse guard hook (hooks/scripts/guard.py).

The hook is a stdin/stdout/exit-code contract, so we drive the real script as a
subprocess: feed it the hook JSON on stdin, set its env, and assert on the exit
code (0 allow / 2 deny), the deny JSON on stdout, and the audit line it appends.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parent.parent / "scripts" / "guard.py"


def run_guard(payload: dict, env_extra: dict | None = None, project_dir: str | None = None):
    """Invoke guard.py with `payload` as stdin JSON. Returns (returncode, stdout)."""
    env = {"PATH": "/usr/bin:/bin"}
    if project_dir is not None:
        env["CLAUDE_PROJECT_DIR"] = project_dir
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(payload),
        capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stdout


def call(tool: str, target: str, *, agent_type: str = "", **kw) -> dict:
    key = "command" if tool == "Bash" else "file_path"
    return {"tool_name": tool, "tool_input": {key: target}, "agent_type": agent_type, **kw}


# --- audit + run-log resolution (#10) --------------------------------------

def test_audit_written_to_if_runlog(tmp_path):
    log = tmp_path / "explicit.jsonl"
    rc, _ = run_guard(call("Read", "somefile.py"), env_extra={"IF_RUNLOG": str(log)})
    assert rc == 0
    line = json.loads(log.read_text().strip())
    assert line["tool"] == "Read" and line["target"] == "somefile.py"


def test_audit_records_guard_decision_allow(tmp_path):
    log = tmp_path / "l.jsonl"
    rc, _ = run_guard(call("Read", "somefile.py"), env_extra={"IF_RUNLOG": str(log)})
    assert rc == 0  # #31 R4: allowed call is stamped allow
    assert json.loads(log.read_text().strip())["guard_decision"] == "allow"


def test_audit_records_guard_decision_deny_even_though_call_is_blocked(tmp_path):
    log = tmp_path / "l.jsonl"
    rc, _ = run_guard(call("Read", "/repo/.env"), env_extra={"IF_RUNLOG": str(log)})
    assert rc == 2  # denied — and the audit line (only record of a denial) says so
    assert json.loads(log.read_text().strip())["guard_decision"] == "deny"


def test_runlog_resolved_via_active_run_pointer(tmp_path):
    # Layout: <proj>/.implement-feature/.active-run -> <workdir>; log at <workdir>/handoff/.
    proj = tmp_path
    workdir = proj / ".implement-feature" / "01-foo-202609101200"
    (workdir / "handoff").mkdir(parents=True)
    (proj / ".implement-feature" / ".active-run").write_text(str(workdir))

    rc, _ = run_guard(call("Read", "x.py"), project_dir=str(proj))
    assert rc == 0
    derived = workdir / "handoff" / "run-log.jsonl"
    assert derived.is_file()
    assert json.loads(derived.read_text().strip())["target"] == "x.py"


def test_runlog_falls_back_to_project_dir_when_no_pointer(tmp_path):
    rc, _ = run_guard(call("Read", "x.py"), project_dir=str(tmp_path))
    assert rc == 0
    assert (tmp_path / "if-runlog.jsonl").is_file()


# --- draft-confinement (#11) -----------------------------------------------

def test_subagent_denied_reading_handoff_draft(tmp_path):
    rc, out = run_guard(
        call("Read", "/repo/.implement-feature/r/handoff/draft/02-design-interface.md",
             agent_type="implement-feature:test-writer"),
        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")},
    )
    assert rc == 2
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_conductor_may_read_handoff_draft(tmp_path):
    # Empty agent_type == the conductor; it authors and reviews the drafts.
    rc, _ = run_guard(
        call("Read", "/repo/.implement-feature/r/handoff/draft/02-design-interface.md",
             agent_type=""),
        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")},
    )
    assert rc == 0


def test_subagent_may_read_promoted_handoff_file(tmp_path):
    rc, _ = run_guard(
        call("Read", "/repo/.implement-feature/r/handoff/02-design-interface.md",
             agent_type="implement-feature:test-writer"),
        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")},
    )
    assert rc == 0


# --- existing guardrails still hold, with numbered names (#17) -------------

def test_secret_read_denied_for_any_agent(tmp_path):
    rc, out = run_guard(call("Read", "/repo/.env"),
                        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 2
    assert "secret" in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"].lower()


def test_test_writer_denied_numbered_design_internal(tmp_path):
    rc, out = run_guard(
        call("Read", "/repo/.implement-feature/r/handoff/03-design-internal.md",
             agent_type="implement-feature:test-writer"),
        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")},
    )
    assert rc == 2  # numeric prefix still trips the substring match
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


TW = "implement-feature:test-writer"


# --- #30 R6: wildcard-ban for the algorithm-blind test-writer ---------------

@pytest.mark.parametrize("cmd", [
    "cat /repo/.implement-feature/r/handoff/*.md",
    "head /repo/.implement-feature/r/handoff/0[23]-*",
    "cat handoff/*",
])
def test_test_writer_denied_wildcard_read_over_handoff(cmd, tmp_path):
    # The glob could resolve to 03-design-internal.md; the literal-substring rule can't
    # see it, so R6 bans the wildcard outright.
    rc, out = run_guard(call("Bash", cmd, agent_type=TW),
                        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 2, f"wildcard handoff read NOT denied: {cmd!r}"
    assert "algorithm-blind" in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]


def test_test_writer_may_read_handoff_file_by_exact_name(tmp_path):
    rc, _ = run_guard(
        call("Bash", "cat /repo/.implement-feature/r/handoff/01-requirements.md", agent_type=TW),
        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 0


def test_test_writer_wildcard_outside_handoff_allowed(tmp_path):
    # A glob that does NOT reference handoff is fine (the test-writer globs its own tests).
    rc, _ = run_guard(call("Bash", "ls tests/*.py", agent_type=TW),
                      env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 0


def test_non_blind_agent_wildcard_over_handoff_allowed(tmp_path):
    # The implementer MAY read design-internal, so its handoff glob is not banned.
    rc, _ = run_guard(call("Bash", "cat handoff/*.md",
                           agent_type="implement-feature:implementer"),
                      env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 0


def test_implementer_denied_writing_test_file(tmp_path):
    rc, out = run_guard(
        call("Write", "/repo/tests/test_foo.py", agent_type="implement-feature:implementer"),
        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")},
    )
    assert rc == 2
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


# --- #30 R2: Bash write FORMS now enforced (closing the historical Bash gaps) ----

def test_implementer_denied_bash_sed_inplace_test_write(tmp_path):
    # Was audited-but-allowed before #30 (sed -i is not a `>` redirect). Now denied.
    rc, out = run_guard(
        call("Bash", "sed -i 's/x/y/' tests/test_foo.py",
             agent_type="implement-feature:implementer"),
        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 2
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_implementer_denied_bash_heredoc_test_write(tmp_path):
    rc, out = run_guard(
        call("Bash", "cat > tests/test_foo.py <<'EOF'\ndef test_x(): assert True\nEOF",
             agent_type="implement-feature:implementer"),
        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 2


@pytest.mark.parametrize("agent", [
    "implement-feature:verifier", "implement-feature:code-reviewer",
])
def test_confined_critics_denied_bash_product_write(agent, tmp_path):
    # #29 (subsumed by #30): verifier + code-reviewer get the test-reviewer's
    # write-confinement — a Bash product-tree write is denied.
    rc, out = run_guard(
        call("Bash", "echo x > /repo/src/ref.py", agent_type=agent),
        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 2
    assert "product tree" in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]


def test_full_length_target_logged_no_truncation(tmp_path):
    # #30 R3: the run-log is the intent record and must log the WHOLE command (the old
    # target[:300] truncation was a data-loss bug the transcript auditor can't tolerate).
    log = tmp_path / "l.jsonl"
    long_cmd = "echo " + "a" * 500 + " > /tmp/scratchpad/x"
    rc, _ = run_guard(call("Bash", long_cmd), env_extra={"IF_RUNLOG": str(log)})
    assert rc == 0
    assert json.loads(log.read_text().strip())["target"] == long_cmd


# --- #16: secret detection must not false-positive on Bash command strings --

BENIGN_BASH = [
    "python3 -c \"import os; print(os.environ.get('FOO'))\"",  # the chunk-21 false positive
    "python3 -c 'import secrets; print(secrets.token_hex(8))'",
    "grep -r environ src/",
    "echo my_api_key=redacted",           # bare identifier, not a file
    "mutmut run",
]


@pytest.mark.parametrize("cmd", BENIGN_BASH)
def test_benign_bash_not_flagged_as_secret(cmd, tmp_path):
    rc, _ = run_guard(call("Bash", cmd, agent_type="implement-feature:test-reviewer"),
                      env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 0, f"benign command false-denied: {cmd!r}"


SECRET_BASH = [
    "cat .env",
    "cat /repo/.env.local",
    "cat ~/.ssh/id_rsa",
    "cat ./config/credentials.json",
    "openssl rsa -in server.pem",
]


@pytest.mark.parametrize("cmd", SECRET_BASH)
def test_real_secret_bash_still_denied(cmd, tmp_path):
    rc, out = run_guard(call("Bash", cmd, agent_type="implement-feature:test-reviewer"),
                        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 2, f"secret read NOT denied: {cmd!r}"
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_env_dir_component_read_denied(tmp_path):
    # A path whose component (not basename) is .env is still a secret read.
    rc, _ = run_guard(call("Read", "/repo/.env/config"),
                      env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 2


def test_lookalike_dir_not_flagged(tmp_path):
    # #1: over-broad substring flagged backend.envtools/; component match does not.
    rc, _ = run_guard(call("Read", "/repo/backend.envtools/app.py"),
                      env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 0


def test_edit_of_secret_file_denied(tmp_path):
    # #m-05: Edit reads the file to diff, but was outside the READISH secrets check.
    secret = tmp_path / ".env"
    secret.write_text("X=1")
    rc, out = run_guard(call("Edit", str(secret)),
                        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 2
    assert "secret" in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"].lower()


def test_grep_directory_containing_secret_denied(tmp_path):
    # #m-05: a Grep call scoped to a directory that contains .env surfaces its contents
    # even though the Grep target itself is not a secret path.
    (tmp_path / ".env").write_text("AWS_SECRET=shh")
    rc, out = run_guard(
        {"tool_name": "Grep", "tool_input": {"pattern": "AWS_SECRET", "path": str(tmp_path)},
         "agent_type": ""},
        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 2
    assert "secret" in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"].lower()


def test_bash_recursive_grep_over_secret_directory_denied(tmp_path):
    # #m-05: `grep -r ... <dir>` over a directory containing .env is a common,
    # innocent-looking way to exfiltrate secret contents without a direct open.
    (tmp_path / ".env").write_text("AWS_SECRET=shh")
    rc, out = run_guard(call("Bash", f"grep -r AWS_SECRET {tmp_path}"),
                        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 2
    assert "secret" in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"].lower()


def test_bash_recursive_grep_over_clean_directory_allowed(tmp_path):
    (tmp_path / "app.py").write_text("x = 1")
    rc, _ = run_guard(call("Bash", f"grep -r x {tmp_path}"),
                      env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 0


# --- #12: test-reviewer write-confinement ----------------------------------

REVIEWER = "implement-feature:test-reviewer"

# The run's real handoff dir is derived from IF_RUNLOG's directory (guard.py's
# `_handoff_dir()`), so confinement tests that write into "the outbox" must point
# IF_RUNLOG at a run-log.jsonl that actually sits alongside the write target.
HANDOFF_RUNLOG = "/repo/.implement-feature/r/handoff/run-log.jsonl"


def test_reviewer_may_write_its_handoff_outbox(tmp_path):
    rc, _ = run_guard(
        call("Write", "/repo/.implement-feature/r/handoff/06-test-review-findings.md",
             agent_type=REVIEWER),
        env_extra={"IF_RUNLOG": HANDOFF_RUNLOG})
    assert rc == 0


def test_reviewer_denied_spoofed_scratchpad_path(tmp_path):
    # #m-06: "scratchpad" appearing anywhere in a product-tree path must not escape
    # confinement — only a real temp-root prefix is sanctioned.
    rc, out = run_guard(
        call("Write", "/repo/scratchpad_util.py", agent_type=REVIEWER),
        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 2
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_reviewer_denied_spoofed_handoff_path(tmp_path):
    # #m-06: a product-tree path that merely contains "/handoff/" (but isn't the run's
    # real handoff dir) must not escape confinement.
    rc, out = run_guard(
        call("Write", "/repo/src/handoff/impl.py", agent_type=REVIEWER),
        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 2
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_reviewer_may_write_scratch_probe(tmp_path):
    rc, _ = run_guard(
        call("Write", "/tmp/scratchpad/probe.py", agent_type=REVIEWER),
        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 0


def test_reviewer_denied_writing_product_source(tmp_path):
    rc, out = run_guard(
        call("Write", "/repo/src/ref.py", agent_type=REVIEWER),
        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 2
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_reviewer_denied_bash_heredoc_into_product(tmp_path):
    rc, out = run_guard(
        call("Bash", "cat > src/ref.py <<'EOF'\nx=1\nEOF", agent_type=REVIEWER),
        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 2
    assert "product tree" in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]


def test_reviewer_bash_probe_to_scratch_allowed(tmp_path):
    rc, _ = run_guard(
        call("Bash", "cat > /tmp/scratchpad/probe.py <<'EOF'\nx=1\nEOF", agent_type=REVIEWER),
        env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 0


def test_reviewer_heredoc_markdown_body_allowed(tmp_path):
    # The (ii) run exposed this: writing the sanctioned handoff outbox via `cat > … <<EOF`
    # whose markdown body has `>` blockquote lines was false-denied — the body `>` parsed
    # as a shell redirection to a phantom file (`Canonical`, `Reviewer`).
    cmd = ("cat > /repo/.implement-feature/r/handoff/06-test-review-findings.md <<'EOF'\n"
           "# Findings\n> Canonical handoff file: `06`\n> Reviewer did not write tests.\nEOF")
    rc, _ = run_guard(call("Bash", cmd, agent_type=REVIEWER),
                      env_extra={"IF_RUNLOG": HANDOFF_RUNLOG})
    assert rc == 0


def test_reviewer_second_heredoc_into_product_still_denied(tmp_path):
    # Stripping heredoc bodies must not blind us to a real redirection after one.
    cmd = ("cat > /repo/.implement-feature/r/handoff/06.md <<'EOF'\n> body\nEOF\n"
           "cat > src/ref.py <<'E2'\ny=1\nE2")
    rc, out = run_guard(call("Bash", cmd, agent_type=REVIEWER),
                        env_extra={"IF_RUNLOG": HANDOFF_RUNLOG})
    assert rc == 2
    assert "product tree" in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]


def test_reviewer_may_run_pytest(tmp_path):
    # A read-ish Bash with no write redirection must not be denied.
    rc, _ = run_guard(call("Bash", "python -m pytest -q", agent_type=REVIEWER),
                      env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 0


@pytest.mark.parametrize("cmd", [
    "python -m pytest tests/ --collect-only -q 2>&1 | tail -20",   # the Phase-2 false positive
    "ruff check . 2>&1",
    "python -c 'x=1' 1>&2",
    "python -m pytest -q 2>/dev/null",                              # bit bucket, not product tree
    "cat pyproject.toml > /dev/null",
])
def test_reviewer_benign_redirects_not_flagged(cmd, tmp_path):
    # `2>&1`/`1>&2` are fd dups; `/dev/null` is the bit bucket — none is a product write (#12 regression).
    rc, _ = run_guard(call("Bash", cmd, agent_type=REVIEWER),
                      env_extra={"IF_RUNLOG": str(tmp_path / "l.jsonl")})
    assert rc == 0, f"benign redirect false-denied: {cmd!r}"


# --- #36: Task/Agent dispatch is AUDITED but never model-enforced ----------
# The #22 deny-if-unnamed hook was reverted (its premise — "a frontmatter model pin is silently
# droppable" — is false, and it broke the dated reviewer pins by forcing an alias-only inline
# model). Pinned gates now dispatch BARE and the honored frontmatter pin governs; the receipt
# verifies the actual model after the fact. So a bare dispatch is ALLOWED and still audited.

def dispatch(subagent_type: str | None, *, tool: str = "Task",
             model: str | None = None, agent_type: str = "") -> dict:
    ti: dict = {}
    if subagent_type is not None:
        ti["subagent_type"] = subagent_type
    if model is not None:
        ti["model"] = model
    return {"tool_name": tool, "tool_input": ti, "agent_type": agent_type}


def test_dispatch_pinned_agent_without_model_is_allowed_and_audited(tmp_path):
    # #36: the dated-pin reviewer is dispatched bare — allowed, and recorded in the run-log so the
    # dispatch is still observable (the receipt verifies the actual resolved model).
    log = tmp_path / "l.jsonl"
    rc, _ = run_guard(dispatch("implement-feature:code-reviewer"),
                      env_extra={"IF_RUNLOG": str(log)})
    assert rc == 0  # bare dispatch of a pinned gate is honored, not denied
    line = json.loads(log.read_text().strip())
    assert line["tool"] == "Task" and line["target"] == "implement-feature:code-reviewer"
    assert line["guard_decision"] == "allow"


def test_dispatch_with_explicit_model_is_allowed(tmp_path):
    log = tmp_path / "l.jsonl"
    rc, _ = run_guard(dispatch("implement-feature:code-reviewer", model="opus"),
                      env_extra={"IF_RUNLOG": str(log)})
    assert rc == 0
    assert json.loads(log.read_text().strip())["guard_decision"] == "allow"


def test_dispatch_unpinned_agent_is_allowed():
    rc, _ = run_guard(dispatch("some-random-agent"))
    assert rc == 0


def test_dispatch_missing_subagent_type_is_allowed():
    # A partial dispatch payload carries no file target — nothing to adjudicate, allow.
    rc, _ = run_guard(dispatch(None))
    assert rc == 0


def test_dispatch_agent_tool_name_also_allowed():
    # The matcher covers both Task and Agent dispatch verbs; neither is model-enforced now.
    rc, _ = run_guard(dispatch("implement-feature:test-reviewer", tool="Agent"))
    assert rc == 0


def test_dispatch_alias_pinned_agent_without_model_is_allowed():
    # A producer pinned to the `sonnet` alias also dispatches bare — the frontmatter pin governs.
    rc, _ = run_guard(dispatch("implement-feature:implementer"))
    assert rc == 0
