import json
from pathlib import Path
from typing import List, Dict, Any

import faiss
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "faiss.index"
DOCS_FILE = BASE_DIR / "docs.json"

MODEL = SentenceTransformer("all-MiniLM-L6-v2")
INDEX = faiss.read_index(str(INDEX_FILE))

with open(DOCS_FILE, encoding="utf-8") as f:
    CHUNKS: List[Dict[str, Any]] = json.load(f)


def search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    FAISS-поиск по внутренней базе.

    Возвращает список словарей:
    {
        "rank": int,
        "score": float,
        "text": str,
        "source": str,
        "source_file": str,
        "page": int | None,
        "section": str | None,
    }
    """
    if not query:
        return []

    v = MODEL.encode([query])
    distances, indices = INDEX.search(v, top_k)

    results: List[Dict[str, Any]] = []
    for rank, (idx, dist) in enumerate(zip(indices[0], distances[0]), start=1):
        if idx < 0:
            continue
        if idx >= len(CHUNKS):
            continue

        chunk = CHUNKS[idx]
        if isinstance(chunk, dict):
            text = chunk.get("text")
            source = chunk.get("source")
            source_file = chunk.get("source_file")
            page = chunk.get("page")
            section = chunk.get("section")
        else:
            # на всякий случай, если старый формат docs.json
            text = str(chunk)
            source = None
            source_file = None
            page = None
            section = None

        results.append(
            {
                "rank": rank,
                "score": float(dist),
                "text": text,
                "source": source,
                "source_file": source_file,
                "page": page,
                "section": section,
            }
        )

    return results
