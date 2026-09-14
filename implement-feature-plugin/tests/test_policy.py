"""Unit tests for the per-agent isolation policy SSOT (policy.py, #30 R1).

These test the pure decision function and predicates directly (no subprocess). The guard
and analyzer are thin callers of `decide()`; their own tests cover the tool-aware wiring.
"""
from __future__ import annotations

import policy
from policy import READ, WRITE, decide

TW = "implement-feature:test-writer"
TR = "implement-feature:test-reviewer"
IMPL = "implement-feature:implementer"
VER = "implement-feature:verifier"
CR = "implement-feature:code-reviewer"
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
