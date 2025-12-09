import os
import json
import faiss
from sentence_transformers import SentenceTransformer

INDEX_FILE = "src/rag/faiss.index"
DOCS_FILE = "src/rag/docs.json"

MODEL = SentenceTransformer("all-MiniLM-L6-v2")


def load_index():
    if not os.path.exists(INDEX_FILE):
        raise FileNotFoundError("❌ FAISS index not found")

    return faiss.read_index(INDEX_FILE)


def load_chunks():
    if not os.path.exists(DOCS_FILE):
        raise FileNotFoundError("❌ CHUNKS docs file not found")

    with open(DOCS_FILE, encoding="utf8") as f:
        return json.load(f)


INDEX = load_index()
CHUNKS = load_chunks()


def search(query: str, top_k: int = 5):

    vector = MODEL.encode([query])

    distances, indices = INDEX.search(vector, top_k)

    results = []

    for i in indices[0]:
        if i < 0 or i >= len(CHUNKS):
            continue
        results.append(CHUNKS[i])

    if not results:
        return "Ничего релевантного в базе не найдено."

    output = "🔎 Найдено по базе знаний:\n\n"

    for i, r in enumerate(results, 1):
        snippet = r["text"][:600].rstrip() + "..."
        source = r["source"].split("/")[-1]

        output += f"{i}. 📄 {source}\n{snippet}\n\n"

    return output.strip()
