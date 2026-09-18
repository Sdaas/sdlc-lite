# Transcript & `.meta.json` format — a reader's field guide

A teaching aid for anyone working on `transcript.py`. It shows **where** Claude Code writes the
session transcript and the per-subagent files, **what shape** the records have, and **which field
the analyzer depends on** for each thing it reports.

> ⚠️ **This format is officially internal and unstable.** It is documented here so a maintainer can
> recognise it and update the parser when it drifts — not as a stable contract. `transcript.py` is a
> deliberately-quarantined satellite for exactly this reason: when these fields disappear, the parser
> raises `TranscriptFormatError` (a loud "format changed" alarm) rather than guessing. The
> *verified-against-a-real-run* proof model lives in
> [`design/audit-observability-findings.md`](../../design/audit-observability-findings.md);
> this file is the quick on-disk reference.

---

## 1. Where the files live

Claude Code keeps one directory per project under the projects root
(`$CLAUDE_CONFIG_DIR/projects`, default `~/.claude/projects`). The project dir is named by the
project's absolute path with every `/` turned into `-`:

```
~/.claude/projects/
└── -Users-sdaas-dev-sdlc-lite/              # project dir = abs path, '/' -> '-'
    ├── 4667b56e-….jsonl                     # the CONDUCTOR / main-thread transcript
    └── 4667b56e-…/                          # dir named by the main file's STEM (no .jsonl)
        └── subagents/
            ├── agent-ad150d6e….jsonl        # one ISOLATED-GATE subagent transcript
            └── agent-ad150d6e….meta.json    # its launch-time sidecar (see §4)
```

Key relationships the parser relies on (`_subagents_dir`, `_agent_label_from_meta`):

- The main transcript is `<dir>/<uuid>.jsonl`; its subagents sit under `<dir>/<uuid>/subagents/`
  (the subdir is named by the main file's **stem**, not the full filename).
- Each `<agent>.jsonl` has a sibling `<agent>.meta.json` with the same stem.
- The analyzer does **not** trust "newest file" — it picks the main transcript by **time-window
  correlation** against the run-log's `[min ts, max ts]` (padded ±5 min). See `find_transcript`.

## 2. The main transcript — JSONL, one record per line

Each line is a JSON object with a `type`. The analyzer only cares about `type: "assistant"`
records; everything else (`user`, `attachment`, …) is skipped. A representative assistant record:

```json
{
  "type": "assistant",
  "timestamp": "2026-09-12T18:04:11.500Z",
  "isSidechain": false,
  "effort": "medium",
  "message": {
    "model": "claude-opus-4-8",
    "usage": {
      "input_tokens": 1200,
      "output_tokens": 340,
      "cache_read_input_tokens": 8000,
      "cache_creation_input_tokens": 512,
      "output_tokens_details": { "thinking_tokens": 210 }
    }
  }
}
```

The fields `transcript.py` reads, and why:

| Field | Where | The parser uses it for |
|---|---|---|
| `type` | top level | keep only `"assistant"` records |
| `timestamp` | top level | correlate the turn to the run window (`Z`/UTC) |
| `isSidechain` | top level | split **main thread** (`false`) vs **sidechain** (`true`) |
| **`effort`** | **top level** (sibling of `message`) | the **actual effort** the turn ran at (#31 R3) |
| `message.model` | inside `message` | the **actual resolved model** (ground truth, e.g. `claude-opus-4-8`) |
| `message.usage.*` | inside `message` | input/output/cache/thinking tokens |

Two easy mistakes this table prevents:

- **`effort` is top-level, not inside `message`.** It sits beside `message`, one per assistant turn.
- **`message.model` is the *resolved* id** (`claude-opus-4-8`), which differs from the *requested
  alias* (`"opus"`) recorded in `.meta.json` (§4). Model integrity (#22) compares the two.

### Schema self-check (drift alarm)
If a file has assistant turns but **none** carry `message.model` + `message.usage`, the format has
almost certainly changed: the parser raises `TranscriptFormatError` instead of reporting an empty
result. An absent *optional* field (like `effort`) is different — it simply yields no effort buckets,
which later degrades the effort verdict to **UNKNOWN**, never a silent PASS.

## 3. Subagent transcripts — same record shape, separate files

Isolated-gate subagents (test-writer, implementer, …) are **not** inlined in the main transcript.
Each runs in its own `<dir>/<uuid>/subagents/<agent>.jsonl` with the **same assistant-record shape**
as §2 (top-level `effort`, `message.model`, `message.usage`). Their turns typically carry
`isSidechain: true`. `parse_subagents` reads each file into a per-gate `SubagentUsage` (model + token
+ effort breakdown) and folds it into the sidechain aggregate.

This whole subtree is **extra-best-effort**: a missing/unreadable/malformed subagents dir yields an
empty breakdown and does not even mark the main section as drift.

## 4. `.meta.json` — the launch-time request sidecar

One `<agent>.meta.json` sits next to each subagent transcript. It records what was **requested at
launch** (intent), as opposed to the transcript's record of what actually **ran** (effect):

```json
{
  "agentType": "general-purpose",
  "description": "Audit Phase 5 completeness",
  "toolUseId": "toolu_01TA6spFqhMRzUjYEsPn6gpA",
  "spawnDepth": 1,
  "model": "opus"
}
```

- **`model` is the requested *alias*** (`"opus"`), not the resolved id — pair it with the
  transcript's `message.model` to check model integrity (#22).
- **There is no `effort` field here.** Requested effort is knowable only from the agent-def
  frontmatter (static config), so effort integrity compares the *pin* against the transcript's
  top-level `effort`.
- **`agentType`** is how a subagent transcript is attributed to a gate. `_agent_label_from_meta`
  is defensive: it tries several likely keys (`agentType`, `subagent_type`, `type`, `name`, …),
  strips any `plugin:` namespace, and falls back to the file stem if the meta is missing/unparseable.

## 5. Tool *results* — where the content actually is (`user` records)

§2–§4 cover *intent* (what an agent asked for) and *metadata* (model/effort/tokens), all on
`assistant` records. The content auditor (`auditor.py`, #30 R3) needs the opposite: the
*effect* — the actual bytes a tool returned into an agent's context. That lives on
**`user`-type records**, not assistant ones, in **two** places per tool call:

```json
{
  "type": "user",
  "isSidechain": true,
  "timestamp": "2026-09-12T02:19:00.501Z",
  "message": {
    "role": "user",
    "content": [
      { "type": "tool_result",
        "tool_use_id": "toolu_01C7z…",
        "content": "1\t---\n2\tname: …" }      // model-facing view (see the gotcha below)
    ]
  },
  "toolUseResult": {                             // structured, RAW — the primary source
    "type": "text",
    "file": { "filePath": "…/03-design-internal.md", "content": "---\nname: …", "numLines": 53 }
  }
}
```

- **`toolUseResult` (top-level) is the primary content source** and its shape is
  **tool-specific** — but the real bytes are always in **string leaves**:

  | Tool | String leaf holding the content |
  |---|---|
  | `Read` | `toolUseResult.file.content` (raw) + `.file.filePath` |
  | `Bash` | `toolUseResult.stdout` + `.stderr` ← catches `cat handoff/*.md`, `python -c open(...)`, xargs |
  | `Edit` | `toolUseResult.originalFile` (the whole pre-edit file) + `.filePath` |
  | `Write` | `toolUseResult.content` + `.filePath` |
  | `Agent` | `toolUseResult` is a plain **string** (the subagent's final report) |

  Because a leak lands in *some* string leaf whatever the tool, `auditor.py` does **not**
  special-case tools — it recursively collects every string leaf (`_string_leaves`). That
  is what makes the content signal **method-agnostic**, and the whole reason it is the
  *authoritative* isolation check: a glob or indirect read exposes no path on the
  `assistant` `tool_use` (only the command), but its output still shows up here.

- **`message.content[]` `tool_result` blocks are the secondary source** (the model-facing
  view). `content` is usually a **string** but can be a **list** of blocks (images,
  `tool_reference` metadata) — handle both; only text carries leakable content.

- **Gotcha — two views of the same file differ.** A `Read` shows up line-number-prefixed
  (`1\t…`, `cat -n` style) in the `tool_result` block, but **raw** in
  `toolUseResult.file.content`; a `cat` in Bash `stdout` is raw. So a content fingerprint
  **must be line-number- and whitespace-agnostic** — `auditor._normalize` strips a leading
  `\d+\t` per line and squeezes whitespace so all three views match one fingerprint.

- **Attribution.** These `user` records live in the **same file** as the turns that caused
  them: subagent tool results are in `<uuid>/subagents/<agent>.jsonl` (§3), with
  `isSidechain: true`. The auditor scans each subagent file for the artifacts that agent's
  role was forbidden to see — *which* artifact is decided by `policy.decide()`, so the
  auditor and the guard agree on what "protected" means by construction.

- **Field the auditor depends on:** `toolUseResult` (any tool) and, secondarily,
  `message.content[].content` for `type:"tool_result"` blocks. If `toolUseResult` disappears
  or moves, the content signal silently finds nothing — so treat its absence as **UNKNOWN,
  never PASS** at the receipt layer (an unavailable transcript is not proof of innocence).

> Discovery note (2026-09-14): `Grep`/`Glob` results did not appear in the sampled
> transcripts, so their `toolUseResult` shape is unconfirmed. The recursive-string-leaf
> collector needs no per-tool schema, so it handles them regardless; document their shape
> here if you capture a real one.

## 6. If you're here because the parser broke

1. Grab a real transcript from a recent dev-container run under `~/.claude/projects/<slug>/`.
2. Diff a `type:"assistant"` record against §2 — which depended-on field moved or renamed?
3. Update `transcript.py` (and the `assistant_turn` factory in `tests/conftest.py` to match), then
   re-run `python -m pytest analyzer/tests -q`.
4. Update the tables above so the next maintainer sees the current shape.
