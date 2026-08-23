MAX_CHUNK_CHARS = 800

# Below this, a chunk is a stray heading or button label ('APPLY FOR
# HOUSING') carrying no answerable content -- but it still competes for
# one of the handful of slots a query gets back, so drop it.
MIN_CHUNK_CHARS = 50


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split page text into paragraph-sized chunks, merging short paragraphs
    up to max_chars so a chunk stays a coherent, retrievable unit."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n{paragraph}".strip() if current else paragraph
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate

    if current:
        chunks.append(current)

    return chunks
