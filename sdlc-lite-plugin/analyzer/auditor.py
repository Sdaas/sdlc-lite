"""Transcript content auditor — the AUTHORITATIVE isolation signal (#30 R3).

The run-log detective (runlog.py) and the guard both key on the *command string* an
agent issued. That shares one blind spot: a glob (`cat handoff/*.md`), an indirect read
(`python -c "print(open('handoff/03-design-internal.md').read())"`), or an `xargs`
pipeline exposes NO resolved path in the record — only the command — so neither the
preventive guard nor the run-log detective can prove what content actually reached the
agent. This module closes that gap by reading the EFFECT, not the intent.

Two signals, roles fixed (the 2026-09-14 design decision):

  1. content-fingerprint  = AUTHORITATIVE / trust-voiding. Read the protected artifact
     (e.g. handoff/03-design-internal.md) from the run's workdir, fingerprint it, and scan
     each subagent transcript's TOOL OUTPUT for that content. A hit voids trust. This is
     the only signal that catches the glob/indirect leak, and it is method-agnostic: the
     content lands in `toolUseResult` string leaves (Read->file.content, Bash->stdout,
     Edit->originalFile, ...) no matter how it was read. See TRANSCRIPT-FORMAT.md §5.

  2. path extraction + best-effort unglob = PRECISE, CORROBORATING (never the authority).
     Explicit file_path from a Read/Edit tool_use is exact; a literal glob is resolved
     against the run's handoff dir to NAME which file would leak. Supporting detail only —
     it shares the command-string blind spot, so it can miss, and it never stands alone.

WHICH artifact a role must not see is delegated to the policy SSOT (policy.decide): a
handoff file is "protected for role R" exactly when the guard would have denied R reading
it with a *content-protection* rule (today: `algorithm-blind` -> design-internal). So the
auditor and the guard agree by construction.

Best-effort satellite (P42): the transcript format is unstable, so every read here is
defensive — a missing/malformed file yields no findings, never an exception. Absence of a
finding is NOT proof of innocence when the transcript is unavailable; that honesty is
carried by the report/receipt layer (an unavailable transcript degrades to UNKNOWN, not
PASS). This module is PURE apart from reading the named files it is handed.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

import policy

# Content-protection deny rules (from policy.decide().rule) that this auditor fingerprints.
# Secrets live outside the handoff dir; draft-confinement is about promotion, not content
# blindness — both are handled elsewhere. Today the one fingerprinted invariant is the
# test-writer's algorithm-blindness (the internal design must never enter its context).
_CONTENT_PROTECTION_RULES = ("algorithm-blind",)

# A fingerprint line must be at least this long (after normalization) to count — short
# lines ("---", "", "## Notes") are boilerplate shared by many files and would false-match.
_MIN_FP_LEN = 40
# Cap how many distinctive lines we fingerprint per artifact (longest first) — enough to
# catch a partial leak (head/tail), bounded so a huge file can't blow up the scan.
_MAX_FPS = 40

_LINENO_RE = re.compile(r"^\s*\d+\t")     # a `cat -n` / Read line-number prefix
_WS_RE = re.compile(r"\s+")


@dataclass
class LeakFinding:
    """One protected artifact whose content was found in a subagent's tool output."""
    agent_label: str
    artifact: str            # path of the protected file that leaked
    rule: str                # the policy rule that makes it protected (e.g. algorithm-blind)
    matched_excerpt: str     # the distinctive line that matched (truncated, for the report)
    session_file: str        # the subagent transcript the leak was found in
    corroboration: str = ""  # non-authoritative: an explicit path / resolved glob, if any


@dataclass
class AuditResult:
    findings: list[LeakFinding] = field(default_factory=list)
    scanned_agents: list[str] = field(default_factory=list)      # agent labels examined
    protected_artifacts: list[str] = field(default_factory=list)  # files checked (any role)

    @property
    def trusted(self) -> bool:
        """No content-leak finding -> the isolation barrier held (for what we could see)."""
        return not self.findings


# --- normalization + fingerprinting ---------------------------------------
def _normalize(text: str) -> str:
    """Collapse a blob to a single line-number-agnostic, whitespace-agnostic string, so a
    file dumped raw (Bash stdout) and the same file shown line-numbered (Read/`cat -n`) both
    match the same fingerprint. Strips a leading `N\\t` per line, then squeezes whitespace."""
    lines = (_LINENO_RE.sub("", ln) for ln in text.splitlines())
    return _WS_RE.sub(" ", " ".join(lines)).strip()


def _fingerprints(artifact_text: str) -> list[str]:
    """Distinctive normalized lines from the artifact, longest first, deduped and capped.
    Each is matched as a substring of the (normalized) haystack; using long lines avoids
    false hits on boilerplate a protected file shares with innocent ones."""
    seen: set[str] = set()
    out: list[str] = []
    for ln in artifact_text.splitlines():
        norm = _WS_RE.sub(" ", _LINENO_RE.sub("", ln)).strip()
        if len(norm) >= _MIN_FP_LEN and norm not in seen:
            seen.add(norm)
            out.append(norm)
    out.sort(key=len, reverse=True)
    return out[:_MAX_FPS]


# --- transcript tool-output extraction (best-effort) -----------------------
def _string_leaves(obj) -> list[str]:
    """Every string leaf of a JSON value — the method-agnostic content collector. A leak
    lands in SOME string field of `toolUseResult` (Read->file.content, Bash->stdout,
    Edit->originalFile, Write->content, Agent->the report string) regardless of the tool,
    so we don't special-case tools: we gather them all."""
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        return [s for v in obj.values() for s in _string_leaves(v)]
    if isinstance(obj, list):
        return [s for v in obj for s in _string_leaves(v)]
    return []


def _tool_output_haystack(session_file: str) -> str:
    """Normalized concatenation of ALL tool output in a transcript: the structured
    `toolUseResult` (primary — raw bytes) plus any `tool_result` block content (secondary —
    the model-facing view, covers the rare case where toolUseResult is absent). Defensive:
    unreadable/malformed lines are skipped, never raised."""
    try:
        lines = _read_text(session_file).splitlines()
    except OSError:
        return ""
    chunks: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        tur = rec.get("toolUseResult")
        if tur is not None:
            chunks.extend(_string_leaves(tur))
        # secondary: tool_result blocks inside a user message (str or list of blocks)
        msg = rec.get("message")
        if isinstance(msg, dict):
            for blk in (msg.get("content") or []):
                if isinstance(blk, dict) and blk.get("type") == "tool_result":
                    chunks.extend(_string_leaves(blk.get("content")))
    return _normalize("\n".join(chunks))


def _explicit_read_paths(session_file: str) -> list[str]:
    """Corroborating (non-authoritative): explicit file_path/paths from Read/Edit/Grep/Glob
    tool_use blocks, and literal glob tokens from Bash commands. Names WHICH file an agent
    reached for; shares the command-string blind spot, so it is supporting detail only."""
    try:
        lines = _read_text(session_file).splitlines()
    except OSError:
        return []
    paths: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict) or rec.get("type") != "assistant":
            continue
        for blk in ((rec.get("message") or {}).get("content") or []):
            if not (isinstance(blk, dict) and blk.get("type") == "tool_use"):
                continue
            ti = blk.get("input") or {}
            fp = ti.get("file_path") or ti.get("path")
            if isinstance(fp, str) and fp:
                paths.append(fp)
            cmd = ti.get("command")
            if isinstance(cmd, str) and cmd:
                paths.extend(policy.bash_wildcard_handoff_reads(cmd))
    return paths


# --- the audit -------------------------------------------------------------
def _protected_for_role(agent_type: str, handoff_dir: str) -> list[tuple[str, str]]:
    """(artifact_path, rule) for each handoff file this role must NOT see by content — i.e.
    a file the policy SSOT would deny it reading with a content-protection rule. Ties the
    auditor to the guard: they agree on WHAT is protected, by construction."""
    out: list[tuple[str, str]] = []
    try:
        names = sorted(os.listdir(handoff_dir))
    except OSError:
        return out
    for name in names:
        path = os.path.join(handoff_dir, name)
        if not os.path.isfile(path):
            continue
        d = policy.decide(agent_type, policy.READ, path, handoff_dir)
        if not d.allowed and d.rule in _CONTENT_PROTECTION_RULES:
            out.append((path, d.rule))
    return out


def _agent_type_of(agent_label: str) -> str:
    """policy.role_of substring-matches, so a de-namespaced label ('test-writer') is a
    valid agent_type to hand it; pass it through unchanged."""
    return agent_label


def audit_content_leaks(transcript, handoff_dir: str | None) -> AuditResult:
    """Scan each subagent transcript for the content of any artifact that agent's role was
    forbidden to see. `transcript` is a transcript.TranscriptAnalysis (its `.subagents`
    give per-agent session files + labels); `handoff_dir` is the run's real handoff dir
    (where the protected artifacts live). Returns an AuditResult; a leak voids trust.

    Best-effort: with no transcript, no subagents, or no handoff dir, returns an empty
    (trusted) result — the caller degrades the receipt to UNKNOWN rather than a false PASS.
    """
    result = AuditResult()
    if transcript is None or not handoff_dir:
        return result

    for sub in getattr(transcript, "subagents", []) or []:
        label = sub.agent_label
        result.scanned_agents.append(label)
        protected = _protected_for_role(_agent_type_of(label), handoff_dir)
        if not protected:
            continue
        for path, _rule in protected:
            if path not in result.protected_artifacts:
                result.protected_artifacts.append(path)

        haystack = _tool_output_haystack(sub.session_file)
        if not haystack:
            continue
        corrob = _explicit_read_paths(sub.session_file)
        for path, rule in protected:
            try:
                fps = _fingerprints(_read_text(path))
            except OSError:
                continue
            hit = next((fp for fp in fps if fp in haystack), None)
            if hit is None:
                continue
            named = next((p for p in corrob if os.path.normpath(p) == os.path.normpath(path)
                          or os.path.basename(path) in p), "")
            result.findings.append(LeakFinding(
                agent_label=label, artifact=path, rule=rule,
                matched_excerpt=(hit[:160] + "…") if len(hit) > 160 else hit,
                session_file=sub.session_file,
                corroboration=(f"explicit reference: {named}" if named else ""),
            ))
    return result


def _read_text(path: str) -> str:
    """Small seam so tests and callers share one reader (utf-8, errors replaced so a binary
    blob in a transcript never crashes the scan)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()
