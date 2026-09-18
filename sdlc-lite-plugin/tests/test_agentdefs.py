"""Unit tests for agentdefs.py — the MODEL/EFFORT pin SSOT (#22).

The receipt's requested-column fill (#22 b/c) depends on these pins agreeing with the
shipped agent-defs (the dispatch is bare — the frontmatter pin is honored, then verified;
the model-enforcement hook was reverted in #36). These tests read the REAL `agents/*.md`,
so they also guard against a pin silently drifting from the SKILL model plan, plus the pure
frontmatter parser's edge cases.
"""
from __future__ import annotations

import agentdefs

# The shipped pins, per the SKILL model plan (Gate 0 step 5). If an agent-def changes, this
# test is the tripwire — update it deliberately, together with the SKILL table.
EXPECTED = {
    "test-writer":   ("sonnet", "medium"),
    "test-reviewer": ("claude-opus-4-8", "medium"),
    "implementer":   ("sonnet", "medium"),
    "verifier":      ("sonnet", "medium"),
    "code-reviewer": ("claude-opus-4-8", "medium"),
}


def test_load_pins_matches_shipped_agent_defs():
    pins = agentdefs.load_pins()
    for role, (model, effort) in EXPECTED.items():
        assert role in pins, f"missing pin for {role}"
        assert pins[role].model == model
        assert pins[role].effort == effort


def test_pin_for_strips_plugin_namespace():
    assert agentdefs.pin_for("sdlc-lite:code-reviewer").model == "claude-opus-4-8"
    assert agentdefs.pin_for("code-reviewer").effort == "medium"


def test_pin_for_unknown_or_conductor_is_none():
    assert agentdefs.pin_for("") is None          # conductor (no agent-def)
    assert agentdefs.pin_for("some-other-agent") is None


def test_parse_frontmatter_flat_keys():
    fm = agentdefs._parse_frontmatter(
        "---\nname: x\nmodel: claude-opus-4-8\neffort: high\ntools: Read, Bash\n---\nbody\n")
    assert fm == {"name": "x", "model": "claude-opus-4-8", "effort": "high",
                  "tools": "Read, Bash"}


def test_parse_frontmatter_absent_yields_empty():
    assert agentdefs._parse_frontmatter("no frontmatter here\n") == {}
    assert agentdefs._parse_frontmatter("") == {}


def test_load_pins_tolerates_missing_fields(tmp_path):
    # A custom plugin root with an agent-def that omits effort -> pin.effort is None (honest
    # absence), never a guess; a file without frontmatter -> a pin with both None.
    adir = tmp_path / "agents"
    adir.mkdir()
    (adir / "solo.md").write_text("---\nname: solo\nmodel: sonnet\n---\n")
    (adir / "bare.md").write_text("just prose, no frontmatter\n")
    pins = agentdefs.load_pins(str(tmp_path))
    assert pins["solo"].model == "sonnet" and pins["solo"].effort is None
    assert pins["bare"].model is None and pins["bare"].effort is None


def test_load_pins_missing_dir_is_empty(tmp_path):
    assert agentdefs.load_pins(str(tmp_path / "nope")) == {}
