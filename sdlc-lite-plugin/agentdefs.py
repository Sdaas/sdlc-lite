"""agentdefs.py — the single source of truth for each isolated gate's MODEL/EFFORT pin.

The pins live in the agent-definition frontmatter (`agents/<role>.md`):

    ---
    name: code-reviewer
    model: claude-opus-4-8
    effort: medium
    ...
    ---

The pins have one consumer: the DETECTIVE analyzer (`analyzer/receipt.py`, #22 legs
(b)/(c)) — it fills the receipt's REQUESTED model/effort columns from these pins and
compares them against the transcript's ACTUAL values (model mismatch = FAIL; effort
deviation = WARN, either direction). This is authoritative — it proves what the run
actually did. Same seam-not-two-copies discipline as `policy.py` for the isolation rules.

Pinned gates are DISPATCHED BARE (no inline `model`); the frontmatter pin — including
the dated reviewer pin — is honored, and the receipt verifies the actual resolved model
against it. #22 originally also had the guard DENY a dispatch that named no model (the
"Witt" deny-if-unnamed technique) on the premise that a frontmatter pin is "silently
droppable"; that premise is FALSE on this platform (a bare-dispatch frontmatter pin IS
honored) and the hook BROKE the dated reviewer pins — the inline `model` lever accepts
only family aliases {sonnet,opus,haiku,fable}, so a forced inline name could only be the
`opus` alias, which (rank-1) overrode the dated `claude-opus-4-8` pin -> `claude-opus-5`.
#36 reverted it. See dev-docs/findings/model-pinning-findings.md §7 and dev-docs/adr/ADR-12-model-effort-integrity.md.

Effort asymmetry (verified against the current Claude Code platform, 2026-09): the
dispatch tool exposes an inline `model` lever but NO `effort` lever — `effort` is
frontmatter-only, so it can only ever be AUDITED after the fact (never forced). Model
does have an inline lever, but it is alias-only and (per #36) is not used: the frontmatter
pin is honored on a bare dispatch. Either way, both pins are proven by the analyzer.

Frontmatter is parsed by hand (no PyYAML dependency): the guard hook must stay
dependency-free, and the frontmatter we read is flat `key: value` lines. Pure w.r.t.
process state; the only I/O is reading the agent-def files. Never raises — a missing
or unparseable agent-def yields no pin (the receipt degrades that column to UNKNOWN),
never a guess.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentPin:
    """One isolated role's pinned model/effort (either may be None if unset)."""
    model: str | None = None
    effort: str | None = None


def _plugin_root() -> str:
    """This module sits at the plugin root (sibling of policy.py and agents/)."""
    return os.path.dirname(os.path.abspath(__file__))


def _agents_dir(plugin_root: str | None = None) -> str:
    return os.path.join(plugin_root or _plugin_root(), "agents")


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Return the flat key->value map from the leading `--- ... ---` YAML frontmatter.

    Only the simple `key: value` lines we depend on (name/model/effort) are needed;
    anything else (lists, nested keys) is ignored. Tolerant by design: a file with no
    frontmatter yields an empty map (the caller then has no pin for it)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip("'\"")
        if key and val:
            out[key] = val
    return out


def load_pins(plugin_root: str | None = None) -> dict[str, AgentPin]:
    """Read every `agents/*.md`, keyed by the frontmatter `name` (the de-namespaced role,
    e.g. 'code-reviewer' — matching the receipt's agent label and policy.role_of()).

    Never raises: an unreadable/unparseable agent-def is simply skipped. A role whose
    frontmatter omits model/effort gets an AgentPin with that field None (honest absence)."""
    pins: dict[str, AgentPin] = {}
    adir = _agents_dir(plugin_root)
    try:
        names = sorted(os.listdir(adir))
    except OSError:
        return pins
    for fn in names:
        if not fn.endswith(".md"):
            continue
        try:
            fm = _parse_frontmatter(open(os.path.join(adir, fn), encoding="utf-8").read())
        except OSError:
            continue
        role = fm.get("name") or fn[:-3]
        pins[role] = AgentPin(model=fm.get("model"), effort=fm.get("effort"))
    return pins


def _role_of(agent_type: str) -> str:
    """De-namespace a (possibly plugin-namespaced) agent/subagent type to its role name,
    e.g. 'sdlc-lite:code-reviewer' -> 'code-reviewer'."""
    return (agent_type or "").split(":", 1)[-1]


def pin_for(agent_type: str, plugin_root: str | None = None) -> AgentPin | None:
    """The pin for one (possibly namespaced) agent/subagent type, or None if it has no
    agent-def (e.g. the conductor / an unknown type)."""
    return load_pins(plugin_root).get(_role_of(agent_type))
