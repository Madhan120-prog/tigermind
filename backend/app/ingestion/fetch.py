import httpx
from bs4 import BeautifulSoup

USER_AGENT = "TigerMind-Ingestion/0.1 (portfolio project; contact via github.com/Madhan120-prog/tigermind)"


def _table_to_text(table) -> tuple[str, bool]:
    """Render an HTML table as 'row label -- header: value, header: value'
    lines, so a row's values stay attached to their column headers instead
    of collapsing into an ambiguous list of numbers once flattened to text.

    Returns (text, is_data_table). is_data_table is True only when at least
    one row actually produced header:value pairs -- that pairing is the sole
    reason a table is worth protecting from the chunker, so a table that
    produced none is markup being used for page layout, not data.
    """
    rows = table.find_all("tr")
    if not rows:
        return "", False

    header_cells = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
    # The header row's first ("corner") cell is nominally the row-label
    # column's header, but pages often stash a table-wide caveat there
    # instead (e.g. an eligibility note) -- surface it rather than
    # silently dropping it, since it's never used as a per-row value.
    corner_note, headers = (
        (header_cells[0], header_cells[1:]) if header_cells else ("", [])
    )

    lines = [corner_note] if corner_note else []
    paired_rows = 0
    for row in rows[1:]:
        values = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
        if not values or not values[0]:
            continue
        label = values[0]
        # zip(headers, values[1:]) -- `headers` has already dropped the
        # corner cell, so slicing it again here shifts every value one
        # column left and silently discards the last one (zip stops at the
        # shorter list). That mislabeled every rate in the corpus by a year.
        pairs = [
            f"{header}: {value}"
            for header, value in zip(headers, values[1:])
            if header and value
        ]
        if pairs:
            paired_rows += 1
        lines.append(f"{label} -- " + ", ".join(pairs) if pairs else label)

    return "\n".join(lines), paired_rows > 0


def fetch_page_blocks(url: str, timeout: float = 15.0) -> list[tuple[str, bool]]:
    """Fetch a page and return (text, is_atomic) blocks.

    A table becomes an atomic block (is_atomic=True) the chunker must never
    split only when it is a real data table -- splitting one mid-row detaches
    a value from the header/year it belongs to, which is exactly the bug that
    motivated this. Tables used purely for page layout have no such pairing
    to protect, so they come back as ordinary splittable prose. Surrounding
    prose becomes one block the chunker is free to split normally.

    Deterministic HTTP + HTML parsing, not an AI-summarizing fetch tool --
    see PLAN.md Section 11 for why that distinction matters for ingestion.
    """
    response = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    blocks: list[tuple[str, bool]] = []
    # Innermost tables first: these pages nest a data table inside a layout
    # table, and rendering the outer one first would emit the inner table's
    # rows a second time as part of the outer table's text.
    while True:
        innermost = [t for t in soup.find_all("table") if not t.find("table")]
        if not innermost:
            break
        for table in innermost:
            table_text, is_data_table = _table_to_text(table)
            if table_text.strip():
                blocks.append((table_text, is_data_table))
            table.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    prose = "\n".join(lines)
    if prose:
        blocks.append((prose, False))

    return blocks
