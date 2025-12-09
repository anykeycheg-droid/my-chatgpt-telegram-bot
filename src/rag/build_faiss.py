import json
import faiss
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

RAW_FILE = "src/rag/raw_docs.json"
CHUNKS_FILE = "src/rag/docs.json"
INDEX_FILE = "src/rag/faiss.index"

CHUNK_SIZE = 900


def chunk_text(text):
    words = text.split()
    for i in range(0, len(words), CHUNK_SIZE):
        yield " ".join(words[i:i + CHUNK_SIZE])


def main():

    print("📥 Load RAW documents...")
    with open(RAW_FILE, encoding="utf8") as f:
        docs = json.load(f)

    print(f"📄 Documents: {len(docs)}")

    chunks = []

    print("🔪 Chunking texts...")
    for d in tqdm(docs):
        for c in chunk_text(d["text"]):
            chunks.append({
                "source": d["source"],
                "text": c,
            })

    print(f"✂ Total chunks: {len(chunks)}")

    model = SentenceTransformer("all-MiniLM-L6-v2")

    texts = [c["text"] for c in chunks]

    print("🧠 Generating embeddings...")

    vectors = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
    )

    print("📦 Building FAISS index...")
    dim = vectors.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(vectors)

    faiss.write_index(index, INDEX_FILE)

    with open(CHUNKS_FILE, "w", encoding="utf8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print("\n✅ FAISS READY")
    print(f"INDEX: {INDEX_FILE}")
    print(f"CHUNKS: {len(chunks)}")


if __name__ == "__main__":
    main()
