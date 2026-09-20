# Prior art & gap analysis — `implement-feature` vs the agentic-SDLC field

_Dated 2026-09-20. Research doc, not a plan: it records what five comparable systems actually
do (read from source, not READMEs), what `sdlc-lite` does better, and where the gaps are that
cap the professional quality of the code and tests it emits. Nothing here is committed work —
the current milestone is still `1.0.0` (#43, #44, #37, #19)._

_§4 was added in a second pass, on the observation that the DESIGN gate is upstream of every
other quality lever — and is the one bias-sensitive gate with neither an independent reviewer
nor a pinned model._

---

## 0. Scope and method

**Question asked:** what is missing from `/implement-feature` (and the commands around it)
such that its output is *genuinely professional quality*?

**Method.** Cloned and read the sources — `SKILL.md`, agent definitions, prompt templates,
reference files — for five systems, then read our own `SKILL.md` (636 lines), five agent
defs, `quality-standards.md`, the templates, and the ADR list in the Developer Guide. No
conclusion below rests on a README.

| System | What it is | Read at | Scale |
|---|---|---|---|
| **obra/superpowers** | Opinionated multi-skill process system, subagent-orchestrated | `5bf4e78`, 2026-09-18 (v6.4.1) | 15 skills, 119 md |
| **addyosmani/agent-skills** | Lifecycle skill pack + 9 slash commands + 4 personas | `c004a74`, 2026-09-17 (v0.6.10) | 25 skills, 95 md |
| **mattpocock/skills** | Small composable skills, deliberately *not* a framework | `c55ee46`, 2026-09-18 | 38 skills, 116 md |
| **Fission-AI/OpenSpec** | Spec-as-source-of-truth SDD with a real CLI (~52k★) | cloned 2026-09-20 | CLI + 12 skills |
| **gsd-build/get-shit-done** | Heavyweight multi-agent context-engineering system (~48–59k★) | cloned 2026-09-20 | 33 agents, 66 commands, 786 md |

The extra two were picked by search: OpenSpec and GSD are the two most-starred systems in this
space and are the two architectural cousins of a gated pipeline (OpenSpec = artifact
dependency graph; GSD = orchestrator + pinned subagents + gates). Matt Pocock's README names
GSD, BMAD and Spec-Kit as the "own the process" camp he is reacting against — useful framing,
because `sdlc-lite` is squarely in that camp.

---

## 1. Where the five actually differ

Reduced to one axis each, because the differences matter more than the feature lists:

- **superpowers** — *the controller is the product*. A ledger file, dispatch briefs as files,
  a five-round fix loop with a defined breaker, per-finding adjudication with written
  "rulings", and an explicit refusal to stall on the human. The most mature *loop mechanics*
  in the field.
- **addyosmani** — *the checklist is the product*. Five-axis review, a Definition of Done, a
  `CONSTRAINTS.md` quality bar with numbers the user chose, and a bar-weakening guard. Plus
  the only real **eval harness** for skills. The most mature *quality-bar* thinking.
- **mattpocock** — *the vocabulary is the product*. Deep modules, seams, `CONTEXT.md` shared
  language, tracer-bullet tickets, and the sharpest short statement of test doctrine in the
  field. Deliberately owns no process: "approaches like GSD, BMAD and Spec-Kit… take away
  your control and make bugs in the process hard to resolve."
- **OpenSpec** — *the spec is the product*. Specs live in git as the durable source of truth;
  changes are ADDED/MODIFIED/REMOVED deltas that merge back on archive. Brownfield-first,
  "dependencies are enablers, not gates," progressive rigor (lite vs full spec).
- **GSD** — *the orchestration is the product*. A four-type gate taxonomy, model profiles with
  a four-level resolution ladder and failure-tier escalation, context-degradation tiers, and
  a stub-detection doctrine ("Existence ≠ Implementation").

---

## 2. What `sdlc-lite` already does better than all five

This matters for the gap list: several "gaps" below are deliberate trade-offs that buy these,
and the recommendations are shaped to not spend them.

1. **Isolation is enforced, not requested.** The PreToolUse guard hook (`guard.py`) *denies*
   at the tool call. Every other system relies on prose — superpowers writes four paragraphs
   of "You Do Not Dispatch Subagents" into three separate prompt templates because a worker
   once spawned its own reviewer. Nobody else has a hook. **This is the single biggest
   differentiator and nothing in this document should erode it.**
2. **The algorithm-blind test-writer.** The interface/internal design split (`02-` shared,
   `03-` withheld, hook-enforced) has no equivalent anywhere. Addy's TDD skill gestures at it
   ("spawn a subagent to write the reproduction test… this separation ensures the test is
   written without knowledge of the fix") but it is one informal paragraph, not a mechanism.
3. **Independent test review before any implementation exists (Gate 4).** Unique. Every other
   system reviews tests as part of a post-implementation diff review, where the reviewer can
   see the code that makes them pass. Gate 4 is a genuinely stronger position, and the "no
   reference implementation, analytical only" constraint (P45) is the right call.
4. **Empirical mutation testing against the shipped code, with an anchored threshold.**
   Superpowers has a *mental* mutation check; addy lists Stryker in a tools table; nobody
   runs it in the loop. You run `mutmut` at Gate 7 against real code with an 80% anchor and a
   justify-any-deviation rule (P46).
5. **Model-pin verification.** The receipt compares the pin in `agents/*.md` against the
   *actual* model from the transcript; a mismatch is a FAIL. GSD has a far richer model
   *policy* (profiles, phase maps, dynamic routing) but verifies nothing after the fact.
   Superpowers just says "always specify the model explicitly."
6. **Un-mocked boundary verification as a distinct role.** The boundary inventory →
   VERIFY-exercises-it-un-mocked contract is a stronger version of what GSD calls
   "Existence ≠ Implementation" and OpenSpec calls `/opsx:verify`, because it is a named
   fresh-eyes agent with a per-boundary obligation rather than a checklist.
7. **The interview.** Gate 1's design-tree/frontier/rounds method with `❓`/`➡️` formatting is
   effectively identical to mattpocock's `grilling` — independent convergence on the best
   version in the field — and the P57 smallest-viable anchor is an improvement none of the
   five have.

**Summary:** on *vertical depth for one feature*, `sdlc-lite` leads the field. The gaps are in
**durability, decomposition, loop mechanics, and the feedback loop on the workflow itself**.

---

## 3. Tier A — gaps that directly cap output quality

Ordered by impact on the stated goal. **The DESIGN gate is treated separately in §4** — it is
upstream of every item here, and its gaps are structural rather than incremental.

### A1. Test-quality doctrine is thin, and `mutmut` is carrying it alone

`test-writer.md` tells the writer: implement the plan's inventory, be mutation-minded, use
`match=` on messages, cover transport faults. That is a good *coverage* doctrine and a thin
*test-quality* doctrine. Five specific rules that ≥2 of the five carry and we do not:

- **No mirror assertions / tautologies.** Expected values must be hand-derived literals, never
  computed by the code under test or its helpers. Superpowers makes this Principle 1 of
  `writing-good-tests.md`; mattpocock names it as one of three anti-patterns with the
  identical worked example. This is *the* characteristic failure of an LLM writing tests from
  a design doc, and mutmut does not reliably catch it — a mirror assertion often survives
  mutation because both sides move together.
- **No change detectors.** A test that can only fail on an intentional decision
  (`assert MAX_RETRIES == 5`) fires on redesign and sleeps through bugs.
- **"Name the break" gate.** Before writing a test body: name the production change that would
  make it fail, and confirm that change is a *bug*, not a *decision*.
- **Mock doctrine.** Mock only at system boundaries; mirror the real structure completely;
  never assert on the mock. Our un-mocked VERIFY gate is a strong backstop — stronger than
  anyone else's — but nothing stops the *unit* suite from being a mock farm that VERIFY then
  quietly compensates for.
- **DAMP over DRY in tests** (addy). Relevant because a writer optimising for terseness hides
  expected values behind shared helpers, which is how mirror assertions get in.

**Recommendation.** Add `references/test-quality.md` to the skill; put it in the *test-writer's*
and *test-reviewer's* inbox. Pure Markdown, no code, no architecture change. Highest
quality-per-unit-effort item in this document.

### A2. Re-review is unscoped, so the bounded loop cannot converge

Gate 7 says: on CHANGES-REQUESTED, repair, then "re-converge forward (→ VERIFY →
CODE-REVIEW)" — a full whole-diff review every round, by a fresh Opus reviewer. A fresh
strong reviewer on the same code finds *new* things every pass. The loop will therefore hit
its bound for reasons unrelated to the findings it was opened on.

Superpowers solves this with a separate **scoped re-review** prompt: it receives the findings
list verbatim plus *only the fix diff*, verdicts each finding `ADDRESSED | NOT ADDRESSED`
("'Attempted' is not addressed"), reports new breakage **in the fix diff only**, and sends
anything noticed outside it to the ledger — "it does not block this task and does not extend
the loop."

**Recommendation.** Add a scoped re-review mode to `code-reviewer.md` (findings + fix range,
per-finding verdict, no wandering). This is the single highest-leverage fix for loop
convergence and cost.

### A3. Findings have a repair target but no severity, and the loop bound has no defined exit

Typing findings `→IMPLEMENT` / `→TESTS` is genuinely good and unique to us. But without
severity, *every* finding enters the bounded loop, including nits — and at the bound, SKILL.md
says only "surface to the human," with no contract for what is surfaced.

All five grade findings. Addy is explicit about why: severity labels "prevent authors from
treating all feedback as mandatory and wasting time on optional suggestions." Superpowers goes
further and defines the exit: Minor findings never enter the loop (ledgered, and the final
review triages them — "a roll-up nobody reads is a silent discard"); at the cap, the controller
adjudicates *each* open finding, parks it with a written **ruling**, distinguishes load-bearing
from not, and surfaces every ruling in the final message, because "a ruling that dies with the
workspace was a decision made in secret."

**Recommendation.** Add severity (Critical/Important/Minor) to the findings contract alongside
the existing repair tag; Minor never loops but lands in Gate 8; at the bound, require a written
per-finding ruling that the human reads at Gate 8/9.

### A4. No resumability — and this is the most expensive failure superpowers reports

Gate 0 step 0 says it plainly: *"There is no in-workflow resume yet; a stale lock is removed by
hand."* `run-log.jsonl` is an **audit** log written for the analyzer, not a **recovery** map
read at Gate 0.

Both superpowers execution skills open with the same warning, from real sessions:
"Conversation memory does not survive compaction. In real sessions, controllers that lost their
place have re-dispatched entire completed task sequences — the single most expensive failure
observed." Their fix is a ledger whose first line names the plan, `Task N: complete` lines, and
the instruction "after compaction, trust the ledger and `git log` over your own recollection."

A 12-gate run on a non-trivial feature *will* compact. The quality consequence is not just
wasted tokens — a conductor that loses its place can silently skip a gate.

**Recommendation.** Make the run-log resumable: Gate 0 step 0 offers RESUME (read the log, find
the last completed gate, re-enter at the next) as a third option beside finish/abandon.

### A5. Reviewers are not told to distrust the producer, and silence isn't permission

Two clauses every strong reviewer prompt in the field carries, and ours do not:

- **"Do not trust the report."** Superpowers: "Treat the implementer's report as unverified
  claims… Design rationales in the report are claims too: 'left it per YAGNI'… is the
  implementer grading their own work. A stated rationale never downgrades a finding's
  severity." Our `code-reviewer` reads the diff and the design but has no such instruction,
  and the implementer *is* asked to return "implementation notes worth carrying to review
  (e.g. a deliberate trade-off)" — i.e. we hand the reviewer the author's self-justification
  with no instruction on how to weigh it.
- **"The spec is a vision document."** Superpowers: "For behavior the spec is silent on, judge
  by what a reasonable person using this software would expect… a spec's silence is not
  permission. Grade such findings by their effect on that person, not by whether the spec
  mentions the trigger." This matters *specifically* for us, because our whole pipeline is
  "the approved artifact is the contract" — which is exactly the condition that produces
  "the requirements didn't mention it, so it's not a finding." We already have one hardcoded
  instance of the principle in `quality-standards.md` (don't conflate "no configurable
  timeout" with "no need to test timeout behaviour") but not the principle itself.
- Related: superpowers' **"Declined to judge"** list — the reviewer enumerates every behaviour
  it considered and set aside as out of scope, one line each, and the controller rules on each.
  Nothing is dropped silently.

**Recommendation.** Add all three to `code-reviewer.md` and the first two to `test-reviewer.md`.
Markdown-only.

### A6. No standing project quality bar, and nothing guards the bar from being weakened

`quality-standards.md` is the *plugin's* bar and a good SSOT. What's missing is the *project's*
bar and the guard on it. Addy's `constraint-driven-development` makes the argument better than
I can paraphrase: an agent writes more in an afternoon than you read in a week, so judgement has
to move out of your head and into checks that run in the loop, with numbers the user actually
chose. Two concrete holes:

- **The numbers are the agent's, not the user's.** Coverage % and mutation kill-rate are set by
  the conductor at Gate 2 and approved by the human per feature. There is no once-per-project
  bar. (Our 80% mutation anchor is a good partial answer to threshold-drift — it just lives in
  the wrong scope.)
- **Nothing detects bar-weakening.** The guard hook blocks the implementer from editing test
  files — best-in-class, nobody else does this — but nothing stops it adding `# type: ignore`,
  `# noqa`, `except: pass`, or `raise NotImplementedError`, and nothing stops the *test-writer*
  emitting an assertion-free test. Addy names the five moves to watch (threshold moved, a test
  got easier, a checker got silenced, work left unfinished, an exception appeared) and notes
  all five are detectable from `git diff` alone. GSD frames the same thing as stub detection
  under "Existence ≠ Implementation."

**Recommendation.** A diff-scoped floor check at Gate 7 (or in `guard.py`, which is already the
sanctioned place for code). Optionally, later, a per-project `CONSTRAINTS.md` the workflow reads.

### A7. Every check in the bar is circular

Addy's test: *can the agent make this pass by writing code that doesn't work?* Checks rank
External (WCAG, a CVE database, a real browser) > Project (your lint rules) > Suite (your own
tests — "the only genuinely circular one"). Our entire bar is Suite (pytest, coverage, mutmut —
all measured against tests this pipeline wrote) plus ruff/mypy. The code-reviewer's Security
dimension is a *model's opinion*, not a check. Addy's verification checklist includes
"at least one constraint is external."

**Recommendation.** One external check in the Gate 7 bar — `pip-audit` or `bandit` is the
cheapest credible option for a Python-only workflow, and both are already in the ecosystem
`toolchain/requirements-dev.txt` targets.

### A8. The feature is the unit of work — there is no decomposition step

Every one of the five has one: superpowers `writing-plans` (task right-sizing: "the smallest
unit that carries its own test cycle and is worth a fresh reviewer's gate"), addy
`planning-and-task-breakdown` plus the spec Phase 0 capability map, mattpocock `to-tickets`
(tracer-bullet vertical slices with blocking edges, and expand–contract for wide refactors),
OpenSpec `tasks.md`, GSD phases/plans/waves.

`sdlc-lite` runs one interview → one design → one test suite → one implement for the whole
feature. P57's smallest-viable anchor is a *scope* control, not a *decomposition* control.
Consequences:

- One large diff, reviewed once. Addy's sizing: ~100 lines good, ~300 acceptable, ~1000 "too
  large, split it." Reviewer calibration degrades exactly where we need it most.
- The implementer holds the whole feature in one context — the context-rot condition both GSD
  and superpowers engineer around.

### A9. Gate 3/5 is batch TDD — a named anti-pattern — and should be a *defended* trade-off

Gate 3 confirms the suite is red once; Gate 5 makes it green. Mattpocock names this exactly:
**horizontal slicing** — "writing all tests first, then all implementation. Bulk tests verify
*imagined* behaviour: you test the *shape* of things rather than user-facing behaviour… you
commit to test structure before understanding the implementation." Superpowers' TDD skill is
equally strict on one-test-at-a-time.

Our architecture *requires* the batch shape: the suite must be complete and independently
reviewed (Gate 4) before an implementer is allowed to exist. That is a real, principled
trade-off — we buy algorithm-blindness and pre-implementation test review, and we pay in
verticality. It is currently undocumented and therefore looks like an oversight.

Note that **A8 resolves A9**: slicing recovers verticality *at the slice level* (one slice =
one red-green cycle) without giving up either purchased property.

**Recommendation.** Write the trade-off up as an ADR now; treat per-slice gating as the v2
resolution, not a v1 patch.

---

## 4. Deep dive — the DESIGN gate and design review

_Added after the first pass, on the observation that if the design and its review are weak,
everything downstream is weak by construction._

### 4.0 The structural finding

The pipeline's core claim is that **every bias-sensitive gate has a fresh, independent,
higher-model critic**. Gates 3, 5 and 6 produce; Gates 4 and 7 review with a pinned
`claude-opus-4-8`. **Gate 2 is the one gate that breaks this, twice:**

- **No reviewer.** `SKILL.md` Gate 2 says only: *"(For a complex feature, optionally spawn a
  fresh design-review subagent first.)"* Optional, unnamed, no agent def, no model pin, no
  inbox, no outbox, no verdict, no loop. In practice it will never fire.
- **No pinned model.** DESIGN is a `[C]` gate, so it runs on the session's model. Gate 0 step 6
  only *warns* when the conductor is below Opus-tier. Effort is uniform `medium` (#35), and
  design is the highest-leverage reasoning task in the run.

So the artifact that determines everything downstream is authored by an unpinned model and
reviewed by the human alone, cold, across three documents — which is exactly what Gate 8 exists
to prevent ("guide the eye; do not dump a diff"). Gate 2 dumps three documents.

Two chain-of-custody consequences follow:

1. **Algorithm-blindness rests on an unchecked rule.** *"Nothing that reveals the algorithm may
   leak into `02-design-interface.md`"* is enforced by prose and nothing else. `guard.py` can
   deny *reading* `03` — it cannot detect that `03`'s content was paraphrased into `02`. If the
   interface design leaks, the test-writer is no longer blind and **we would never know**. The
   headline differentiator (§2.2) has no verification.
2. **The test plan is an unaudited oracle.** Gate 4 judges coverage "per the test plan" and
   Gate 7 enforces *the plan's* thresholds. The test-reviewer does also check against
   `01-requirements.md`, so it is partially independent — but the test inventory, the implied
   seams, and the mutation kill-rate all arrive from Gate 2 unexamined. A weak plan is ratified
   downstream as "covered."

### 4.1 Strengthening the design artifact

Ranked by leverage. All Markdown-only; none require a new gate.

**(a) Name the seams — and make them a primary design output.**
The test plan enumerates tests by *level* (unit/api/e2e) traced to ACs. It never names the
**seam** each test observes behaviour at, so the test-writer picks the seam implicitly.

This is a hole in algorithm-blindness itself: blindness is enforced against the design
*document*, not against the *seam*. If `02` exposes a low seam, the test-writer produces
internal-shaped tests without ever reading `03` — fully compliant, and coupled to the
implementation anyway.

Mattpocock's rule (`tdd/SKILL.md`): *"Test only at pre-agreed seams. Before writing any test,
write down the seams under test and confirm them with the user. No test is written at an
unconfirmed seam."* And (`to-spec`): *"Existing seams should be preferred to new ones. Use the
highest seam possible. The fewer seams across the codebase, the better — the ideal number is
one."*

→ Add a **Seams** section to `02-design-interface.md` (which seam, why that height, existing or
new) and a **seam column** to the `04-test-plan.md` inventory. Surface it at approval: it is a
decision the human should make, not inherit.

**(b) Give the interface a quality bar, not just a shape.**
`design-interface-template.md` asks for signature / purpose / I-O / error behaviour /
invariants / traceability — a form to fill in. Nothing in it would ever reject a bad interface.

Add the deep-module criteria from mattpocock's `codebase-design`, which are unusually checkable:
- **Depth** — a lot of behaviour behind a small interface. Can I reduce the methods? Simplify
  the params? Hide more inside?
- **The deletion test** — imagine deleting the module. If complexity vanishes it was a
  pass-through; if it reappears across N callers it was earning its keep.
- **"The interface is the test surface"** — callers and tests cross the same seam. If you would
  want to test *past* the interface, the module is the wrong shape. (Same insight as (a), from
  the design side.)
- **"One adapter means a hypothetical seam; two means a real one"** — kills speculative
  abstraction at design time instead of at Gate 7.

This interacts directly with the differentiator: a *shallow* interface produces a wide test
surface, which makes the algorithm-blind test-writer's job harder and its output more brittle.

**(c) Design it twice, in parallel, isolated.**
Gate 2 asks the conductor to "present the approach **and alternatives considered**." One model
that has already committed to a design, listing alternatives afterwards, produces post-hoc
rationalisation rather than exploration.

Mattpocock ships `codebase-design/DESIGN-IT-TWICE.md` for exactly this: parallel sub-agents
design the interface several radically different ways, then compare on **depth, locality, and
seam placement**. Superpowers' brainstorming requires 2–3 approaches with trade-offs *before*
a design is presented.

We already have the subagent machinery and the isolation hook. Two or three parallel `designer`
agents over the same `01-requirements.md`, compared by the conductor against a fixed rubric, is
a natural fit — and the comparison is a far better artifact to hand the human than one design
plus a narrated list of roads not taken.

**(d) A "Review Focus" section — what the requirements did *not* say.**
The cheapest high-value mechanism found in any of the five, from superpowers `writing-plans`:

> The five input classes or failure modes the spec implies but no task's tests exercise that
> are most likely to bite a person using this software — one line each... The spec is a vision
> document: its silence on an input is not permission for that input to break the program.
> Write the list here, once, with the spec in front of you. **Then, for each line, add the test
> that pins it.**

This turns "spec silence is not permission" from a *reviewer* posture (A5) into a *design
deliverable* — much earlier and much cheaper. `quality-standards.md` already contains exactly
one hardcoded instance of this reasoning (the transport-fault rule, with its warning not to
conflate "no configurable timeout" — a scope decision — with "no need to test timeout
behaviour" — a coverage gap). Generalise it.

**(e) An explicit assumptions block.**
Addy's spec skill: *"Surface assumptions immediately. Before writing any spec content, list
what you're assuming... → Correct me now or I'll proceed with these."* The requirements
template has §6 assumptions; both design templates have none. Design assumptions — about
existing code, conventions, library semantics — are the dangerous ones, because they are
invisible in the output.

**(f) Read the repo first.**
Gate 2 never instructs the conductor to explore the existing codebase. Superpowers: *"Explore
the current structure before proposing changes. Follow existing patterns."* Mattpocock: respect
ADRs in the area you are touching and use the project's vocabulary. In a stranger's repo this
is the difference between a design that fits and one Gate 7 later flags as inconsistent.

**(g) A Gate 2 self-review checklist.**
Both superpowers planning skills run one inline, with no dispatch: placeholder scan, internal
consistency, scope check, and an **ambiguity check** — *"Could any requirement be interpreted
two different ways? If so, pick one and make it explicit."* Add mechanical **bidirectional
traceability**: the interface template traces surface→AC, but nothing checks that every AC has
a surface.

### 4.2 Making design review a real gate

**Recommendation: Gate 2.5 DESIGN-REVIEW `[I]` `design-reviewer`, pinned `claude-opus-4-8`,
with the same contract shape as Gates 4 and 7.** Inbox `01`+`02`+`03`+`04` plus repo read
access; outbox a numbered findings file with a verdict; bounded loop back to Gate 2; the human
sees findings *before* approving.

Why a subagent rather than a better human prompt:

- The conductor authored it, so it cannot review it — the identical anchoring argument that
  justifies Gates 4 and 7.
- It is the only way to pin a **model and effort** onto the design step, since `[C]` gates run
  on the session's model.
- It gives the human findings to focus on instead of three cold documents — consistent with
  P47 and the Gate 8 discipline.

**What it judges:**

1. **Leakage (load-bearing).** Does `02` reveal the algorithm? Could a reader of `02` alone
   infer the approach in `03`? The only possible verification of the central differentiator,
   and a semantic check no hook can perform.
2. **Testability through the interface.** Can every AC be observed through this surface without
   reaching past it? Is the seam right, and the highest available?
3. **Depth.** Deletion test; shallow pass-throughs; speculative surface with no AC behind it
   (Fowler's Speculative Generality; superpowers' "Extra" scope-creep category).
4. **Bidirectional AC coverage.** Every AC has a surface; every surface traces to an AC.
5. **Test-plan adequacy** — the audit that currently never happens. Would the inventory kill
   plausible bugs? Does every boundary in the inventory have a test? Is the kill-rate
   justification honest, or an unargued deviation from the 80% anchor (P46)?
6. **Coherence across `02`/`03`/`04`** — does the internal design implement the stated
   interface, and does the plan test *that* interface?
7. **Declined to judge** — list every concern set aside as out of scope, one line each, so
   nothing is dropped silently (A5). The conductor rules on each.

**How it is framed matters as much as the checklist.** Addy's `doubt-driven-development` is the
sharpest guidance in the field on adversarial review, and two rules apply directly:

> Adversarial review. Find what is wrong with this artifact. **Assume the author is
> overconfident.** ... Do NOT validate. Do NOT summarize. Find issues, or state explicitly that
> you cannot find any after thorough examination.

and, critically:

> **Pass ARTIFACT + CONTRACT only. Do NOT pass the CLAIM.** Handing the reviewer your
> conclusion biases it toward agreement.

Applied here: the reviewer receives `01-requirements.md` (the contract) and the three drafts
(the artifact) — and **not** the conductor's narration of why the design is good. That
narration is precisely what Gate 2 currently leads with. Add superpowers' corollary: a stated
rationale inside the design ("kept it simple deliberately", "YAGNI") is the author grading
their own work, and never downgrades a finding.

Addy also names the failure mode to watch: **doubt theatre** — across two or more rounds where
the reviewer surfaced substantive findings, zero were classified actionable. That is a
measurable signal `/analyze-run` could eventually report (C2).

### 4.3 The bolder option — make DESIGN itself an `[I]` gate

Dispatch design *authoring* to a pinned `designer` agent working from `01-requirements.md`
alone, with the conductor as presenter and the human as approver.

**For:** closes the unpinned-model hole completely; the only way to raise `effort` on the
highest-leverage reasoning step; enables (c) naturally; and forces `01-requirements.md` to
genuinely be self-sufficient — which its own template already claims it is ("This file — not
the conversation — is the inbox for downstream gates").

**Against:** the conductor holds rich Gate 1 interview context that never reaches the file.
That is either a bug (the file should carry it) or a feature (the human is in the loop anyway).

**Assessment:** a v1.1/v2 decision, not a pre-GA one. The requirements-self-sufficiency forcing
function is genuinely attractive, but it is a structural change that needs a dry run to prove
the file survives the handoff.

### 4.4 Sequencing note

Do 4.1 (a), (b), (d), (g) **before** adding the Gate 2.5 reviewer. A reviewer with no rubric
produces prose; those four give it something concrete to review against.

---

## 5. Tier B — the adjacent commands that don't exist

We ship two commands: `/implement-feature` and `/analyze-run`. The field:

| Lifecycle need | superpowers | addy | mattpocock | OpenSpec | GSD | **sdlc-lite** |
|---|---|---|---|---|---|---|
| Brownfield orientation | — | context-engineering | wayfinder | onboard / explore | map-codebase, explore | **none** |
| Idea → durable spec | brainstorming → spec file | `/spec` | `/to-spec` | propose → `specs/` SSOT | spec-phase | per-run, gitignored |
| Decompose into units | writing-plans | `/plan` | `/to-tickets` | `tasks.md` | roadmap/phases | **none** |
| Implement | subagent-driven-dev | `/build` | `/implement` | `/opsx:apply` | execute-phase | **✅ the product** |
| Fix a bug | systematic-debugging | debugging-and-error-recovery | diagnosing-bugs | — | `/gsd:debug` | **none** |
| Review an existing diff/PR | requesting-code-review | `/review` | `/code-review` | `/opsx:verify` | `/gsd:code-review` | Gate 7 only |
| Refactor / simplify | — | `/code-simplify` | improve-codebase-architecture | — | — | **none** |
| Finish the branch | finishing-a-development-branch | `/ship` | (commit only) | archive | `/gsd:ship`, pr-branch | **none** |
| Process forensics | diagnosing-superpowers | evals | `/retro` | — | `/gsd:forensics` | `/analyze-run` (partial) |

The three that matter, in order:

### B1. `/fix-bug` — the obvious missing sibling

A bug fix has a different gate sequence: reproduce → write the failing test that reproduces it
→ root-cause → fix → regression-guard. Running `/implement-feature` on a bug is wrong: its Gate
1 interview and Gate 2 interface/internal split don't fit a defect in existing code. Everyone
has this as a separate first-class workflow — and *we already believe this*, because
`fix-shell-bug` exists for shell scripts. Most of the existing agents transfer; the gate list
shrinks. Superpowers' `verification-before-completion` has the red-green-revert-red protocol
worth stealing verbatim: "Write → Run (pass) → Revert fix → Run (MUST FAIL) → Restore → Run
(pass)" — proof the regression test actually guards.

### B2. Nothing happens after COMMIT

Gate 10 commits on a feature branch; Gate 11 prints a report; the human is left holding a branch
with no push, no PR, no merge, no cleanup. SKILL.md acknowledges this in a *parenthetical*:
"*(In a repo with branch/PR conventions: commit on the feature branch, push… and open a PR)*".

Superpowers makes this a whole skill with a three-option menu, base-branch confirmation, a test
run **on the merged result**, worktree-cleanup provenance rules, and a rationalization table
entirely devoted to not making the integration decision for the human ("Integration is your
human partner's decision. Present the menu and wait."). Our "never commit before approval"
discipline stops one step short of where the risk actually is.

### B3. The spec is per-run and gitignored — worth an explicit revisit

`01-requirements.md` and `02-design-interface.md` live in `.implement-feature/<run>/`, which is
gitignored and discarded conceptually after the run. OpenSpec's entire thesis is the opposite:
specs are the repo's durable source of truth, each change is a delta (ADDED/MODIFIED/REMOVED)
that merges back on archive, and the accumulated spec is what makes the *next* change cheap.
Consequence for us: feature #2 cannot see feature #1's contract, the human can't diff a spec
across features, and nothing compounds.

This follows from ADR-4 (separate product from process by lifecycle), which is right for
run-logs and findings. But requirements and the interface design are arguably *product* — they
are the contract. Worth deciding deliberately rather than inheriting it from the P48 rule.

---

## 6. Tier C — you cannot currently tell whether a change to the workflow helped

### C1. No eval harness for the skill itself

Addy runs three tiers: **structural** (frontmatter/sections, CI, free), **trigger & routing**
(TF-IDF over descriptions — does each skill's description carry the words users actually say,
and do two descriptions collide? CI, free), and **behavioral** (each eval runs in a throwaway
git repo through headless `claude -p --output-format stream-json`, graded against
`expectations[]`). They also keep an **append-only ledger of rejected changes** with their
before/after eval scores, so contributors can see what was already tried and failed. Their
discipline skills include deliberate **pressure cases** for time pressure, sunk cost and
authority pressure.

Superpowers frames the same thing as TDD applied to process docs: run the scenario WITHOUT the
skill and watch the agent fail (RED), write the skill against the *observed* failures (GREEN),
then close the new loopholes (REFACTOR). They ship pressure fixtures inside the skill folders.

Our methodology is the manual green end-to-end dry run in the dev container. That is a good
*acceptance* test, but it is one sample, it is manual, and it cannot tell you whether a wording
change to `SKILL.md` made things better or worse. The `design/*-findings.md` files in this repo
are precisely the artifacts an eval suite would produce automatically.

**This is the compounding gap: every other item in this document gets cheaper to close once a
change can be measured.**

### C2. `/analyze-run` measures process compliance, not output quality

It reports isolation verdicts, model pins, tokens, tool calls. It does not report: findings per
gate, loop rounds burned, whether the mutation threshold was actually met, coverage delta, which
gates deviated. GSD's forensics and obra's `diagnosing-superpowers` both mine the transcript for
*quality* signals across named dimensions (plan-adherence, repeated-work, quality-evidence,
stumbles, cost-and-time), with the rule "every finding cites `path:line`. No citation, no
finding." Our run-log plus the numbered findings files already hold most of this data.

### C3. No rationalization tables

All three skill libraries put an anti-rationalization table in every discipline skill; addy
lists it as one of four key design choices. Superpowers explains the provenance: you *generate*
the rows from observed baseline failures.

`SKILL.md` is prescriptive prose plus a Rules list, with no counter-arguments to the specific
excuses a model reaches for. Yet we have *already observed* several and buried them as
parenthetical principle IDs: P57 (the interview maximised instead of anchoring), P46 (an agent
handed a metric with no anchor drifts), P45 (the reviewer built a reference implementation),
P44 (a Bash-holding critic can't be made read-only by tool removal). Those are rationalization
table rows, currently written as design rationale.

---

## 7. Tier D — small, high-ROI specifics

- **No model escalation on a stuck loop.** Every bounded loop re-spawns the *same* pinned model
  with the same findings. Superpowers escalates at rounds 4–5 to a fresh implementer one tier
  up, with the framing "A prior implementer attempted this task N times; you own it now" —
  because "a loop that survives three resumes usually means the implementer cannot see its own
  problem." GSD has a whole `dynamic_routing` ladder with `max_escalations`. Cheap fix:
  escalate one tier on the final bounded round.
- **"Turn count beats token price"** (superpowers) — an argument against uniform Sonnet
  producers on multi-step work, since cheap models routinely take 2–3× the turns. We have the
  token data in the analyzer already and could actually test this claim.
- **Hand the reviewer a diff file.** Superpowers builds a review package (commit list + stat +
  `git diff -U10`) to a file and passes the *path*, so the diff never enters the controller's
  context and the reviewer reads it in one call. We have an artifact dir already; this is a
  small change that also makes the reviewer's view deterministic.
- **Subagents must not spawn subagents.** Superpowers spends four paragraphs on this in three
  templates because they observed the cost: "every reviewer a worker spawned duplicated the
  task review the controller dispatched anyway — a full extra review seat per task." Our agent
  defs don't forbid it and the guard doesn't block the Agent/Task tool.
- **No progressive rigor.** Twelve gates run for every feature, however small. Superpowers
  classifies spike/bounded/architectural up front ("when in doubt take the heavier path; the
  ratchet is one-way"); OpenSpec has lite vs full specs; addy's spec skill names when *not* to
  use it. Gate 0 assesses triviality for the branch decision only. An escape hatch — human
  confirmed — would widen adoption considerably.
- **Grilling is inlined, not a primitive.** Mattpocock's `grilling` is a reusable
  model-invoked skill that five user-invoked skills call. Ours is Gate 1 prose. This becomes
  load-bearing the moment `/fix-bug` exists and needs the same interview discipline.

---

## 8. Recommended sequence

Deliberately mapped against the fact that `1.0.0` already has four committed issues.

**Before GA — Markdown-only, no architecture change, directly raises output quality.**
Items 1–4 are the design-side fixes from §4.1 and come first: they are upstream of everything
else, and they give the Gate 2.5 reviewer (item 10) a rubric to review against.

1. Seams in `02-design-interface.md` + a seam column in `04-test-plan.md` (§4.1a).
2. Deep-module criteria + the deletion test in the interface template (§4.1b).
3. A "Review Focus" section in the test plan (§4.1d).
4. Gate 2 self-review checklist, incl. bidirectional AC traceability (§4.1g).
5. `references/test-quality.md` (A1) — into the test-writer's and test-reviewer's inboxes.
6. Scoped re-review mode in `code-reviewer.md` (A2) — the convergence fix.
7. Severity + adjudication contract for findings (A3).
8. Three reviewer clauses: don't trust the report, spec silence isn't permission, declined-to-judge (A5).
9. "No nested subagents" line in all five agent defs (§7).

**Right after GA — mechanism, small and bounded:**

10. **Gate 2.5 DESIGN-REVIEW** with a pinned `design-reviewer` (§4.2) — the structural fix, and
    the only verification the algorithm-blindness guarantee has ever had.
11. Resumable run-log (A4) — the compaction fix.
12. Diff-scoped floor/stub check (A6) + one external check in the Gate 7 bar (A7).
13. Model escalation on the last bounded round (§7).
14. ADR documenting the batch-TDD trade-off (A9).

**v1.1 — new surface:**

15. `/fix-bug` (B1) — the highest-value missing command, and the cheapest new one.
16. A finish-the-branch gate or command (B2).
17. Extend `/analyze-run` with output-quality dimensions, incl. doubt-theatre detection (C2, §4.2).

**v2 — structural, decide deliberately:**

18. An eval harness (C1). Argument for doing it *earlier*: everything above becomes measurable.
19. Parallel design-it-twice (§4.1c) and/or DESIGN as a pinned `[I]` gate (§4.3).
20. Slicing / decomposition (A8), which also resolves A9.
21. Durable specs in git vs the per-run artifact dir (B3).

---

## Sources

- [obra/superpowers](https://github.com/obra/superpowers)
- [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) · [blog post](https://addyosmani.com/blog/agent-skills/)
- [mattpocock/skills](https://github.com/mattpocock/skills) · [aihero.dev](https://www.aihero.dev/)
- [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec)
- [gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done) (now [open-gsd/gsd-core](https://github.com/open-gsd/gsd-core))
- [spec-driven-development topic](https://github.com/topics/spec-driven-development) · [Augment Code: best SDD tools](https://www.augmentcode.com/tools/best-spec-driven-development-tools) · [danielscholl/claude-sdlc](https://github.com/danielscholl/claude-sdlc) · [bashebr/ai-native-sdlc](https://github.com/bashebr/ai-native-sdlc)
