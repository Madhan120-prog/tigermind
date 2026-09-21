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

- **RESOLVED 2026-08-24 by a Phase 2 spike — the cause is a firewall, not JS rendering.** Phase 0 guessed JS execution; that was wrong. `content.php` returns **HTTP 202 with a zero-byte body** to every client tested, and with a `PHPSESSID` session cookie it returns 2,011 bytes containing an **AWS WAF JavaScript challenge** (`window.gokuProps`, `awswaf.com/.../challenge.js`). A browser `User-Agent` makes no difference. The catalog root (`catalog.memphis.edu/`) *does* serve normally (~98 KB) and is not challenged, but the content pages are. There is no `sitemap.xml` (404) and no bulk PDF export link on the homepage — only a print-friendly view of the same challenged content.
- **`robots.txt` allows `/content.php` but sets `crawl-delay: 120`** — two minutes between requests. Even if the WAF were passable, a full course catalog is hundreds of pages, i.e. days of polite crawling.
- **The Banner alternative is not publicly reachable.** `ssb.bannerprod.memphis.edu` resolves (141.225.119.65) but refuses connections on 80, 443 and 8443 while a control host connects fine — campus-network-only or decommissioned. It is not a stale mirror to choose between; it is simply unavailable.
- **Conclusion: deferred, not scheduled.** See `PLAN.md` 17.12. Getting past the WAF means driving a headless browser to defeat a bot challenge, which this project declines.
- **Two parallel systems**: the Modern Campus/Acalog catalog and a legacy Banner self-service catalog both appear to carry course detail pages. Phase 1 needs to determine which is current/authoritative and avoid ingesting stale duplicate data from the other.
- Individual course URLs use opaque numeric IDs (`catoid`, `coid`, `navoid`), not human-readable slugs — course-code-to-URL mapping has to come from the filtered listing pages, not be guessed directly.
- Conceptual overlap with Majors: per `PLAN.md` §3, keep "what majors/programs exist" here in Course Catalog's `programs` collection; reserve the Majors agent for the stateful declare-vs-apply flow only.

## Proposed retrieval strategy

- [ ] Semantic RAG
- [ ] Structured lookup
- [x] Hybrid

Justification: Matches `PLAN.md` §6. Course-code queries ("what's COMP 1000") are structured/exact-match; broader questions ("how do I withdraw," "what does this program cover") are semantic. The confirmed `SUBJ #### - Title` format supports clean structured parsing once ingestion actually reaches the data (see complication above).
