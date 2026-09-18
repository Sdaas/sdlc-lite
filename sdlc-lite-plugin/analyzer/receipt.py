"""Per-agent trust receipt — the #31 schema skeleton.

The receipt is the headline of the audit: ONE record per agent (the conductor and each
isolated gate) attesting to the two guarantees — (a) isolation and (b) bounded
model/effort. Each column is filled by its capability leg:

  - (b) model/effort — REQUESTED from the agent-def pins (agentdefs.py, #22), ACTUAL
    from the transcript; the verdicts compare them (model mismatch = FAIL, effort
    deviation = WARN, either direction). The conductor has no agent-def pin, so its
    requested side stays UNKNOWN (an honest 'nothing to check', never a silent PASS).
  - (a) isolation — which file *content* actually entered each agent's context (#30),
    from the content auditor.

A blind/absent transcript degrades the ACTUAL columns to UNKNOWN, and an un-passed leg
renders UNKNOWN — never a silent PASS. This module is PURE — it derives from a
RunLogAnalysis plus an OPTIONAL TranscriptAnalysis (None when the transcript is
absent/drifted/disabled) plus the pins/audit passed in, and does no I/O.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from .auditor import AuditResult
from .runlog import CONDUCTOR, RunLogAnalysis
from .transcript import TranscriptAnalysis

# Verdicts (and the value sentinel share one token: an unfilled column IS unknown).
UNKNOWN = "UNKNOWN"
PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"


_FAMILIES = ("opus", "sonnet", "haiku", "fable")


def _family(model: str) -> str | None:
    """The model family named in a model string, or None. `claude-opus-4-8`, `opus`,
    `claude-3-opus-20240229` all -> 'opus'."""
    m = model.lower()
    return next((f for f in _FAMILIES if f in m), None)


def _is_alias(model: str) -> bool:
    """A floating alias (`sonnet`, `opus`) carries NO version digits; an explicit/dated id
    (`claude-opus-4-8`, `claude-sonnet-4-5-20250929`) does. This is the split the repo's own
    pinning rationale rests on: reviewers pin a DATED id for reproducible behavior, producers
    pin a floating alias for the-latest-tier."""
    return not any(c.isdigit() for c in model)


def model_matches(requested: str, actual: str) -> bool:
    """Does the ACTUAL (transcript, always a resolved dated id) satisfy the REQUESTED pin?

    Per the #22 decision (exact-if-dated, family-if-alias): an ALIAS pin (`sonnet`) is
    satisfied by any model of the same family (the transcript reports a resolved dated id,
    which an alias can never string-equal); an EXPLICIT/DATED pin (`claude-opus-4-8`) demands
    an EXACT id match — a silent opus-4-8 -> opus-5 drift is a mismatch, honoring the dated
    pin's reproducibility intent."""
    r, a = requested.strip().lower(), actual.strip().lower()
    if not r or not a:
        return False
    if _is_alias(r):
        rf = _family(r)
        return rf is not None and rf == _family(a)
    return r == a


def classify_model(requested: str, actual: str) -> str:
    """Model integrity verdict. A mismatch is trust-voiding -> FAIL. UNKNOWN whenever either
    side is unknown (e.g. no transcript, or the conductor, which has no agent-def pin). The
    match itself is alias/dated-aware — see model_matches (#22)."""
    if requested == UNKNOWN or actual == UNKNOWN:
        return UNKNOWN
    return PASS if model_matches(requested, actual) else FAIL


def classify_effort(requested: str, actual: str) -> str:
    """Effort deviation verdict, per the WIDENED policy (#31): ANY deviation from the pin,
    in EITHER direction (a downgrade *or* an upgrade), is a WARN — effort is the cost knob,
    not trust-voiding, so never a FAIL. UNKNOWN whenever either side is unknown."""
    if requested == UNKNOWN or actual == UNKNOWN:
        return UNKNOWN
    return PASS if requested == actual else WARN


@dataclass
class AgentReceipt:
    label: str
    # (b) bounded model/effort — requested filled by #22; actual filled today.
    requested_model: str = UNKNOWN
    actual_model: str = UNKNOWN
    requested_effort: str = UNKNOWN
    actual_effort: str = UNKNOWN
    # (a) isolation — the concrete file content that entered context, filled by #30.
    # files_content_seen is the human display value; files_verdict is its PASS/FAIL/UNKNOWN
    # glyph driver. A content leak (an artifact a role was forbidden to see, found in its
    # tool output) is trust-voiding -> FAIL. "none" + PASS means the gate WAS scanned and
    # no forbidden content reached it; UNKNOWN means it was not scanned (no transcript, or
    # the conductor, which is not an isolated gate) — never a silent PASS.
    files_content_seen: str = UNKNOWN
    files_verdict: str = UNKNOWN
    # grant/deny counts (the guard's own decision, #31 R4) — filled today from the run-log.
    grants: int = 0
    denies: int = 0
    decision_unknown: int = 0
    # Provenance: the transcript file the actual model/effort were read from, so a developer
    # can open it and cross-check by hand. UNKNOWN when no transcript backed this agent.
    transcript_file: str = UNKNOWN

    @property
    def model_verdict(self) -> str:
        return classify_model(self.requested_model, self.actual_model)

    @property
    def effort_verdict(self) -> str:
        return classify_effort(self.requested_effort, self.actual_effort)


def _joined(values) -> str:
    """A set of observed values -> a stable display string, or UNKNOWN when none were seen
    (so an absent/blind transcript degrades the column, never invents a value)."""
    vals = sorted(v for v in values if v)
    return ", ".join(vals) if vals else UNKNOWN


def _files_column(label: str, audit: AuditResult | None) -> tuple[str, str]:
    """The (display, verdict) for one agent's 'Files seen' column, from the content auditor.

    None audit (no transcript / disabled) -> UNKNOWN, never a silent PASS. A leak is
    trust-voiding -> FAIL, naming the artifact(s). A scanned gate with no leak -> "none" /
    PASS. A label the auditor never scanned (e.g. the conductor) -> UNKNOWN."""
    if audit is None:
        return UNKNOWN, UNKNOWN
    leaked = sorted({os.path.basename(f.artifact)
                     for f in audit.findings if f.agent_label == label})
    if leaked:
        return "LEAK: " + ", ".join(leaked), FAIL
    if label in audit.scanned_agents:
        return "none", PASS
    return UNKNOWN, UNKNOWN


def build_receipt(runlog: RunLogAnalysis,
                  transcript: TranscriptAnalysis | None,
                  audit: AuditResult | None = None,
                  pins: dict | None = None) -> list[AgentReceipt]:
    """Assemble one receipt per agent, correlating the run-log and transcript on the
    de-namespaced agent label (e.g. 'test-writer', 'conductor'). Conductor first, then
    subagents alphabetically (matching the run-log table's ordering). The optional `audit`
    (transcript content-fingerprint, #30 R3) fills the isolation 'Files seen' column.

    `pins` (#22) is the agent-def MODEL/EFFORT SSOT keyed by role label (from
    agentdefs.load_pins()); it fills the REQUESTED columns the model/effort verdicts compare
    against. None (the default, and every role absent from it — e.g. the conductor, which has
    no agent-def) leaves the requested side UNKNOWN: an honest 'no pin to check', never a
    silent PASS."""
    # Run-log side: grant/deny counts, keyed by de-namespaced label.
    grants: dict[str, tuple[int, int, int]] = {}
    for act in runlog.agents.values():
        grants[act.label] = (act.grants, act.denies, act.decision_unknown)

    # Transcript side: actual model(s) + effort(s) + the source file, keyed by the same label.
    actual_models: dict[str, str] = {}
    actual_efforts: dict[str, str] = {}
    source_files: dict[str, str] = {}
    if transcript is not None:
        # The main thread is the conductor.
        if transcript.main:
            actual_models[CONDUCTOR] = _joined(transcript.main.keys())
        if transcript.main_efforts:
            actual_efforts[CONDUCTOR] = _joined(transcript.main_efforts.keys())
        if transcript.main or transcript.main_efforts:
            source_files[CONDUCTOR] = transcript.session_file
        for sub in transcript.subagents:
            actual_models[sub.agent_label] = _joined(sub.by_model.keys())
            actual_efforts[sub.agent_label] = _joined(sub.efforts.keys())
            source_files[sub.agent_label] = sub.session_file

    labels = set(grants) | set(actual_models) | set(actual_efforts)
    ordered = sorted(labels, key=lambda l: (l != CONDUCTOR, l))

    pins = pins or {}
    out: list[AgentReceipt] = []
    for label in ordered:
        g, d, u = grants.get(label, (0, 0, 0))
        files_seen, files_verdict = _files_column(label, audit)
        pin = pins.get(label)  # None for the conductor / any un-pinned role -> UNKNOWN
        out.append(AgentReceipt(
            label=label,
            requested_model=(pin.model if pin and pin.model else UNKNOWN),
            actual_model=actual_models.get(label, UNKNOWN),
            requested_effort=(pin.effort if pin and pin.effort else UNKNOWN),
            actual_effort=actual_efforts.get(label, UNKNOWN),
            files_content_seen=files_seen, files_verdict=files_verdict,
            grants=g, denies=d, decision_unknown=u,
            transcript_file=source_files.get(label, UNKNOWN),
        ))
    return out
