"""Unit tests for agentdefs.py — the MODEL/EFFORT pin SSOT (#22).

The receipt's requested-column fill (#22 b/c) depends on these pins agreeing with the
shipped agent-defs (the dispatch is bare — the frontmatter pin is honored, then verified;
the model-enforcement hook was reverted in #36). These tests read the REAL `agents/*.md`,
so they also guard against a pin silently drifting from the SKILL model plan, plus the pure
frontmatter parser's edge cases.
"""
from __future__ import annotations

import re
from pathlib import Path

import agentdefs

# The shipped pins, per the SKILL model plan (Gate 0 step 5). If an agent-def changes, this
# test is the tripwire — update it deliberately, together with the SKILL table.
EXPECTED = {
    "test-writer":   ("claude-sonnet-5-5", "medium"),
    "test-reviewer": ("claude-opus-5-5", "medium"),
    "implementer":   ("claude-sonnet-5-5", "medium"),
    "verifier":      ("claude-sonnet-5-5", "medium"),
    "code-reviewer": ("claude-opus-5-5", "medium"),
}


def test_load_pins_matches_shipped_agent_defs():
    pins = agentdefs.load_pins()
    for role, (model, effort) in EXPECTED.items():
        assert role in pins, f"missing pin for {role}"
        assert pins[role].model == model
        assert pins[role].effort == effort


def test_pin_for_strips_plugin_namespace():
    assert agentdefs.pin_for("sdlc-lite:code-reviewer").model == "claude-opus-5-5"
    assert agentdefs.pin_for("code-reviewer").effort == "medium"


def test_pin_for_unknown_or_conductor_is_none():
    assert agentdefs.pin_for("") is None          # conductor (no agent-def)
    assert agentdefs.pin_for("some-other-agent") is None


def test_product_prose_names_only_pinned_models():
    # The frontmatter is the pin SSOT (#63): every dated model id the shipped prose names
    # (SKILL.md tables and render templates, agent bodies, references) must be a current pin,
    # so a bump that misses a prose copy fails here instead of shipping a stale id.
    root = Path(agentdefs.__file__).parent
    pinned = {p.model for p in agentdefs.load_pins().values()}
    named = {
        (str(f.relative_to(root)), m)
        for pattern in ("skills/**/*.md", "agents/*.md")
        for f in root.glob(pattern)
        for m in re.findall(r"claude-(?:opus|sonnet|haiku|fable)-\d[\w-]*", f.read_text())
    }
    assert {(f, m) for f, m in named if m not in pinned} == set()


def test_skill_model_table_rows_name_each_pin():
    # Each `[I]` row of the SKILL.md model plan (Gate 0 step 5) names that gate's pin.
    skill = Path(agentdefs.__file__).parent / "skills/implement-feature/SKILL.md"
    rows = re.findall(r"^\s*\|[^|\n]*\| \[I\] `([\w-]+)` \|([^\n]*)$", skill.read_text(), re.M)
    pins = agentdefs.load_pins()
    assert {role for role, _ in rows} == set(EXPECTED)
    assert "`sonnet` alias" not in skill.read_text()   # producers pin a dated id (#63)
    for role, rest in rows:
        assert pins[role].model in rest, f"SKILL.md model-table row for {role} names a stale model"


def test_parse_frontmatter_flat_keys():
    fm = agentdefs._parse_frontmatter(
        "---\nname: x\nmodel: claude-opus-5-5\neffort: high\ntools: Read, Bash\n---\nbody\n")
    assert fm == {"name": "x", "model": "claude-opus-5-5", "effort": "high",
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
