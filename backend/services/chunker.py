import json
import os
import re
from pathlib import Path
from typing import Any
import faiss
import numpy as np

from backend.services.embedder import embed


INDEXES_DIR = Path(__file__).resolve().parent.parent / "data" / "indexes"
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"


def ensure_storage_dirs():
    """Ensure data/indexes and data/uploads directories exist."""
    INDEXES_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def extract_text_from_pdf(filepath: str | Path) -> list[dict[str, Any]]:
    """
    Extract text per page from a PDF file using PyMuPDF (fitz).
    Returns a list of dicts: [{"page": page_number, "text": text}, ...]
    """
    import fitz  # PyMuPDF
    doc = fitz.open(str(filepath))
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        if text:
            pages.append({"page": page_num + 1, "text": text})
    doc.close()
    return pages


def extract_text_from_docx(filepath: str | Path) -> list[dict[str, Any]]:
    """
    Extract text from a DOCX file using python-docx.
    Returns a list with page 1 representing the document text.
    """
    import docx
    doc = docx.Document(str(filepath))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    full_text = "\n\n".join(paragraphs)
    if not full_text:
        return []
    return [{"page": 1, "text": full_text}]


def extract_text_from_txt(filepath: str | Path) -> list[dict[str, Any]]:
    """
    Extract text from a plain TXT file.
    Returns a list with page 1 representing the document text.
    """
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        text = f.read().strip()
    if not text:
        return []
    return [{"page": 1, "text": text}]


def extract_document_pages(filepath: str | Path) -> list[dict[str, Any]]:
    """
    Extract pages and text according to file extension.
    Supported: .pdf, .docx, .txt
    """
    path = Path(filepath)
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    elif ext == ".docx":
        return extract_text_from_docx(path)
    elif ext in (".txt", ".text", ".md"):
        return extract_text_from_txt(path)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Supported formats are PDF, DOCX, TXT.")


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences while keeping punctuation."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def split_text_into_chunks(
    pages: list[dict[str, Any]],
    chunk_size: int = 800,
    overlap: int = 100
) -> list[dict[str, Any]]:
    """
    Split document text into overlapping chunks of approx chunk_size characters with overlap,
    respecting paragraph and sentence boundaries wherever possible.
    Preserves page number references.
    """
    chunks: list[dict[str, Any]] = []
    chunk_id = 0

    for page_info in pages:
        page_num = page_info.get("page", 1)
        raw_text = page_info.get("text", "")
        if not raw_text.strip():
            continue

        # Split into paragraphs
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw_text) if p.strip()]

        current_chunk_parts: list[str] = []
        current_len = 0

        for para in paragraphs:
            # If paragraph itself is larger than chunk_size, split by sentences
            if len(para) > chunk_size:
                sentences = _split_into_sentences(para)
                for sentence in sentences:
                    sentence_len = len(sentence)
                    if current_len + sentence_len > chunk_size and current_chunk_parts:
                        chunk_text = " ".join(current_chunk_parts).strip()
                        chunks.append({
                            "chunk_id": chunk_id,
                            "page": page_num,
                            "text": chunk_text
                        })
                        chunk_id += 1

                        # Compute overlap prefix from end of previous chunk
                        if overlap > 0 and len(chunk_text) > overlap:
                            overlap_text = chunk_text[-overlap:].strip()
                            # Try to cut at first word boundary
                            first_space = overlap_text.find(" ")
                            if first_space != -1:
                                overlap_text = overlap_text[first_space + 1:].strip()
                            current_chunk_parts = [overlap_text, sentence]
                            current_len = len(overlap_text) + 1 + sentence_len
                        else:
                            current_chunk_parts = [sentence]
                            current_len = sentence_len
                    else:
                        current_chunk_parts.append(sentence)
                        current_len += sentence_len + 1
            else:
                para_len = len(para)
                if current_len + para_len > chunk_size and current_chunk_parts:
                    chunk_text = "\n\n".join(current_chunk_parts).strip()
                    chunks.append({
                        "chunk_id": chunk_id,
                        "page": page_num,
                        "text": chunk_text
                    })
                    chunk_id += 1

                    # Compute overlap prefix from end of previous chunk
                    if overlap > 0 and len(chunk_text) > overlap:
                        overlap_text = chunk_text[-overlap:].strip()
                        first_space = overlap_text.find(" ")
                        if first_space != -1:
                            overlap_text = overlap_text[first_space + 1:].strip()
                        current_chunk_parts = [overlap_text, para]
                        current_len = len(overlap_text) + 2 + para_len
                    else:
                        current_chunk_parts = [para]
                        current_len = para_len
                else:
                    current_chunk_parts.append(para)
                    current_len += para_len + 2

        if current_chunk_parts:
            chunk_text = "\n\n".join(current_chunk_parts).strip()
            if chunk_text:
                chunks.append({
                    "chunk_id": chunk_id,
                    "page": page_num,
                    "text": chunk_text
                })
                chunk_id += 1

    return chunks


def get_index_path(document_id: int) -> Path:
    return INDEXES_DIR / f"doc_{document_id}.faiss"


def get_chunks_path(document_id: int) -> Path:
    return INDEXES_DIR / f"doc_{document_id}_chunks.json"


def build_and_save_document_index(document_id: int, chunks: list[dict[str, Any]]):
    """
    Embed all chunks for a document, build a FAISS inner product index,
    and persist both index and chunks metadata to disk.
    """
    ensure_storage_dirs()
    if not chunks:
        # Create empty dummy index
        dummy_vecs = embed(["placeholder"])
        dim = dummy_vecs.shape[1]
        index = faiss.IndexFlatIP(dim)
        faiss.write_index(index, str(get_index_path(document_id)))
        with open(get_chunks_path(document_id), "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        return index, []

    chunk_texts = [c["text"] for c in chunks]
    embeddings = embed(chunk_texts)
    dim = embeddings.shape[1]

    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    faiss.write_index(index, str(get_index_path(document_id)))
    with open(get_chunks_path(document_id), "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)

    return index, chunks


def load_document_index(document_id: int) -> tuple[faiss.Index | None, list[dict[str, Any]]]:
    """
    Load a document's FAISS index and chunk metadata from disk.
    Returns (index, chunks) or (None, []) if not found.
    """
    idx_path = get_index_path(document_id)
    chunks_path = get_chunks_path(document_id)

    if not idx_path.exists() or not chunks_path.exists():
        return None, []

    index = faiss.read_index(str(idx_path))
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    return index, chunks


def search_document_chunks(
    document_id: int,
    query: str,
    top_k: int = 5
) -> list[dict[str, Any]]:
    """
    Search chunks of a document by semantic similarity to a query.
    Returns list of chunks with an added 'score' field.
    """
    index, chunks = load_document_index(document_id)
    if index is None or not chunks or index.ntotal == 0:
        return []

    q_vec = embed([query])
    k = min(top_k, index.ntotal)
    scores, indices = index.search(q_vec, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if 0 <= idx < len(chunks):
            chunk_copy = dict(chunks[idx])
            chunk_copy["score"] = float(score)
            results.append(chunk_copy)
    return results
