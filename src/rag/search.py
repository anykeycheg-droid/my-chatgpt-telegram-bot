import json
import faiss
from sentence_transformers import SentenceTransformer

INDEX_FILE = "src/rag/faiss.index"
DOCS_FILE = "src/rag/docs.json"

MODEL = SentenceTransformer("all-MiniLM-L6-v2")

INDEX = faiss.read_index(INDEX_FILE)

with open(DOCS_FILE, encoding="utf8") as f:
    CHUNKS = json.load(f)


def search(query, top_k=5):
    v = MODEL.encode([query])
    d, i = INDEX.search(v, top_k)

    results = []

    for ix in i[0]:
        results.append(CHUNKS[ix])

    return results
