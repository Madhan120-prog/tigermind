# Domain Research: course-catalog

> Phase 0 deliverable per PLAN.md Section 13. Fill in before writing any
> ingestion code for this domain.

## Source

- URL(s):
  - `catalog.memphis.edu/content.php?catoid=34&navoid=2098` — 2025-2026 Undergraduate Catalog homepage
  - `catalog.memphis.edu/content.php?catoid=26&navoid=1462` — course descriptions, filterable by subject (e.g. `filter[27]=COMP`)
  - `catalog.memphis.edu/preview_course_nopop.php?catoid=X&coid=Y` — individual course detail pages
  - `catalog.memphis.edu/content.php?catoid=26&navoid=1456` — full undergraduate program list
  - Legacy/parallel system: `ssb.bannerprod.memphis.edu/prod/bwckctlg.p_disp_course_detail` — a separate Banner self-service catalog also indexed by search engines; need to confirm in Phase 1 whether this is authoritative or a stale mirror
- Format: HTML — a "Modern Campus Catalog" (Acalog) platform with a filter-driven search UI. **A plain fetch of both the catalog homepage and the filtered course-list page returned empty/unrenderable content in this research pass.** Individual course pages and filtered-search URLs were discoverable via search-engine indexing, confirming the content exists and is crawlable, even though a direct fetch in this session didn't render it.
- Approximate size: large — full undergraduate + graduate catalog across all departments. Confirmed course format: `SUBJ #### - Title` (e.g. "COMP 1000 - CS for All: Introduction to Computer Science").
- Update frequency: annual (new catalog year).

## Real questions this domain should answer

1. What are the prerequisites for [course code]?
2. What courses does the [department] offer at the [level]?
3. What programs/majors exist under [college]? *(overlaps with Majors — Course Catalog owns "what programs exist," Majors owns the stateful advising flow, per `PLAN.md` §3)*
4. What's the course description for [course code]?
5. Is [course] offered in [semester]?

## Data complications

- **Direct fetch didn't render content in this research pass** — the one domain where Phase 0 couldn't fully verify data by simple HTTP fetch. catalog.memphis.edu appears to require JS execution or specific query/session handling a basic fetch doesn't satisfy. **Needs a dedicated ingestion spike early in Phase 1/2**: test `requests`/`httpx` + BeautifulSoup directly against the `content.php?filter[...]` URLs, and check whether Acalog exposes a bulk PDF export or sitemap (many Acalog catalogs do) before assuming the standard pipeline works unmodified.
- **Two parallel systems**: the Modern Campus/Acalog catalog and a legacy Banner self-service catalog both appear to carry course detail pages. Phase 1 needs to determine which is current/authoritative and avoid ingesting stale duplicate data from the other.
- Individual course URLs use opaque numeric IDs (`catoid`, `coid`, `navoid`), not human-readable slugs — course-code-to-URL mapping has to come from the filtered listing pages, not be guessed directly.
- Conceptual overlap with Majors: per `PLAN.md` §3, keep "what majors/programs exist" here in Course Catalog's `programs` collection; reserve the Majors agent for the stateful declare-vs-apply flow only.

## Proposed retrieval strategy

- [ ] Semantic RAG
- [ ] Structured lookup
- [x] Hybrid

Justification: Matches `PLAN.md` §6. Course-code queries ("what's COMP 1000") are structured/exact-match; broader questions ("how do I withdraw," "what does this program cover") are semantic. The confirmed `SUBJ #### - Title` format supports clean structured parsing once ingestion actually reaches the data (see complication above).
