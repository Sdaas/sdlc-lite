"""Unit tests for the per-agent isolation policy SSOT (policy.py, #30 R1).

These test the pure decision function and predicates directly (no subprocess). The guard
and analyzer are thin callers of `decide()`; their own tests cover the tool-aware wiring.
"""
from __future__ import annotations

import policy
from policy import READ, WRITE, decide

TW = "sdlc-lite:test-writer"
TR = "sdlc-lite:test-reviewer"
IMPL = "sdlc-lite:implementer"
VER = "sdlc-lite:verifier"
CR = "sdlc-lite:code-reviewer"
CONDUCTOR = ""  # empty agent_type == the conductor / main thread

HANDOFF = "/repo/.implement-feature/r/handoff"


# --- role resolution -------------------------------------------------------
def test_role_of_strips_namespace():
    assert policy.role_of(TW) == "test-writer"
    assert policy.role_of(CR) == "code-reviewer"
    assert policy.role_of(VER) == "verifier"  # not confused with code-reviewer


def test_role_of_conductor_and_unknown():
    assert policy.role_of("") is None
    assert policy.role_of("some-other-agent") is None


# --- global: secrets denied to everyone, including the conductor -----------
def test_secret_read_denied_for_conductor():
    d = decide(CONDUCTOR, READ, "/repo/.env")
    assert not d.allowed and d.rule == "secret"


def test_secret_read_denied_for_subagent():
    assert not decide(IMPL, READ, "/repo/config/credentials.json").allowed


def test_ordinary_read_allowed():
    assert decide(IMPL, READ, "/repo/src/app.py").allowed
    assert decide(TW, READ, "/repo/.implement-feature/r/handoff/02-design-interface.md").allowed


# --- global: draft-confinement (subagents only) ----------------------------
def test_subagent_denied_reading_draft():
    d = decide(TW, READ, f"{HANDOFF}/draft/02-design-interface.md")
    assert not d.allowed and d.rule == "draft-confinement"


def test_conductor_may_read_draft():
    assert decide(CONDUCTOR, READ, f"{HANDOFF}/draft/02-design-interface.md").allowed


# --- test-writer algorithm-blindness ---------------------------------------
def test_test_writer_denied_design_internal():
    d = decide(TW, READ, f"{HANDOFF}/03-design-internal.md")
    assert not d.allowed and d.rule == "algorithm-blind"


def test_other_agents_may_read_design_internal():
    assert decide(TR, READ, f"{HANDOFF}/03-design-internal.md").allowed
    assert decide(IMPL, READ, f"{HANDOFF}/03-design-internal.md").allowed


# --- implementer test-integrity --------------------------------------------
def test_implementer_denied_writing_test_file():
    d = decide(IMPL, WRITE, "/repo/tests/test_foo.py")
    assert not d.allowed and d.rule == "test-integrity"


def test_implementer_may_write_source():
    assert decide(IMPL, WRITE, "/repo/src/app.py").allowed


def test_test_writer_may_write_test_file():
    # The test-writer's job IS to write tests — confinement/test-integrity must not bite it.
    assert decide(TW, WRITE, "/repo/tests/test_foo.py").allowed


# --- write-confinement: reviewers + verifier (#29 generalization) ----------
def test_confined_agents_denied_product_write():
    for agent in (TR, VER, CR):
        d = decide(agent, WRITE, "/repo/src/ref.py", handoff_dir=HANDOFF)
        assert not d.allowed and d.rule == "write-confinement", agent


def test_confined_agents_may_write_handoff_outbox():
    assert decide(TR, WRITE, f"{HANDOFF}/06-test-review-findings.md", handoff_dir=HANDOFF).allowed
    assert decide(VER, WRITE, f"{HANDOFF}/07-verify-report.md", handoff_dir=HANDOFF).allowed


def test_confined_agents_may_write_scratch_and_devnull():
    assert decide(CR, WRITE, "/tmp/scratchpad/probe.py", handoff_dir=HANDOFF).allowed
    assert decide(TR, WRITE, "/dev/null", handoff_dir=HANDOFF).allowed


def test_confinement_anchored_not_substring():
    # A product path that merely CONTAINS "/handoff/" or "scratchpad" must not escape.
    assert not decide(TR, WRITE, "/repo/src/handoff/impl.py", handoff_dir=HANDOFF).allowed
    assert not decide(TR, WRITE, "/repo/scratchpad_util.py", handoff_dir=HANDOFF).allowed


def test_confinement_denies_when_handoff_dir_unknown():
    # With no known handoff dir, the outbox can't be recognized -> product write stays denied.
    assert not decide(TR, WRITE, f"{HANDOFF}/06-test-review-findings.md", handoff_dir=None).allowed


# --- Bash parsing helpers (shared vocabulary) ------------------------------
def test_looks_secret_bash_vs_path_split():
    # Bash target is a whole command: scan path-like tokens, not the raw body (#16).
    assert not policy.looks_secret("Bash", "python3 -c \"os.environ.get('X')\"")
    assert policy.looks_secret("Bash", "cat ~/.ssh/id_rsa")
    assert policy.looks_secret("Read", "/repo/.env")


def test_bash_write_targets_and_heredoc_strip():
    assert policy.bash_write_targets("echo hi > out.txt") == ["out.txt"]
    assert policy.bash_write_targets("pytest -q 2>&1") == []  # fd dup, not a file
    # The redirection OUTSIDE a heredoc body is kept; `>` inside the body is not.
    cmd = "cat > f.md <<'EOF'\n> a blockquote\nEOF"
    assert policy.bash_write_targets(cmd) == ["f.md"]


def test_bash_write_targets_in_place_and_copy_forms():
    # #30 R2: sed -i / cp / mv are write forms, not just >/>>/tee.
    assert policy.bash_write_targets("sed -i 's/a/b/' tests/test_foo.py") == ["tests/test_foo.py"]
    assert policy.bash_write_targets("cp ref.py src/app.py") == ["src/app.py"]
    assert policy.bash_write_targets("mv a.py tests/test_b.py") == ["tests/test_b.py"]
    # A plain sed (no -i) writes nothing; a read-only grep writes nothing.
    assert policy.bash_write_targets("sed 's/a/b/' file.py") == []
    assert policy.bash_write_targets("grep -r x src/") == []


# --- R6 wildcard-ban helpers -----------------------------------------------
def test_is_algorithm_blind():
    assert policy.is_algorithm_blind(TW)
    assert not policy.is_algorithm_blind(IMPL)   # implementer may read design-internal
    assert not policy.is_algorithm_blind(CONDUCTOR)


def test_bash_wildcard_handoff_reads():
    assert policy.bash_wildcard_handoff_reads("cat handoff/*.md") == ["handoff/*.md"]
    assert policy.bash_wildcard_handoff_reads("head .../handoff/0[23]-*") == [".../handoff/0[23]-*"]
    # An explicit (non-glob) handoff read is fine; a glob NOT over handoff is fine.
    assert policy.bash_wildcard_handoff_reads("cat handoff/01-requirements.md") == []
    assert policy.bash_wildcard_handoff_reads("ls tests/*.py") == []


# --- #40/#75: critics never run the quality tools (the conductor does, at Gate 7) ---------
def test_runs_quality_tool_detects_mutmut_and_pytest_cov():
    for cmd in ("mutmut run", "mutmut results --all true", "cd /r && mutmut results",
                "python -m pytest --cov=romankit", "pytest -q --cov-report=term-missing",
                "/usr/bin/python3 -m pytest --cov romankit tests",
                "python -m mutmut run"):
        assert policy.runs_quality_tool(cmd), cmd


def test_runs_quality_tool_ignores_plain_tests_and_mentions():
    for cmd in ("pytest -q", "python -m pytest tests", "grep mutmut pyproject.toml",
                "cat mutants.txt", "cat quality/coverage.txt", "echo --cov"):
        assert not policy.runs_quality_tool(cmd), cmd


def test_critic_bash_decision_denies_every_confined_critic():
    for agent in (TR, VER, CR):
        d = policy.critic_bash_decision(agent, "mutmut run")
        assert not d.allowed and d.rule == "critic-quality-tool", agent
        assert not policy.critic_bash_decision(agent, "pytest --cov=x").allowed, agent


def test_critic_bash_decision_allows_conductor_and_producers():
    for agent in (CONDUCTOR, IMPL, TW):
        assert policy.critic_bash_decision(agent, "mutmut run").allowed, agent


def test_critic_bash_decision_allows_critics_plain_pytest():
    assert policy.critic_bash_decision(CR, "python -m pytest -q").allowed


def test_runs_quality_tool_sees_through_launch_prefixes():
    # Gate 6 review: env assignments and launcher wrappers must not hide the run.
    for cmd in ("COVERAGE_FILE=x pytest --cov=romankit", "env A=1 mutmut run",
                "timeout 600 mutmut run", "uv run mutmut run", "(mutmut run)",
                "python -X dev -m pytest --cov", "coverage run -m pytest",
                "python -m coverage run -m pytest"):
        assert policy.runs_quality_tool(cmd), cmd


def test_runs_quality_tool_quoted_pipe_is_not_a_segment():
    assert not policy.runs_quality_tool('grep "a|mutmut run" notes.txt')
    assert not policy.runs_quality_tool("coverage report")   # reads .coverage, writes nothing


# --- #68: critics never change the Python environment (pip install/uninstall) ---------
def test_changes_environment_detects_pip_forms():
    for cmd in ("pip install -e .", "pip3 uninstall -y roman-numeral", "pip3.12 install x",
                "python -m pip install x", "python3 -m pip uninstall -y x",
                "/usr/bin/python3 -m pip install -e .", "uv pip install x",
                "uv pip uninstall x", "uv pip sync requirements.txt", "uv run pip install x",
                "env PIP_NO_INPUT=1 pip install x", "pip -q install x",
                "cd /tmp/mut && pip install -e ."):
        assert policy.changes_environment(cmd), cmd


def test_changes_environment_ignores_read_only_and_mentions():
    for cmd in ("pip list", "pip show roman-numeral", "pip freeze", "python -m pip list",
                "uv pip list", "uv pip freeze", "grep 'pip install' README.md", "echo pip install",
                "python -m pytest -q"):
        assert not policy.changes_environment(cmd), cmd


def test_critic_bash_decision_denies_env_change_for_every_critic():
    for agent in (TR, VER, CR):
        d = policy.critic_bash_decision(agent, "pip install -e .")
        assert not d.allowed and d.rule == "critic-env-change", agent
        assert "pip" in d.reason and "conductor" in d.reason, agent


def test_critic_bash_decision_allows_env_change_for_conductor_and_implementer():
    for agent in (CONDUCTOR, IMPL):
        assert policy.critic_bash_decision(agent, "pip install -e .").allowed, agent
