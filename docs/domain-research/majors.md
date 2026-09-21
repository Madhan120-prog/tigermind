# Domain Research: majors

> Phase 0 deliverable per PLAN.md Section 13. Fill in before writing any
> ingestion code for this domain.

## Tier split (read this first)

Majors is not one domain — it's two, per `PLAN.md` Section 3:

- **Tier 1 (`programs` collection)**: static "what majors exist / what
  does X major cover / how do I change my major" questions. Answered by
  the existing generic, config-driven agent — a `domains.yaml` entry, no
  new code.
- **Tier 2 (stateful Majors advising)**: "help me figure out which major
  to pick" / "can I get into a competitive major" — needs a checkpointer,
  multi-turn intake, and an `interrupt()`-gated recommendation. This is
  the flagship feature Phase 3 builds.

Everything below is organized around that split.

## Source

- URL(s):
  - `memphis.edu/academics/ugmajors.php` — Tier 1 breadth. Confirmed
    reachable (no WAF/SSO gate, unlike Course Catalog). A single
    alphabetical table of essentially every UofM undergraduate
    major/minor/concentration.
  - `memphis.edu/fcbeundergrad/programs/` (+ its per-major pages) — Tier 1
    depth for the Fogelman College of Business and Economics, the same
    college Faculty already covers. 8 named majors, each with its own
    description page (Accounting, Business Economics, Finance, HR
    Management, Management, MIS, Marketing, Supply Chain Management).
  - Loewenberg College of Nursing's general BSN program-description page —
    Tier 1 depth for one non-FCBE example. **Not** the admission-criteria
    page below — that's Tier 2 config data, not retrieval content.
  - `memphis.edu/advising/students/changingmajor.php` — the general
    declare-path process. Ingested once, reused by both tiers: Tier 1
    answers "how do I change my major" directly; Tier 2's `recommend` node
    cites this same chunk for the declare path.
  - `memphis.edu/nursing/program-admit/bsn/updatedbsn.php` — Tier 2 only.
    The real, current BSN admission-criteria numbers that drive the
    `interrupt()` eligibility logic. Confirmed current and authoritative:
    a second page, `memphis.edu/nursing/program-admit/howtoapply.php`,
    404s and no longer exists, and an earlier general web search had
    surfaced different (stale/cached) numbers from it — this page was
    fetched directly just now and is the one to trust.
  - **Explicitly not usable, for either tier**: `umdegree.memphis.edu`,
    the degree-audit tool named in the project's original source-planning
    (`PLAN.md` Section 12). Fetching it 302-redirects straight to
    `sso.memphis.edu` — it's SSO-gated, the same failure class as Course
    Catalog's WAF block (17.12), just a different gate. It is not
    fetchable content at all. `PLAN.md` Section 12 needs correcting to
    remove it, not silently drop it.
- Format: HTML throughout (no PDFs needed for this domain, unlike Fees).
- Approximate size: `ugmajors.php` is one page; FCBE adds ~9 pages;
  Nursing adds 2 (general description + admission criteria);
  `changingmajor.php` is 1. Small corpus overall, deliberately scoped —
  see "Data complications" below for why it isn't broader.
- Update frequency: slow for program descriptions and the general declare
  process; the Nursing admission numbers and deadlines are exactly the
  kind of thing that changes per cycle (the `howtoapply.php` vs.
  `updatedbsn.php` discrepancy is itself evidence of this) — treat
  `competitive_majors.yaml`'s numbers as needing a refresh check each
  admission cycle, not a one-time capture.

## Real questions this domain should answer

**Tier 1 (`programs`):**
1. What majors does the Fogelman College of Business and Economics offer?
2. Does UofM have a Nursing major / what department is it in?
3. What does the BSN (Nursing) program cover?
4. How do I change my major?
5. Is it competitive to get into the Computer Science major? (negative
   case — most majors aren't gated at all; this should not be confused
   with Nursing's real competitive process)

**Tier 2 (stateful advising):**
1. "I'm not sure what major to pick, I like biology and helping people" —
   open-ended, needs intake before any recommendation is possible.
2. "I want to apply for Nursing" (no GPA given yet) — should prompt for
   more information, not guess.
3. "I want to switch to Nursing, my GPA is 3.4 and I've finished all the
   prereqs with Bs or better" — clearly eligible, should not pause for
   confirmation.
4. "My cumulative GPA is 2.85 and I'm still finishing one prereq" —
   borderline by design (inside the margin band around the real 3.0
   cutoff), should pause via `interrupt()` before finalizing.
5. "I want to switch to Communication Sciences and Disorders" — a major
   with no verified competitive-admission data in this project (see
   Data complications) — should get the generic declare-path answer, not
   an invented eligibility judgment.

## Data complications

- **Nursing's own admission pages disagree with each other over time** —
  confirmed directly: `howtoapply.php` (no longer live) gave different
  GPA/deadline figures than the current `updatedbsn.php`. This is the
  same "institutional pages go stale, verify against the current source"
  lesson found earlier in Fees and Student Employment, now confirmed a
  third time. `competitive_majors.yaml`'s numbers should carry the source
  URL and be treated as needing a periodic recheck, not captured once and
  trusted forever.
- **Only one competitive major (Nursing) is verified with real numbers.**
  Other UofM programs likely have their own competitive/transfer-GPA
  gates (Engineering and some Communication Sciences programs are common
  examples elsewhere), but none were researched here — modeling them
  without equally-verified numbers would repeat the exact fabrication
  risk this project already caught and fixed (see PLAN.md 17.13, 17.14).
  Deliberately scoped to one real, fully-verified ruleset, matching how
  Fees scoped to one tuition track and Faculty to one college. Any major
  not in `competitive_majors.yaml` gets the generic declare-path answer —
  correct for the overwhelming majority of majors, and honest about not
  knowing the handful of exceptions this project didn't research.
- **`umdegree.memphis.edu` is unusable** (SSO-gated) for anything — this
  removes what would otherwise be the single best per-student "what would
  changing my major actually require" tool. The stateful flow has to work
  from general program pages plus what the student reports about their
  own GPA/courses, not a live degree-audit lookup.
- Admission is **threshold-based, not ranked/competitive** for Nursing
  specifically (meeting the stated criteria guarantees consideration,
  confirmed directly on `updatedbsn.php`) — this matters for the
  `interrupt()` design: "borderline" can be a clean numeric distance from
  a fixed cutoff, not an approximation of a competitive ranking against
  other applicants.

## Proposed retrieval strategy

**Tier 1 (`programs`):**
- [x] Semantic RAG
- [ ] Structured lookup
- [ ] Hybrid

Justification: matches `PLAN.md` §6's existing classification of Majors
process text as semantic. Program descriptions and the declare-path
process are prose; there's no course-code-like structured key here the
way Faculty (names) or Fees (credit-hour rows) have.

**Tier 2 (stateful advising):** not a retrieval-mode question — this is a
`StateGraph` with an intake node and an `interrupt()`-gated recommend
node, not a `domains.yaml` entry. See the Phase 3 implementation plan for
the full design (state schema, node structure, eligibility-band logic).
