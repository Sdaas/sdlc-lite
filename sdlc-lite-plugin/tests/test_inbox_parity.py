"""Agent inboxes agree with SKILL.md (#61).

Each isolated gate's agent file carries its own "Read (your inbox)" list and steps, and SKILL.md
restates them in its inbox table and gate prose. When the two drift, the agent reads less than the
gate grades it against. Cheap to assert without a model call.
"""
from __future__ import annotations

import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILL = PLUGIN / "skills" / "implement-feature" / "SKILL.md"
STANDARDS = PLUGIN / "skills" / "implement-feature" / "references" / "quality-standards.md"


def _inbox(agent: str) -> str:
    """The agent's `## Read (your inbox)` section."""
    text = (PLUGIN / "agents" / f"{agent}.md").read_text()
    m = re.search(r"^## Read \(your inbox\)\n(.*?)(?=^## )", text, re.S | re.M)
    assert m, f"{agent}.md has no '## Read (your inbox)' section"
    return m.group(1)


def _table_row(gate: str) -> str:
    """SKILL.md's inbox-table row for `gate` (e.g. 'CODE-REVIEW')."""
    m = re.search(rf"^\| {re.escape(gate)} \[I\] \|.*$", SKILL.read_text(), re.M)
    assert m, f"SKILL.md inbox table has no {gate} row"
    return m.group(0)


def _gate_section(heading: str) -> str:
    text = SKILL.read_text()
    m = re.search(rf"^## {re.escape(heading)}.*?(?=^## )", text, re.S | re.M)
    assert m, f"SKILL.md has no '## {heading}' section"
    return m.group(0)


# --- CODE-REVIEW grades against the test plan's thresholds, so it reads it ---

def test_code_reviewer_inbox_lists_test_plan():
    assert "04-test-plan.md" in _inbox("code-reviewer")


def test_skill_code_review_table_row_lists_test_plan():
    assert "04-test-plan.md" in _table_row("CODE-REVIEW")


def test_skill_gate7_inbox_prose_lists_test_plan():
    section = _gate_section("Gate 7 — CODE-REVIEW")
    inbox = section.split("Its inbox:", 1)[1].split("\n\n", 1)[0]
    assert "04-test-plan.md" in inbox


def test_test_reviewer_inbox_lists_test_plan():
    assert "04-test-plan.md" in _inbox("test-reviewer")


# --- VERIFY: the standards file and the concurrency step ---------------------

def test_verifier_inbox_names_standards():
    assert "standards" in _inbox("verifier").lower()


def test_skill_gate6_inbox_prose_names_standards():
    section = _gate_section("Gate 6 — VERIFY")
    inbox = section.split("Its inbox:", 1)[1].split("\n\n", 1)[0]
    assert "standards" in inbox.lower()


def test_verifier_has_concurrency_step():
    text = (PLUGIN / "agents" / "verifier.md").read_text()
    do = text.split("## Do", 1)[1].split("\n## ", 1)[0]
    assert "concurrency" in do.lower()
    assert "stress" in do.lower()
    assert "no concurrency surface" in do


def test_skill_gate6_concurrency_step_matches_verifier():
    section = _gate_section("Gate 6 — VERIFY")
    assert "stress" in section.lower()
    assert "no concurrency surface" in section


# --- quality-standards commands target <code_root>, not a fixed src/ ----------

def test_standards_commands_use_code_root():
    text = STANDARDS.read_text()
    assert "mypy src/" not in text
    assert "--cov=src" not in text
    assert "mypy <code_root>" in text
    assert "--cov=<code_root>" in text
