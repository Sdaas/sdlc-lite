"""Per-agent trust receipt — the #31 schema skeleton.

The receipt is the headline of the audit: ONE record per agent (the conductor and each
isolated gate) attesting to the two guarantees — (a) isolation and (b) bounded
model/effort. This module fixes that record's SHAPE now, so the two legs each just fill
their column later instead of inventing partial shapes reconciled at the end:

  - #22 supplies the REQUESTED model/effort (agent-def pin / .meta.json) and the
    match verdict against the actual values;
  - #30 supplies which file *content* actually entered each agent's context.

Until then those columns render UNKNOWN — a deliberately honest verdict, never a
silent PASS. The columns whose raw data already exists are filled today: the actual
model + effort (from the transcript) and the guard's grant/deny counts (from the
run-log). This module is PURE — it derives from a RunLogAnalysis plus an OPTIONAL
TranscriptAnalysis (None when the transcript is absent/drifted/disabled), and does no I/O.
"""
from __future__ import annotations

from dataclasses import dataclass

from .runlog import CONDUCTOR, RunLogAnalysis
from .transcript import TranscriptAnalysis

# Verdicts (and the value sentinel share one token: an unfilled column IS unknown).
UNKNOWN = "UNKNOWN"
PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"


def classify_model(requested: str, actual: str) -> str:
    """Model integrity verdict. A mismatch is trust-voiding -> FAIL. UNKNOWN whenever
    either side is unknown (the skeleton state: requested is always UNKNOWN until #22,
    which also supplies the alias↔resolved-id comparison this placeholder equality lacks)."""
    if requested == UNKNOWN or actual == UNKNOWN:
        return UNKNOWN
    return PASS if requested == actual else FAIL


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
    files_content_seen: str = UNKNOWN
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


def build_receipt(runlog: RunLogAnalysis,
                  transcript: TranscriptAnalysis | None) -> list[AgentReceipt]:
    """Assemble one receipt per agent, correlating the run-log and transcript on the
    de-namespaced agent label (e.g. 'test-writer', 'conductor'). Conductor first, then
    subagents alphabetically (matching the run-log table's ordering)."""
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

    out: list[AgentReceipt] = []
    for label in ordered:
        g, d, u = grants.get(label, (0, 0, 0))
        out.append(AgentReceipt(
            label=label,
            actual_model=actual_models.get(label, UNKNOWN),
            actual_effort=actual_efforts.get(label, UNKNOWN),
            grants=g, denies=d, decision_unknown=u,
            transcript_file=source_files.get(label, UNKNOWN),
        ))
    return out
