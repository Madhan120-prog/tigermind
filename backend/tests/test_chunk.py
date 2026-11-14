from app.ingestion.chunk import MAX_CHUNK_CHARS, chunk_text


def test_empty_and_whitespace_only_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("  \n\n \t\n") == []


def test_short_paragraphs_merge_into_one_chunk():
    assert chunk_text("a\nb\nc", max_chars=10) == ["a\nb\nc"]


def test_blank_lines_and_padding_are_stripped():
    assert chunk_text("\n  first  \n\n\n  second \n", max_chars=50) == ["first\nsecond"]


def test_splits_at_paragraph_boundary_when_merge_would_exceed_limit():
    text = "\n".join(["x" * 6, "y" * 6, "z" * 6])
    chunks = chunk_text(text, max_chars=13)
    assert chunks == ["x" * 6 + "\n" + "y" * 6, "z" * 6]
    assert all(len(c) <= 13 for c in chunks)


def test_single_long_paragraph_is_kept_whole_not_split():
    long_para = "w" * (MAX_CHUNK_CHARS + 200)
    assert chunk_text(long_para) == [long_para]


def test_long_paragraph_after_a_short_one_starts_its_own_chunk():
    long_para = "w" * 30
    assert chunk_text(f"short\n{long_para}", max_chars=20) == ["short", long_para]
