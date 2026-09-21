"""Fetch and extract a PDF's tables, same contract as fetch.fetch_page.

Fees' actual dollar amounts live in per-year, per-residency PDF schedules,
not HTML -- confirmed for ug_resident.pdf 2026-08-24 (PLAN.md Section 11).
The table shape pdfplumber returns is the same "header row + data rows"
shape an HTML <table> reduces to, so extraction reuses fetch.rows_to_data
rather than duplicating the header/value pairing logic for a second format.
"""
import io

import httpx
import pdfplumber

from app.ingestion.fetch import USER_AGENT, rows_to_data


def fetch_pdf(url: str, timeout: float = 30.0) -> tuple[str, list[tuple[str, bool, str]]]:
    """Fetch a PDF and return (heading, [(text, is_atomic, record_key), ...]).

    heading comes from the table's own corner cell (e.g. "Undergraduate
    2025-26 Resident") -- these schedules carry no page title distinct from
    that, unlike an HTML page's <h1>. Each data row becomes one atomic block
    keyed by its own label (a credit-hour count here), for the same reason
    an HTML data row does: an exact-match lookup needs one row, not a table
    of similarly-worded neighbors.
    """
    response = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True)
    response.raise_for_status()

    blocks: list[tuple[str, bool, str]] = []
    heading = ""
    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                rows = [[cell or "" for cell in row] for row in table]

                # A PDF table can carry a title row above its real header
                # row (all cells but the first blank) -- an HTML <table>
                # doesn't, since its title lives outside the <table> tag
                # entirely. rows_to_data expects row 0 to already be the
                # header, so treating the title row as one collapses every
                # header to blank and folds all 18 rate rows into one
                # undifferentiated notes blob instead of 18 data rows.
                title = ""
                while rows and not any(rows[0][1:]):
                    title = rows.pop(0)[0]

                context, data_rows, is_data_table = rows_to_data(rows)
                context = "\n".join(filter(None, [title, context]))
                if not heading and title:
                    heading = title.replace("\n", " ")
                if is_data_table:
                    for record_key, data_row in data_rows:
                        blocks.append(("\n".join(filter(None, [context, data_row])), True, record_key))
                elif context.strip():
                    blocks.append((context, False, ""))

    return heading, blocks
