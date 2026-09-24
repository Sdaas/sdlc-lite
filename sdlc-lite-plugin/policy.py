"""policy.py — the single per-agent isolation policy (the #30 SSOT / seam).

Isolation between /implement-feature gates used to live as scattered `if` branches in
`hooks/scripts/guard.py`, re-implemented by hand in `analyzer/runlog.py` under "KEEP IN
SYNC" comments. Both read the SAME run-log through the SAME substring predicates, so a
single Bash trick bypassed *both* legs at once — the two "legs" shared one blind spot.

This module makes the two mechanisms **import one definition** instead of each owning a
copy:

  - the PREVENTIVE guard hook (`guard.py`) — real-time, best-effort for Bash;
  - the DETECTIVE analyzer (`analyzer/`) — post-hoc, and (from #30 R3) transcript-based.

It owns three things, all pure (no I/O, no process exit):

  1. the shared **predicates** — `looks_secret`, `is_test_path`, the design-internal /
     draft path tests, the reviewer write-confinement test, and the Bash command parsing
     (`bash_tokens`, `strip_heredocs`, `bash_write_targets`). These are the vocabulary both
     legs must agree on; defining them once is the whole point.
  2. a per-agent **rule table** (`POLICY`) — for each isolated role, what it may read /
     write, expressed as data. Deny-by-default is honored structurally in `decide()`:
     reads default to "anything except the explicit deny set"; writes are either
     unrestricted-minus-a-deny (the producers) or **confined** to an allow-list (the
     read-only critics).
  3. `decide(agent_type, access, path, handoff_dir)` — the single allow/deny authority for
     one (agent, access, path) tuple, returning a `Decision`. The guard extracts targets
     from a tool call (tool-aware; Bash best-effort) and calls this per target; the analyzer
     (next) extracts targets from the transcript and calls the SAME function.

Deliberate widening (documented, not accidental): a restrictive *read* allow-list is
impossible for the producer roles — the implementer and verifier legitimately read the
whole repo and the stdlib. So `readable` is "everything minus the deny set", and the deny
set carries the real invariants (secrets, design-internal for the test-writer, unapproved
drafts for any subagent). The seam still lets a role's reads be tightened later; today only
the deny set bites.
"""
from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass, field

# --- access kinds ----------------------------------------------------------
READ = "read"
WRITE = "write"

# The conductor (main thread) logs with an EMPTY agent_type. It authors and reviews the
# drafts and is not an isolated gate — global secret-deny still applies to it, but the
# per-role read/write rules do not.
CONDUCTOR = "conductor"

# The five isolated roles, matched as a SUBSTRING of the (possibly plugin-namespaced)
# agent_type — e.g. "sdlc-lite:test-writer" -> "test-writer". The four hyphenated
# names are mutually distinct substrings; "verifier" is distinct from "code-reviewer".
ROLES = ("test-writer", "test-reviewer", "implementer", "verifier", "code-reviewer")


def role_of(agent_type: str) -> str | None:
    """The isolated role named by `agent_type`, or None for the conductor / an unknown
    agent. Substring match keeps it namespace-tolerant (mirrors the historical guard)."""
    at = agent_type or ""
    for r in ROLES:
        if r in at:
            return r
    return None


# --- secret detection (PATH-aware, tool-split) -----------------------------
# #16: the old code substring-matched these against the tool's whole target. For a Bash
# call the target is the ENTIRE command string, so `python -c "os.environ.get('X')"`
# tripped the ".env" hint (it is inside "os.environ"). Fix: match PATH COMPONENTS, and for
# Bash scan only tokens that actually look like file paths — never the raw command body.
_SECRET_EXTS = (".pem", ".key")                       # matched as a component suffix
_SECRET_NAMES = ("id_rsa", "id_ed25519", "credentials", ".netrc", ".pgpass")  # in a component
_SECRET_FRAGMENTS = (".ssh/", ".aws/credentials")     # matched anywhere in the path


def is_secret_component(comp: str) -> bool:
    return (comp == ".env" or comp.startswith(".env.")
            or comp.startswith("secrets.")
            or comp.endswith(_SECRET_EXTS)
            or any(n in comp for n in _SECRET_NAMES))


def is_secret_path(target: str) -> bool:
    """True if `target`, read as a filesystem path, points at a secret. Over-broad on
    purpose for real file targets (a false positive just makes an agent ask again)."""
    t = target.strip().strip("'\"").lower().replace("\\", "/")
    if not t:
        return False
    if any(frag in t for frag in _SECRET_FRAGMENTS):
        return True
    return any(is_secret_component(c) for c in t.split("/") if c)


def _bash_token_is_secret(token: str) -> bool:
    """Stricter than is_secret_path: only flag a Bash token that clearly denotes a secret
    FILE (a path, a dotfile, or a secret extension). A bare identifier like `environ` or
    `credentials` in a command is NOT a file read — don't false-deny it."""
    t = token.strip().strip("'\"").lower().replace("\\", "/")
    if not t:
        return False
    pathlike = ("/" in t) or t.startswith(".") or t.endswith(_SECRET_EXTS)
    return pathlike and is_secret_path(t)


def bash_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()  # unbalanced quotes (common in code heredocs): degrade safely


def looks_secret(tool: str, target: str) -> bool:
    """Secret-read predicate, split by tool. Bash scans path-like tokens (never the raw
    command body, #16); every other tool's target IS a path -> path-component match."""
    if tool == "Bash":
        return any(_bash_token_is_secret(tok) for tok in bash_tokens(target))
    return is_secret_path(target)


# --- test-path / design-internal / draft predicates ------------------------
def is_test_path(target: str) -> bool:
    base = os.path.basename(target)
    return ("/tests/" in target or "/test/" in target
            or base.startswith("test_") or base.endswith("_test.py")
            or base == "conftest.py")


def is_design_internal(target: str) -> bool:
    """The algorithm-blind file. Substring match is prefix-tolerant: the numbered
    `03-design-internal.md` still trips it."""
    return "design-internal" in target


def is_draft(target: str) -> bool:
    """A file under handoff/draft/ — an unapproved draft. The conductor promotes on
    approval; only then is a copy readable at handoff/."""
    return "handoff/draft/" in target.replace("\\", "/")


# --- write-confinement (reviewers / verifier: the read-only critics) -------
# A Bash-granted critic can't be made read-only by removing Write/Edit (P44), so we enforce
# the property we actually want: it NEVER mutates the product tree. Its only sanctioned
# writes are its outbox (under the run's handoff dir) and throwaway probes in a scratch dir.
#
# Both allow-list checks are ANCHORED (a real temp-root prefix / the run's ACTUAL handoff
# dir), not free substrings — a product-tree path that merely *contains* "scratchpad",
# "/scratch/", or "/handoff/" (e.g. `src/handoff/impl.py`) must NOT escape confinement.
_TEMP_ROOTS = ("/tmp/", "/private/tmp/", "/var/folders/")


def is_scratch_path(t: str) -> bool:
    if t == "/tmp":
        return True
    tn = t if t.endswith("/") else t + "/"
    return any(tn.startswith(root) for root in _TEMP_ROOTS)


def is_within(target: str, base_dir: str | None) -> bool:
    """True if `target` is `base_dir` itself or lives under it (anchored, normalized).
    False when `base_dir` is None/empty (unknown handoff dir -> nothing is 'inside' it)."""
    if not base_dir:
        return False
    base = os.path.normpath(base_dir)
    tn = os.path.normpath(target)
    return tn == base or tn.startswith(base + os.sep)


def confined_write_denied(target: str, handoff_dir: str | None) -> bool:
    """True if a write-confined agent must NOT write here (i.e. not its outbox/scratch)."""
    t = target.strip().strip("'\"").replace("\\", "/")
    if not t:
        return False
    if t.startswith("/dev/"):
        return False   # /dev/null etc. are the bit bucket, not the product tree
    if is_within(t, handoff_dir):
        return False   # its named outbox (06-…/07-… .md) lives under the run's handoff/
    if is_scratch_path(t):
        return False   # tiny throwaway probes are legitimate (P45)
    return True        # anything else = the product tree / repo -> denied


# --- Bash write-target extraction ------------------------------------------
# Heredoc start: `<<`, optional `-`, optional ws, optional quote, delimiter word.
_HEREDOC_RE = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def strip_heredocs(command: str) -> str:
    """Drop heredoc *bodies* so their literal text (e.g. markdown `>` blockquotes) is never
    mistaken for shell redirections. The `cmd > file <<EOF` redirection sits OUTSIDE the
    body and is preserved."""
    lines = command.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        out.append(lines[i])
        m = _HEREDOC_RE.search(lines[i])
        i += 1
        if m:
            delim = m.group(2)
            while i < len(lines) and lines[i].strip() != delim:
                i += 1
            i += 1  # consume the terminator line (not a command)
    return "\n".join(out)


def bash_write_targets(command: str) -> list[str]:
    """Best-effort: the paths a Bash command redirects/writes into. Covers shell
    redirections (`>`, `>>`, `tee`) AND the recognizable in-place/copy write FORMS
    (`sed -i`, `cp`, `mv`) that #30 R2 calls out. Bash write-detection is inherently
    fragile (P44) — key on the targets we can see; the transcript auditor is the backstop."""
    toks = bash_tokens(strip_heredocs(command))
    targets: list[str] = []
    for i, tok in enumerate(toks):
        stripped = tok.lstrip("012")  # 1>, 2>> ...
        if stripped in (">", ">>", ">|") and i + 1 < len(toks):
            targets.append(toks[i + 1])
        elif stripped.startswith(">") and len(stripped) > 1:
            targets.append(stripped.lstrip(">|"))   # `>file` with no space
        elif tok == "tee" and i + 1 < len(toks):
            nxt = toks[i + 1]
            targets.append(nxt if not nxt.startswith("-")
                           else (toks[i + 2] if i + 2 < len(toks) else ""))
    targets += _command_write_targets(toks)
    # Drop fd-duplication targets (`2>&1`, `>&2`): `&N` is a descriptor, not a file write.
    return [t for t in targets if t and not t.startswith("&")]


def _command_write_targets(toks: list[str]) -> list[str]:
    """Best-effort write targets of the in-place/copy write COMMANDS (`sed -i`, `cp`, `mv`).
    Heuristic (deliberately simple, P44): the LAST non-option operand is the write target —
    the file `sed -i` edits in place, the destination `cp`/`mv` writes. Misses multi-file
    forms and is only a real-time backstop; the transcript auditor is authoritative."""
    if not toks:
        return []
    prog = os.path.basename(toks[0].strip("'\""))
    operands = [t for t in toks[1:] if not t.startswith("-")]
    if prog == "sed":
        in_place = any(t == "-i" or t.startswith("-i") or t == "--in-place"
                       for t in toks[1:])
        # For `sed`, the first non-option operand is the SCRIPT, the rest are files.
        return operands[1:] if in_place and len(operands) > 1 else []
    if prog in ("cp", "mv", "install") and len(operands) >= 2:
        return [operands[-1]]   # the destination
    return []


# --- the per-agent rule table (data, not code) -----------------------------
@dataclass(frozen=True)
class AgentPolicy:
    """One isolated role's read/write rules, as data.

    read_denied  — named predicates that void a READ (checked against the target path).
    write_confined — True: writes allowed ONLY to the run's handoff outbox + a scratch dir
                     (the read-only critics). False: writes allowed except write_denied.
    write_denied — named predicates that void a WRITE (only meaningful when not confined).
    """
    read_denied: tuple = ()
    write_confined: bool = False
    write_denied: tuple = ()


# Predicates referenced by name so the table stays declarative. Each takes the target path.
_DESIGN_INTERNAL = "design-internal"
_TEST_PATH = "test-path"
_PRED = {
    _DESIGN_INTERNAL: is_design_internal,
    _TEST_PATH: is_test_path,
}

# Global rules apply to EVERY agent (including the conductor):
#   - secrets are denied to read for anyone (checked directly in decide());
#   - drafts are denied to every SUBAGENT (any non-empty agent_type) — see decide().

POLICY: dict[str, AgentPolicy] = {
    # Algorithm-blind: must not read the internal design. (A wildcard read that could
    # resolve to it is additionally banned by the guard's R6 rule.)
    "test-writer":   AgentPolicy(read_denied=(_DESIGN_INTERNAL,)),
    # Read-only critics — write-confined to their handoff outbox + scratch (subsumes #29:
    # verifier & code-reviewer get the same confinement the test-reviewer already had).
    "test-reviewer": AgentPolicy(write_confined=True),
    "verifier":      AgentPolicy(write_confined=True),
    "code-reviewer": AgentPolicy(write_confined=True),
    # Producer: writes code freely but must not weaken the tests.
    "implementer":   AgentPolicy(write_denied=(_TEST_PATH,)),
}


def is_algorithm_blind(agent_type: str) -> bool:
    """True if this agent must not see the internal design (the test-writer). Used by the
    R6 wildcard-ban: such an agent may not run an unresolvable wildcard read over handoff/,
    since the glob could expand to 03-design-internal.md."""
    pol = POLICY.get(role_of(agent_type) or "")
    return bool(pol and _DESIGN_INTERNAL in pol.read_denied)


_GLOB_CHARS = ("*", "?", "[")


def bash_wildcard_handoff_reads(command: str) -> list[str]:
    """#30 R6 (best-effort): glob tokens in a Bash command that reference the handoff dir.
    The literal design-internal substring rule cannot see `03-design-internal.md` through a
    wildcard (`cat handoff/*.md`, `head handoff/0[23]-*`), so for an algorithm-blind agent
    we BAN the wildcard rather than allow-and-hope — read the needed files by exact name.
    Returns the offending glob tokens (empty = none). Cannot catch a `cd handoff && cat *`
    that hides the segment; the transcript auditor is the authoritative backstop."""
    out: list[str] = []
    for tok in bash_tokens(command):
        t = tok.strip().strip("'\"").replace("\\", "/")
        if any(c in t for c in _GLOB_CHARS) and "handoff/" in (t + "/"):
            out.append(tok)
    return out


@dataclass
class Decision:
    allowed: bool
    rule: str = ""       # short slug of the rule that fired (for the audit / reason)
    reason: str = ""     # human-facing explanation (used verbatim by the guard on deny)


_ALLOW = Decision(allowed=True)


# --- explicit entry: this plugin's skills are never auto-invoked (#55) -------
#
# A skill is reachable two mechanically distinct ways, and only ONE of them is the
# product's entry point (both verified empirically — see the #55 finding):
#
#   1. the user TYPES `/implement-feature` — the CLI expands the slash command and injects
#      SKILL.md directly. **No `Skill` tool call happens**, so this path never reaches the
#      hook and is unaffected by the rule below.
#   2. the model decides on its own, from a phrasing match against the skill `description` —
#      this goes through the `Skill` TOOL, which PreToolUse sees.
#
# So denying (2) yields explicit-only entry exactly, with no need to guess at intent. The
# rule is plugin-wide rather than per-skill: every skill this plugin ships is a gated,
# repo-mutating workflow that a human starts deliberately, and a future skill inherits the
# policy instead of having to remember it.
PLUGIN_SKILL_PREFIX = "sdlc-lite:"


def is_plugin_skill(skill: str) -> bool:
    """True for a skill shipped by THIS plugin (namespaced `sdlc-lite:<name>`)."""
    return skill.strip().startswith(PLUGIN_SKILL_PREFIX)


def skill_invoke_decision(skill: str) -> Decision:
    """Adjudicate a `Skill` tool call. Denies this plugin's own skills; allows all others.

    Deny-by-default within our namespace: the workflow starts when a human types the slash
    command, never because a request happened to sound like it.
    """
    if not is_plugin_skill(skill):
        return _ALLOW
    name = skill.strip()[len(PLUGIN_SKILL_PREFIX):] or skill.strip()
    return Decision(False, "explicit-entry",
                    f"the {name} workflow is explicit-entry only: it starts when the user "
                    f"types /{name}, not from a phrasing match. Tell the user to type "
                    f"/{name} if they want to run it.")


def decide(agent_type: str, access: str, target: str,
           handoff_dir: str | None = None) -> Decision:
    """The single allow/deny authority for one (agent, access, path) tuple.

    `access` is READ or WRITE. `target` is a resolved path for single-target tools; for a
    Bash-derived target the CALLER (guard / analyzer) has already extracted it. `handoff_dir`
    is the run's real handoff dir (anchors write-confinement); None when unknown.

    Global rules (any agent, conductor included): secret reads are denied; any SUBAGENT
    reading an unapproved draft is denied. Then the per-role table applies.
    """
    role = role_of(agent_type)
    is_subagent = bool(agent_type)  # empty agent_type == conductor (main thread)

    if access == READ:
        # Global: secrets. (looks_secret is tool-split; a resolved path is not Bash here,
        # so the path form is correct.)
        if is_secret_path(target):
            return Decision(False, "secret",
                            "reading secrets/.env is not allowed "
                            f"(target: {os.path.basename(target) or target[:60]}).")
        # Global: no subagent may read an unapproved draft.
        if is_subagent and is_draft(target):
            return Decision(False, "draft-confinement",
                            "handoff/draft/ holds unapproved drafts. Subagents read only "
                            "promoted files under handoff/. (Conductor promotes on approval.)")
        pol = POLICY.get(role) if role else None
        if pol:
            for name in pol.read_denied:
                if _PRED[name](target):
                    if name == _DESIGN_INTERNAL:
                        return Decision(False, "algorithm-blind",
                                        "the test-writer is algorithm-blind and must not "
                                        "read design-internal.md.")
                    return Decision(False, name, f"read denied by policy ({name}).")
        return _ALLOW

    if access == WRITE:
        pol = POLICY.get(role) if role else None
        if pol is None:
            return _ALLOW
        if pol.write_confined:
            if confined_write_denied(target, handoff_dir):
                return Decision(False, "write-confinement",
                                f"{role} is an analytical/verifying gate — it may write only "
                                "its handoff/ outbox and throwaway probes in a scratch dir, "
                                f"never the product tree (target: {target[:80]}).")
            return _ALLOW
        for name in pol.write_denied:
            if _PRED[name](target):
                if name == _TEST_PATH:
                    return Decision(False, "test-integrity",
                                    "the implementer must make the code pass the tests, not "
                                    "modify the tests. Editing test files is not allowed.")
                return Decision(False, name, f"write denied by policy ({name}).")
        return _ALLOW

    return _ALLOW  # unknown access kind: fail open (never break a tool we don't model)
