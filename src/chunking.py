from .documents import Document


def chunk_document(
    document: Document,
    chunk_size: int = 300,
    overlap: int = 40,
) -> list[Document]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    words = document.content.split()
    if not words:
        return []

    step = chunk_size - overlap
    chunks = []
    for start in range(0, len(words), step):
        chunk_words = words[start : start + chunk_size]
        metadata = {**document.metadata, "chunk_index": len(chunks)}
        chunks.append(
            Document(
                id=f"{document.id}-{len(chunks):04d}",
                content=" ".join(chunk_words),
                metadata=metadata,
            )
        )
        if start + chunk_size >= len(words):
            break
    return chunks
