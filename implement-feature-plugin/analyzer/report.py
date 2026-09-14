"""Report assembler — pure Markdown rendering, no I/O, no exception handling.

The orchestration (which reader to call, and catching the transcript's typed
errors) lives in analyze_run.py. This module only turns already-computed results
into text, so it is trivially testable and cannot itself fail a run.

The run-log section is ALWAYS rendered. The transcript section is rendered from
one of three inputs the caller supplies after quarantining the satellite:
  - a TranscriptAnalysis            -> the token/cost table
  - ("absent", reason)              -> a soft, expected "skipped" note
  - ("drift",  reason)              -> a LOUD "format changed, update parser" alarm
"""
from __future__ import annotations

import os

from .auditor import AuditResult
from .receipt import FAIL, PASS, UNKNOWN, WARN, AgentReceipt
from .runlog import RunLogAnalysis
from .transcript import ModelUsage, TranscriptAnalysis


def _fmt(n: int) -> str:
    return f"{n:,}"


_VERDICT_GLYPH = {PASS: "✅", FAIL: "❌", WARN: "⚠️", UNKNOWN: "❔"}


def render_runlog(a: RunLogAnalysis) -> str:
    lines: list[str] = ["## Run-log analysis (stable / load-bearing)", ""]
    window = "—"
    if a.window_start and a.window_end:
        window = f"{a.window_start:%Y-%m-%d %H:%M:%S}Z .. {a.window_end:%H:%M:%S}Z"
    lines += [
        f"- Source: `{a.path}`",
        f"- Tool calls: **{_fmt(a.total_entries)}**"
        + (f"  ({_fmt(a.orchestration_entries)} orchestration record(s))"
           if a.orchestration_entries else "")
        + (f"  ({a.malformed_lines} malformed line(s) skipped)" if a.malformed_lines else ""),
        f"- Run window: {window}",
        "",
        "### Per-agent activity",
        "",
        "| Agent | Calls | Tools | Files read | Files written |",
        "|---|---:|---|---:|---:|",
    ]
    # Conductor first, then subagents alphabetically.
    for atype in sorted(a.agents, key=lambda t: (t != "", t)):
        act = a.agents[atype]
        tools = ", ".join(f"{k}×{v}" for k, v in sorted(act.tool_counts.items()))
        lines.append(
            f"| {act.label} | {act.total_calls} | {tools} "
            f"| {len(act.reads)} | {len(act.writes)} |"
        )

    lines += ["", "### Isolation compliance", ""]
    for c in a.checks:
        mark = "✅" if c.passed else "❌"
        lines.append(f"- {mark} **{c.name}** — {c.detail}")
        if not c.passed and c.evidence:
            for ev in c.evidence[:10]:
                lines.append(f"    - `{ev}`")
    verdict = "✅ all isolation checks passed" if a.all_passed else "❌ isolation VIOLATION(S) detected"
    lines += ["", f"**Verdict: {verdict}.**", ""]
    return "\n".join(lines)


def _render_usage_table(title: str, buckets: dict[str, ModelUsage]) -> list[str]:
    if not buckets:
        return [f"_{title}: none_", ""]
    out = [
        f"**{title}**", "",
        "| Model | Turns | Input | Output | Thinking | Cache read | Cache write |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for mu in sorted(buckets.values(), key=lambda m: m.model):
        out.append(
            f"| {mu.model} | {mu.turns} | {_fmt(mu.input_tokens)} | {_fmt(mu.output_tokens)} "
            f"| {_fmt(mu.thinking_tokens)} | {_fmt(mu.cache_read_tokens)} "
            f"| {_fmt(mu.cache_creation_tokens)} |"
        )
    out.append("")
    return out


def _render_subagent_table(subs: list) -> list[str]:
    if not subs:
        return ["_Per-subagent (isolated gates): none found_", ""]
    out = [
        "**Per-subagent (isolated gates) — the per-gate model split**", "",
        "| Subagent | Model | Turns | Input | Output | Thinking |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for sub in sorted(subs, key=lambda s: s.agent_label):
        for mu in sorted(sub.by_model.values(), key=lambda m: m.model):
            out.append(
                f"| {sub.agent_label} | {mu.model} | {mu.turns} | {_fmt(mu.input_tokens)} "
                f"| {_fmt(mu.output_tokens)} | {_fmt(mu.thinking_tokens)} |"
            )
    out.append("")
    return out


def render_transcript(t: TranscriptAnalysis) -> str:
    lines = [
        "## Token / cost analysis (best-effort, from transcript)", "",
        f"- Source: `{t.session_file}`",
        f"- Assistant turns in window: **{t.turns_in_window}**",
        f"- Subagent transcripts found: **{len(t.subagents)}**", "",
    ]
    lines += _render_usage_table("Conductor / main thread", t.main)
    lines += _render_subagent_table(t.subagents)
    lines += _render_usage_table("Subagents / sidechains (aggregate by model)", t.sidechain)
    return "\n".join(lines)


def render_transcript_unavailable(mode: str, reason: str) -> str:
    if mode == "absent":
        return "\n".join([
            "## Token / cost analysis (best-effort, from transcript)", "",
            f"ℹ️  **Skipped — no transcript found.** {reason}",
            "",
            ("This is expected when the run happened outside the sandbox or the "
             "session log is unavailable. The run-log analysis above is complete."),
            "",
        ])
    # "drift" or any unexpected failure -> loud alarm.
    return "\n".join([
        "## Token / cost analysis (best-effort, from transcript)", "",
        "⚠️  **TRANSCRIPT ANALYSIS UNAVAILABLE**",
        "",
        f"    Reason: {reason}",
        "",
        "    A transcript WAS found but could not be parsed. The Claude Code",
        "    transcript format has likely changed; the analyzer's transcript",
        "    parser needs updating (see `analyzer/transcript.py`).",
        "",
        "    ► The run-log analysis above is unaffected and complete.",
        "",
    ])


def render_content_audit(audit: AuditResult | None) -> str:
    """The AUTHORITATIVE isolation section (#30 R3/R4): did any content an isolated gate was
    forbidden to see actually reach it? This reads the transcript's tool OUTPUT, so unlike
    the run-log section it catches glob/indirect leaks. A finding marks the run UNTRUSTED.

    `audit is None` (no transcript) is NOT a pass — it renders as UNKNOWN, because absence of
    the transcript is absence of proof, never proof of innocence."""
    head = "## Content isolation audit (authoritative — from transcript tool output)"
    if audit is None:
        lines = [head, "", (
            "❔ **UNKNOWN — not run.** The content audit requires the session transcript "
            "(it scans each gate's tool *output*). No transcript was available, so isolation "
            "here is **unproven, not passed** — see the run-log section for the intent-level "
            "checks that do not need the transcript."), ""]
        return "\n".join(lines)
    lines = [head, ""]
    if audit.scanned_agents:
        lines.append(f"- Isolated gates scanned: {', '.join(sorted(audit.scanned_agents))}")
    if audit.protected_artifacts:
        arts = ", ".join(f"`{os.path.basename(p)}`"
                         for p in sorted(audit.protected_artifacts))
        lines.append(f"- Content-protected artifacts checked: {arts}")
    lines.append("")
    if not audit.findings:
        lines += [(
            "✅ **No forbidden content reached any isolated gate.** For every gate scanned, "
            "none of the artifacts its role must not see were found in its tool output."), ""]
        return "\n".join(lines)
    # Findings -> the run is untrusted. Make it unmissable.
    lines += [(
        "❌ **CONTENT LEAK DETECTED — THIS RUN IS UNTRUSTED.** An artifact a gate was "
        "forbidden to see was found in its tool output (the isolation barrier was breached). "
        "Investigate before trusting this run's result:"), ""]
    for f in audit.findings:
        lines.append(f"- ❌ **{f.agent_label}** saw `{os.path.basename(f.artifact)}` "
                     f"(forbidden by rule *{f.rule}*)")
        lines.append(f"    - matched content: `{f.matched_excerpt}`")
        if f.corroboration:
            lines.append(f"    - {f.corroboration}")
        lines.append(f"    - evidence transcript: `{f.session_file}`")
    lines.append("")
    return "\n".join(lines)


def _grant_deny_cell(r: AgentReceipt) -> str:
    cell = f"{r.grants} / {r.denies}"
    if r.decision_unknown:  # legacy (pre-R4) lines with no recorded decision
        cell += f" (?{r.decision_unknown})"
    return cell


def render_receipt(receipts: list[AgentReceipt], runlog_path: str | None = None) -> str:
    """The per-agent trust receipt (#31 schema). Columns needing a requested value (model /
    effort → #22) or content-level detection (files seen → #30) render ❔ UNKNOWN — an honest
    verdict, never a silent PASS. Each model/effort cell leads with its own deviation glyph.
    A Sources block cites the exact files the receipt was derived from for manual cross-check."""
    lines = [
        "## Per-agent trust receipt", "",
        ("The receipt for the two guarantees — **(a) isolation** and **(b) bounded "
         "model/effort**. Each row compares the **requested** pin (agent-def frontmatter) "
         "against the **actual** value (transcript): a model mismatch is trust-voiding (❌), an "
         "effort deviation is a ⚠️ (the cost knob, not trust). `❔ UNKNOWN` is a valid, honest "
         "verdict — a blind/absent transcript degrades the *actual* columns, and the conductor "
         "has no agent-def pin to check; never a silent PASS."), "",
        "| Agent | Model (req → actual) | Effort (req → actual) | Files seen | Grants / Denies |",
        "|---|---|---|---|---|",
    ]
    for r in receipts:
        mg = _VERDICT_GLYPH[r.model_verdict]
        eg = _VERDICT_GLYPH[r.effort_verdict]
        fg = _VERDICT_GLYPH[r.files_verdict]
        lines.append(
            f"| {r.label} "
            f"| {mg} {r.requested_model} → {r.actual_model} "
            f"| {eg} {r.requested_effort} → {r.actual_effort} "
            f"| {fg} {r.files_content_seen} "
            f"| {_grant_deny_cell(r)} |"
        )
    lines += [
        "",
        ("_Legend: ✅ matches pin / no forbidden content · ⚠️ effort deviates (either "
         "direction) · ❌ model mismatch or content leak (run untrusted) · ❔ unknown (no pin, "
         "or transcript blind). Model match is alias/dated-aware: an alias pin (`sonnet`) "
         "accepts any same-family tier, a dated pin (`claude-opus-4-8`) demands an exact id. "
         "Grants / Denies is the guard's own decision per call; `(?N)` = N legacy calls with "
         "no recorded decision._"),
        "",
        "### Sources (for manual cross-check)", "",
        "The exact evidence this receipt was derived from — open these to verify any cell by hand:",
        "",
        f"- Run-log (grants/denies): `{runlog_path or UNKNOWN}`",
        "- Transcripts (actual model/effort), per agent:",
    ]
    for r in receipts:
        lines.append(f"    - {r.label}: `{r.transcript_file}`")
    lines.append("")
    return "\n".join(lines)


def assemble(sections: list[str]) -> str:
    header = "# /implement-feature run report\n"
    return header + "\n" + "\n".join(sections).rstrip() + "\n"
