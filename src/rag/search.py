import json
import logging
from pathlib import Path
from typing import List, Dict, Any

import faiss
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "faiss.index"
DOCS_FILE = BASE_DIR / "docs.json"

# Ограничим число потоков FAISS (чуть экономим память и CPU)
try:
    faiss.omp_set_num_threads(1)
except Exception:
    # если сборка без OpenMP — просто игнорируем
    pass

MODEL = SentenceTransformer("all-MiniLM-L6-v2")

INDEX = None
CHUNKS: List[Dict[str, Any]] = []
RAG_READY = False


def _load_index_mmap() -> None:
    """Загрузка FAISS индекса в режиме memory-mapped.

    Если что-то пошло не так — просто отключаем RAG
    и даём боту работать без внутреннего поиска.
    """
    global INDEX, CHUNKS, RAG_READY

    try:
        if not INDEX_FILE.exists():
            logging.error(f"FAISS index file not found: {INDEX_FILE}")
            RAG_READY = False
            return

        if not DOCS_FILE.exists():
            logging.error(f"Docs file not found: {DOCS_FILE}")
            RAG_READY = False
            return

        logging.info(f"Loading FAISS index (mmap) from {INDEX_FILE}")

        # 🔥 Ключевой момент: используем memory-mapped режим
        INDEX = faiss.read_index(str(INDEX_FILE), faiss.IO_FLAG_MMAP)

        with open(DOCS_FILE, encoding="utf-8") as f:
            CHUNKS = json.load(f)

        RAG_READY = True
        logging.info(
            "FAISS index loaded in mmap mode. "
            f"Chunks: {len(CHUNKS)}"
        )

    except Exception:
        logging.exception("Failed to load FAISS index in mmap mode")
        INDEX = None
        CHUNKS = []
        RAG_READY = False


# Загружаем индекс при импорте модуля
_load_index_mmap()


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

    if not RAG_READY or INDEX is None or not CHUNKS:
        # Индекс не загрузился или база пуста — просто возвращаем пустой список.
        # Внешняя логика (chat_func.try_rag) аккуратно обработает это.
        logging.warning("RAG search requested, but index is not ready")
        return []

    # Векторизуем запрос
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
