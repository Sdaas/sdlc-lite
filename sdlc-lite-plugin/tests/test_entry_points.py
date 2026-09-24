"""Entry-point invariants (#55).

Two things broke at once in #55, and both are cheap to assert without a model call:

  1. **No name collision.** A command file whose name matches a skill directory SHADOWS the
     skill: the runtime injects the command's markdown in place of `SKILL.md`, then reports
     the skill as "already loaded", so the body never arrives and a re-invocation cannot
     recover. Measured on all three load paths (directory marketplace, `--plugin-dir`,
     installed-from-umbrella) — see `dev-docs/findings/2026-09-23-skill-suppression-findings.md`.
  2. **Explicit entry.** This plugin's skills start when a human types the slash command.
     The model must not auto-invoke them from a phrasing match, which it demonstrably will
     (measured: a plain "add a to_roman(n) helper, test-first" loaded the whole score).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN))

import policy  # noqa: E402


# --- 1. no command/skill name collision -------------------------------------

def _command_names() -> set[str]:
    d = PLUGIN / "commands"
    return {p.stem for p in d.glob("*.md")} if d.is_dir() else set()


def _skill_names() -> set[str]:
    d = PLUGIN / "skills"
    return {p.name for p in d.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()} if d.is_dir() else set()


def test_no_command_shadows_a_skill():
    collisions = _command_names() & _skill_names()
    assert not collisions, (
        f"command/skill name collision: {sorted(collisions)}. A same-named command file "
        "suppresses the skill's SKILL.md body on every load path (#55) — the skill alone "
        "already registers the slash command, so delete the command file."
    )


def test_the_skill_still_owns_the_entry_point():
    """The entry point users type must keep existing as a skill after the command is gone."""
    assert "implement-feature" in _skill_names()
    assert (PLUGIN / "skills/implement-feature/SKILL.md").read_text().startswith("---")


# --- 2. explicit entry ------------------------------------------------------

@pytest.mark.parametrize("skill", [
    "sdlc-lite:implement-feature",
    "sdlc-lite:analyze-run",
    "sdlc-lite:some-future-workflow",
])
def test_this_plugins_skills_are_never_auto_invoked(skill):
    d = policy.skill_invoke_decision(skill)
    assert not d.allowed
    assert d.rule == "explicit-entry"
    assert "/" in d.reason  # the denial tells the user which slash command to type


@pytest.mark.parametrize("skill", ["pdf", "other-plugin:implement-feature", ""])
def test_other_skills_are_untouched(skill):
    assert policy.skill_invoke_decision(skill).allowed


def test_guard_denies_a_skill_tool_call():
    """End-to-end through the guard's own decision function, not just the policy."""
    sys.path.insert(0, str(PLUGIN / "hooks" / "scripts"))
    import guard  # noqa: E402

    reason = guard._deny_reason("Skill", {"skill": "sdlc-lite:implement-feature"}, "", "")
    assert reason and "explicit-entry only" in reason
    assert guard._deny_reason("Skill", {"skill": "pdf"}, "", "") is None
