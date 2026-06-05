from settings import settings


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    """
    Split text into overlapping chunks by character count.
    Returns a single-element list if text fits within one chunk.
    """
    chunk_size = chunk_size or settings.TRANSCRIPT_CHUNK_CHARS
    overlap = overlap or settings.TRANSCRIPT_CHUNK_OVERLAP_CHARS

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks
