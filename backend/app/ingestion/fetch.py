import re

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "TigerMind-Ingestion/0.1 (portfolio project; contact via github.com/Madhan120-prog/tigermind)"

_NAV_HINT = re.compile("nav", re.I)

# A real header labels a column ("Tuition", "Total"); it is never itself a
# value. A table with no header row at all -- every row, including the
# first, is a data record -- has no way to signal that in the markup here
# (both kinds of row are plain <td>, confirmed against two such tables), so
# the header row's own last cell is the only available tell: if it reads as
# a value rather than a label, row 0 is data, not a header.
_VALUE_LIKE = re.compile(r"^\$?[\d,]+(\.\d+)?$|^free$", re.I)


def _is_navigation(tag) -> bool:
    """Match the class/id naming convention for menus.

    Deliberately not a link-density rule: a container that is mostly links
    describes this site's menus, but it also describes the Flyers domain's
    announcements page, which is genuinely a list of links. Matching the
    naming convention is the narrower, safer signal.
    """
    return bool(
        _NAV_HINT.search(" ".join(tag.get("class", [])))
        or _NAV_HINT.search(tag.get("id") or "")
    )


def rows_to_data(rows: list[list[str]]) -> tuple[str, list[tuple[str, str]], bool]:
    """Render a table's rows into (context, [(record_key, data_row), ...], is_data_table).

    Shared by HTML and PDF extraction -- pdfplumber's extract_tables() and a
    BeautifulSoup <table>'s rows both reduce to a plain list of lists first,
    and everything past that point is the same problem: keep each row's
    values attached to their column headers, since a chunk that loses that
    pairing states a real number against the wrong header. record_key is the
    row's own label (e.g. a credit-hour count, or a person's slug) so an
    exact-match lookup can find this one row instead of a table full of
    similar rows.

    context is the header row's corner cell plus every row that produced no
    header:value pairs. Those rows aren't data -- they're notes qualifying
    the whole table (an eligibility restriction, or which term a fee
    schedule applies to) -- and a data row separated from them loses the
    qualifier that makes it true. Source pages carry no <caption> and no
    usable preceding heading, so these in-table notes are the only context
    available.

    is_data_table is False when no row produced pairs at all: without that
    pairing there is nothing to protect from the chunker, so the markup is
    page layout rather than data.

    A table with no header row renders each row positionally instead --
    "label -- value, value, ..." -- since there are no real column names to
    pair values against. This is a real fee table found on the Fees
    domain's overview page: every row is [category, description, dollar
    amount], with no header, and the general header:value logic silently
    ate its first row as a fake header and mislabeled every dollar amount
    against the row above it -- a table with a header row was assumed
    universal until this one wasn't.
    """
    if not rows:
        return "", [], False

    # A PDF cell wraps as a literal "\n" mid-word ("University\nService
    # Fee"); an HTML cell never does (get_text(strip=True) has no internal
    # newlines), so this is a no-op there and a real cleanup here.
    rows = [[" ".join((cell or "").split()) for cell in row] for row in rows]

    header_cells = rows[0]
    has_header_row = not (header_cells and _VALUE_LIKE.match(header_cells[-1]))

    if has_header_row:
        corner_note, headers = (
            (header_cells[0] or "", header_cells[1:]) if header_cells else ("", [])
        )
        data_source_rows = rows[1:]
    else:
        corner_note, headers = "", None
        data_source_rows = rows

    notes = [corner_note] if corner_note else []
    data_rows: list[tuple[str, str]] = []
    for values in data_source_rows:
        if not values or not values[0]:
            continue
        label = values[0]
        if headers is not None:
            # zip(headers, values[1:]) -- `headers` has already dropped the
            # corner cell, so slicing it again here would shift every value
            # one column left and discard the last one (zip stops at the
            # shorter list), which mislabeled every rate in the corpus by a
            # year.
            parts = [
                f"{header}: {value}"
                for header, value in zip(headers, values[1:])
                if header and value
            ]
        else:
            parts = [value for value in values[1:] if value]

        if parts:
            data_rows.append((label, f"{label} -- " + ", ".join(parts)))
        elif headers is not None:
            notes.append(label)

    return "\n".join(notes), data_rows, bool(data_rows)


def _table_to_rows(table) -> tuple[str, list[tuple[str, str]], bool]:
    rows = [
        [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
        for tr in table.find_all("tr")
    ]
    return rows_to_data(rows)


def fetch_page(url: str, timeout: float = 15.0) -> tuple[str, list[tuple[str, bool, str]]]:
    """Fetch a page and return (heading, [(text, is_atomic, record_key), ...]).

    The heading travels with every chunk from the page, because a chunk
    lifted out of the middle of a page loses what the page was about -- a
    faculty member's biography paragraph does not repeat their name, so
    "what is Dr. Amini's email" cannot reach it.

    A real data table becomes one atomic block per row, each carrying the
    table's notes and its own row label as record_key -- a page can be a
    single record (a faculty member) or a table of many (a fee schedule
    keyed by credit hours), and only the row itself knows which. The row --
    not the table -- is the unit that must stay intact: splitting mid-row
    detaches a value from the header it belongs to, while splitting between
    rows costs nothing and lets a row retrieve on its own terms instead of
    being averaged into one table-wide vector dominated by whichever column
    has the most text. Tables used purely for page layout have no
    header:value pairing to protect, so they come back as ordinary
    splittable prose (record_key ""), as does the surrounding page text.

    Deterministic HTTP + HTML parsing, not an AI-summarizing fetch tool --
    see PLAN.md Section 11 for why that distinction matters for ingestion.
    """
    response = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    # Captured before scoping to <main>, which drops <head>.
    document_title = soup.title.get_text(strip=True) if soup.title else ""
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    # These pages put a sidebar menu in a plain <div class="tertiary-nav">
    # rather than a <nav>, so the tag strip above misses it.
    for tag in soup.find_all(_is_navigation):
        if not getattr(tag, "decomposed", False):
            tag.decompose()

    # Site chrome is text too, and menu labels mixed into a chunk drag its
    # embedding away from what the chunk is actually about -- that is what
    # buried the mail-services fee behind six unrelated rate rows. Fall back
    # to the whole document when a page has no <main>: losing the
    # improvement on such a page is acceptable, losing its content is not.
    main = soup.find("main")
    if main is not None:
        soup = main

    first_h1 = soup.find("h1")
    heading = (first_h1.get_text(" ", strip=True) if first_h1 else "") or document_title

    blocks: list[tuple[str, bool, str]] = []
    # Innermost tables first: these pages nest a data table inside a layout
    # table, and rendering the outer one first would emit the inner table's
    # rows a second time as part of the outer table's text.
    while True:
        innermost = [t for t in soup.find_all("table") if not t.find("table")]
        if not innermost:
            break
        for table in innermost:
            context, data_rows, is_data_table = _table_to_rows(table)
            if is_data_table:
                for record_key, data_row in data_rows:
                    blocks.append(("\n".join(filter(None, [context, data_row])), True, record_key))
            elif context.strip():
                blocks.append((context, False, ""))
            table.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    prose = "\n".join(lines)
    if prose:
        blocks.append((prose, False, ""))

    return heading, blocks
