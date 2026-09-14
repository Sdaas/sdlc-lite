"""agentdefs.py — the single source of truth for each isolated gate's MODEL/EFFORT pin.

The pins live in the agent-definition frontmatter (`agents/<role>.md`):

    ---
    name: code-reviewer
    model: claude-opus-4-8
    effort: high
    ...
    ---

Two independent consumers need those pins and must agree on them (the same
seam-not-two-copies discipline as `policy.py` for the isolation rules):

  - the PREVENTIVE guard hook (`hooks/scripts/guard.py`, #22 leg (a)) — on a
    `Task`/`Agent` dispatch it looks up the pinned model and DENIES a dispatch that
    carries no explicit `model`. NOTE (#36): this leg is being reverted. Its premise —
    "a frontmatter pin is rank-2 and silently droppable, so promote it to a rank-1
    per-invocation argument" — is FALSE on this platform (a bare-dispatch frontmatter
    pin IS honored), and it BREAKS the dated reviewer pins: the inline `model` lever
    accepts only family aliases {sonnet,opus,haiku,fable}, so a forced inline name can
    only be the `opus` alias, which (rank-1) overrides the dated `claude-opus-4-8`
    frontmatter pin -> the reviewer resolves to `claude-opus-5`. See
    design/model-pinning-findings.md §7.
  - the DETECTIVE analyzer (`analyzer/receipt.py`, #22 legs (b)/(c)) — it fills the
    receipt's REQUESTED model/effort columns from these pins and compares them
    against the transcript's ACTUAL values (model mismatch = FAIL; effort deviation
    = WARN, either direction). This half is authoritative and unaffected by #36.

Effort asymmetry (verified against the current Claude Code platform, 2026-09): the
dispatch tool exposes an inline `model` lever but NO `effort` lever — `effort` is
frontmatter-only, so it can only be AUDITED after the fact. (Model does have an inline
lever, but it is alias-only and — per #36 — need not and should not be used: the
frontmatter pin is honored on a bare dispatch.) This module carries both pins; the
audit lives in the analyzer (both), and the model-enforcement leg in the guard is
being removed (#36). See the developer-guide ADR-12.

Frontmatter is parsed by hand (no PyYAML dependency): the guard hook must stay
dependency-free, and the frontmatter we read is flat `key: value` lines. Pure w.r.t.
process state; the only I/O is reading the agent-def files. Never raises — a missing
or unparseable agent-def yields no pin (the receipt degrades that column to UNKNOWN,
and the guard fails OPEN on it), never a guess.
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
    e.g. 'implement-feature:code-reviewer' -> 'code-reviewer'."""
    return (agent_type or "").split(":", 1)[-1]


def pin_for(agent_type: str, plugin_root: str | None = None) -> AgentPin | None:
    """The pin for one (possibly namespaced) agent/subagent type, or None if it has no
    agent-def (e.g. the conductor / an unknown type)."""
    return load_pins(plugin_root).get(_role_of(agent_type))
