# TigerMind Knowledge Base — Phase by Phase

A study reference for this project, not a build log (that's `git log` and
the PR history) and not the architecture spec (that's `PLAN.md`). This
file exists to answer one question per phase: *if someone asked me about
this in an interview, what would I actually say?* Updated at the end of
every phase, per the working agreement.

Each phase covers: what got built, the technical decisions and why,
the real bugs found and fixed (the actual engineering stories — this is
the part worth remembering, not the happy path), what I learned, and a
short interview pitch.

---

## Phase 0 — Domain Reconnaissance

**What I built:** Research, not code. For all 8 originally-planned Tier-1
domains (Housing, Fees, Faculty, Flyers, Events, Exams/Deadlines, Student
Employment, Course Catalog), I found the real source pages, wrote down
real questions a student would ask, and figured out whether each one
needs simple keyword lookup, open-ended semantic search, or a mix. Seeded
`eval/eval_set.csv` with 40 real question/answer pairs (5 per domain)
*before* writing any ingestion code.

**Key decisions & why:** Research before code, on purpose — the checkpoint
rule (`PLAN.md` §13) exists specifically because it's cheap to discover a
source is unreachable in Phase 0 and expensive to discover it mid-build.

**What I found (the actual value of this phase):**
- Fees' dollar amounts live in per-year PDF schedules, not HTML — this is
  why "hybrid retrieval" and PDF parsing (`pdfplumber`) exist in the stack
  at all.
- Faculty has no central directory — each department publishes its own
  page in its own way. This is why Faculty later needed sitemap-based
  auto-discovery instead of a hardcoded URL list.
- Events and Course Catalog are both JS-rendered — a plain HTTP fetch
  returns nothing useful. Course Catalog turned out to be worse: it's
  behind an AWS WAF bot-challenge, not just JS-rendered (confirmed in
  Phase 2, `PLAN.md` 17.12) — still unresolved, permanently dropped from
  scope rather than fought.

**What I learned:** A source that "has the data" isn't the same as a
source you can actually fetch. Two domains (Events, Course Catalog) that
looked identical to the other six on paper turned out to need
fundamentally different ingestion approaches (or to be blocked entirely) —
you only find that out by actually trying to fetch the page, not by
reading its content in a browser.

**Interview pitch:** *"Before writing any retrieval code, I did a research
pass across all the planned data sources and found that two of them
couldn't be fetched with a plain HTTP request at all — one was
JS-rendered, one was behind a bot-detection wall. Catching that in a
research phase instead of mid-build is why the project's scope changed
early and cleanly instead of stalling out later."*

---

## Phase 1 — The Vertical Slice (Housing)

**What I built:** The full pipeline, end to end, for exactly one domain:
fetch → chunk → embed → retrieve → guardrails → answer. Config-driven from
the start (`backend/app/config/domains.yaml`) so every domain after this
one is a config entry, not new agent code.

**Key decisions & why:** Ingestion uses `httpx` + BeautifulSoup, not an
AI-summarizing fetch — a chunk has to be the source's actual text, not a
model's paraphrase of it, because the citation-grounded guardrail design
(cite the exact source URL for a claim) only works if what's stored is
what the source actually said.

**Bugs found & fixed (started at 2/5 on the eval set, ended 5/5):**
- **Off-by-one in header/value pairing.** `zip(headers[1:], values[1:])`
  sliced an already-sliced list, so every dollar figure in the corpus got
  labeled with the *wrong year* — and the assistant stated it confidently,
  citation attached. Only caught because the eval question specifically
  asked for one year's rate. This is the single best example in the whole
  project of "a program running without errors is not the same as a
  program being correct."
- **Prose tables bypassing the chunk-size limit.** Every `<table>` was
  treated as unsplittable, but some tables on this site are just layout,
  not data — a 1,900-character prose block sailed past the 800-character
  chunking target because it happened to sit inside `<table>` tags. Fixed
  by only treating a table as atomic if it actually produced real
  `header: value` pairs.
- **Table rows split across chunks.** A long rate table got cut in half
  by the chunker, separating a row from its own header — the row, not the
  whole table, needed to be the atomic unit, carrying its own header and
  any note rows with it.
- **Navigation text polluting embeddings.** A sidebar menu lived in a
  plain `<div class="tertiary-nav">` (no `<nav>` tag), and its link text
  was dragging chunk embeddings off-topic. Fixed by matching the
  class/id convention directly, not a generic "link density" heuristic —
  a link-density rule would have wrongly deleted the Flyers domain, which
  is legitimately a list of links.

**What I learned:** Almost all the real bugs in a RAG pipeline live in how
you split source documents into chunks, not in the retrieval or
generation code. A bad split hands the model information that *looks*
fine and reads fine but is quietly wrong — and the model has no way to
know that on its own. Also: test with real, specific questions early. A
"the demo works" smoke test would never have caught the year mislabeling;
a specific eval question caught it in minutes.

**Interview pitch:** *"My first real bug in this project was a table
parser that silently mislabeled every price with the wrong year, and the
assistant answered confidently anyway, citation and all. It taught me
that in a RAG system, most of the actual risk is in the chunking step —
not the model call — because a bad chunk still looks completely
plausible to both the model and a casual reader."*

---

## Phase 2 — Scaling the Generic Agent (Fees, Faculty, Student Employment)

**What I built:** Three more Tier-1 domains, one per retrieval mode, to
prove the config-driven agent actually generalizes: Student Employment
(semantic — zero new code beyond a config entry), Faculty (structured —
sitemap-based auto-discovery across 100 pages, no hardcoded URL list),
Fees (hybrid — first PDF ingestion in the project, deliberately scoped to
one tuition track). Course Catalog was dropped from scope here once the
WAF block was confirmed; Fees took over its teaching slot for hybrid
retrieval.

**Key decisions & why:** Faculty's sitemap-discovery approach means adding
a new department later is a config change (a URL pattern), not new code —
directly extending Phase 1's "config, not code" principle to *source
discovery* itself, not just retrieval behavior. Fees was deliberately
scoped to exactly one track (undergrad, TN resident, 2025-26) rather than
every tuition variant, to prove the hybrid mechanism cheaply first — the
same "smallest slice that proves the mechanism" pattern later reused for
Majors (one verified competitive major) and Housing (one domain before
scaling).

**Bugs found & fixed:**
- **Two bugs in the shared table-extraction logic**, both surfaced by real
  Fees data that Housing and Faculty happened not to contain: a PDF's
  title row getting mistaken for its header row (collapsing 18 rows into
  one blob), and one HTML table with *no* header row at all silently
  eating its first real record as a fake header. Both fixed generically —
  a real header's last cell is a label ("Total"), never a value ("$25") —
  so the fix applies to every domain's tables, not just Fees'.
  Markup-based signals (`<th>` vs `<td>`) didn't distinguish these cases
  on this site; the fix had to be content-based.
- **The structured-matcher's noise filter ate valid data.** A length-3
  floor meant to drop short noise words from a slug (like "van") was also
  dropping single-digit keys — exactly what a credit-hour count is, and
  the only thing distinguishing one fee-schedule row from the next.
- **A real safety finding, not a code bug:** the university's own pages
  disagree on how many hours an F-1 student can work during school
  breaks — one page says 40, another says 20. Getting this wrong risks a
  real visa-status violation for a real student. Built a config-driven
  deferral system: a domain declares its own sensitive topics and where to
  redirect students, and a guardrail (not just a prompt instruction)
  refuses to state a figure on that topic even if the model tries to
  volunteer one unprompted.

**What I learned:** A bug found in one domain's real data is often a bug
waiting in every domain — the two table bugs above were latent in shared
code from Phase 1, just never triggered because Housing's tables happened
not to expose them. Also: a safety rule that only lives in a prompt is
not a guarantee — the model *did* volunteer the risky figure even after
being told not to, which is exactly why the check has to also live in
code, checked after generation, not just instructed before it.

**Interview pitch:** *"I found a real safety issue where the university's
own web pages contradicted each other about a rule that affects a
student's visa status. I didn't just patch the prompt to say 'don't
guess' — I added a code-level guardrail that inspects the model's actual
output and blocks it from stating a number on that topic at all, because
I'd already seen the model ignore the prompt instruction once. That
distinction — a rule you can verify in code versus a rule you're just
hoping the model follows — is the core of what 'safe agentic AI' actually
means in practice, not just the vibe of it."*

---

## Phase 3 — The Majors Advising Agent (Tier 2, Stateful)

**What I built:** The project's first genuinely stateful agent: a student
can say they want to apply to Nursing, give their GPA several messages
later, list completed courses even later than that, and the system holds
onto all of it. This is also the first place `interrupt()` (a real pause
for human confirmation) and a LangGraph checkpointer (real persistence
across separate API calls) actually get used, not just described in the
plan. Also shipped `programs` (Tier 1) for general "what majors exist /
what does X cover" questions, deliberately separate from the personalized
advising flow.

**Key decisions & why:** Scoped to exactly one real, fully-verified
competitive major (Nursing) rather than guessing at rules for others —
same "smallest slice" pattern as Fees' one tuition track. Nursing's real
numbers came from directly fetching the current admission page, not
assumption — an earlier candidate page gave different numbers and now
404s, which would have been a real fabrication risk if I'd trusted it
without checking directly.

**The most important technical fact in the whole project, verified by
direct testing, not assumed:** when a paused LangGraph node resumes, its
**entire function body re-runs from the top** — not just the code after
the `interrupt()` call. I proved this with a throwaway graph and an
incrementing counter before writing the real recommendation logic. The
consequence: everything before the pause has to be pure, deterministic
computation (config lookups, arithmetic) with zero side effects and zero
LLM calls — because if it ran an LLM call, a resume could produce a
*different* draft than the one the student actually confirmed against,
silently defeating the entire point of asking for confirmation.

**Bugs found & fixed:**
- **Decline detection only matched the literal word "no."** A natural
  reply like *"no, let me improve my numbers first"* still starts with
  "no," so a naive exact-match would have worked — but the actual bug was
  the reverse risk (matching too narrowly and missing real declines
  worded differently), caught and fixed with a proper pattern match before
  it shipped.
- **The model hallucinated the Nursing college's actual name** ("Lonel C.
  Lowel School of Nursing," which doesn't exist) because the real name was
  never given to it as a fact — it was left to guess from context. Fixed
  by putting the real name in config and the prompt, not by telling the
  model to "be careful."
- **A GPA-proxy bug** (caught later, by Copilot's automated review): using
  one GPA field for both Nursing's cumulative-GPA and prerequisite-GPA
  thresholds let a strong overall GPA mask a genuinely failing
  prerequisite GPA. Fixed by tracking them as two independent numbers,
  each checked on its own terms — a single collapsed number is *not* a
  safe stand-in for two separate real-world requirements.

**What I learned:** A framework's documented behavior and its actual
runtime behavior can differ in ways that matter enormously — "resume from
where it paused" sounds intuitive and is *wrong* for LangGraph's actual
mechanic, and I would not have caught this by reading documentation
alone; I had to run a real test. Also: an automated code reviewer (GitHub
Copilot, in this case) catches real logic gaps a human misses when too
close to their own code, especially adjacent-case bugs like the GPA-proxy
issue.

**Interview pitch:** *"The trickiest thing I had to reason about this
project wasn't the AI part at all — it was a graph-execution detail. When
you pause a LangGraph node for human confirmation and then resume it, the
whole function reruns from the top, not just the part after the pause. I
verified that with a throwaway test before trusting it, and it directly
shaped my design: anything before that pause has to be a pure function
with no side effects, or a student could end up confirming one answer and
seeing a different one."*

---

## Phase 4 — Router, Synthesizer, Guardrails (One Unified Entry Point)

**What I built:** Replaced two separate, disconnected paths — a Tier-1
endpoint that required the *caller* to say which topic to use, and a
completely separate Majors conversation flow — with one real router. A
single AI classification step now reads a question (and the whole
conversation so far) and decides: is this a factual question (which
topic, or topics?), a personalized Majors conversation, or something
outside the data entirely? A question spanning two topics at once now
gets genuinely combined into one coherent answer instead of only
answering half of it. Guardrails (the safety/citation checks) now apply
uniformly everywhere, including to Majors' final answers, which never had
them before.

**Key decisions & why:** Chose the harder, bigger-scope option
deliberately: unify everything behind one real `/ask` endpoint (matching
the architecture diagram that had existed in the plan since day one)
rather than the smaller option of routing only among the factual topics
and leaving Majors on its own separate endpoint. This is a real example of
"the plan said something for months, and building it for real turned out
to cost more than the plan assumed" — worth noticing and saying out loud,
not quietly under-delivering against the original diagram.

**Bugs found & fixed (an unusually bug-dense phase, because it introduced
real concurrency for the first time):**
- **Router misclassification, caught before committing.** "I want to
  apply to Nursing" (no numbers given yet) was first read as a general
  factual question about Nursing instead of the start of a personalized
  advising conversation. Fixed by having the router treat *expressed
  intent* to apply/declare as personalized from the very first message,
  not waiting for the student to actually state a number.
- **A genuine LangGraph concurrency gotcha.** When a question needs more
  than one topic, the system runs those lookups in parallel (a "fan-out").
  A decision step attached directly to the node that runs in parallel gets
  evaluated once *per branch as it finishes*, not once after all branches
  are done — so with two topics active, the decision could fire on
  incomplete information. Fixed by adding an explicit "wait for everyone"
  step before the decision runs.
- **A real thread-safety bug**, also only possible once real parallelism
  existed: two lookups racing to set up the shared database connection for
  the first time crashed, because Python's built-in caching decorator
  releases its lock *while* the slow setup work runs — so two threads can
  both slip through and both try to create the connection. Fixed with an
  explicit lock.
- **A subtle safety gap in the "combine two answers" step.** After
  merging two topics' answers into one, the system was trusting the
  *pre-merge* safety-check results while returning the *post-merge* text —
  meaning a merge that accidentally rewrote or reintroduced something
  risky would still be labeled fully safe. Fixed by re-checking the merged
  text itself, with a safe deterministic fallback (show the two original,
  already-checked answers stacked, not blended) if the recheck fails.
- **Stale data leaking across separate conversation turns.** A LangGraph
  design detail: a value the system accumulates *during one request* was
  also being kept *between* separate requests on the same conversation
  thread, because nothing explicitly cleared it — so asking about housing,
  then later asking a totally separate question about fees, could still
  carry the housing answer forward and wrongly combine it with the new
  one. Caught by an automated code review, reproduced live, then fixed
  with a custom "clear on every new turn" rule.
- **Fixed a real bug the plan had already flagged weeks earlier but this
  phase's actual work-plan forgot to include:** a plain domestic question
  like "how many hours can I work" was sometimes losing its correct answer
  entirely because the model volunteered an unrelated, risky figure
  alongside it, tripping the same-topic safety check and discarding the
  whole (otherwise correct) answer. Fixed with exactly one retry: restate
  the violated rule concretely and try again once before actually
  discarding the answer.

**What I learned:** Concurrency bugs don't show up until you actually run
things concurrently — every one of the four fan-out-related bugs above
was latent in earlier, sequential-only code and only became reachable
once real parallel branches existed. Also: re-reading your own past
planning documents on a regular cadence surfaces real, already-identified
work you'd otherwise silently skip — the domestic-hours bug fix wasn't in
my plan for this phase at all; I only caught it by rereading an old
"known issues" note while doing routine documentation cleanup.

**Interview pitch:** *"Once I introduced real concurrency — running two
topic lookups in parallel and merging their answers — I hit four separate
bugs that were all invisible before, because nothing had ever actually run
at the same time as anything else: a race condition on a shared database
connection, a decision step firing on incomplete parallel data, and a
safety check that trusted pre-merge results for post-merge text. Finding
and fixing all four taught me that 'it worked in every test so far' means
a lot less once you add real parallelism — the bugs aren't there until
concurrency makes them reachable."*

---

## Concepts worth reviewing / going deeper on

Things this project touched but where there's more depth to learn beyond
what was needed here:

- **LangGraph's Pregel/superstep execution model** — why a conditional
  edge attached directly to a `Send`-targeted node behaves differently
  than one attached after a join node. Phase 4 hit this as a bug; worth
  understanding the underlying "superstep" model directly from LangGraph's
  own docs, not just the workaround.
- **Checkpointer backends beyond `MemorySaver`** — `MemorySaver` is
  in-process only and lost on restart, by design, for this project. A
  durable backend (Postgres, SQLite-backed) is the natural next thing to
  learn if this ever needed to survive real deployment.
- **Chroma / vector database internals** — the confidence gate here uses
  raw L2 distance with a threshold picked empirically (`PLAN.md` 17.9),
  never properly calibrated against labeled data. Understanding precision/
  recall tradeoffs for retrieval thresholds is a real gap.
- **Extended thinking / reasoning-mode models** — discovered during Phase
  4 that `claude-opus-5` can return thinking blocks by default. Worth
  understanding when and why to enable/disable extended thinking
  deliberately, rather than discovering its latency impact by accident
  (which is what happened here).
- **Prompt injection / adversarial robustness** — this project's
  guardrails defend against the *model* making mistakes (hallucinating
  figures, mishandling deferrals), not against an adversarial student
  deliberately trying to manipulate the router or agents. Worth studying
  as a distinct threat model before this kind of system ever handled real
  user input in production.

---

*Last updated: end of Phase 4 (2026-09-28). Add a new phase section each
time a phase's PR merges, per the working agreement.*
