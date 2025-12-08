import os
from sentence_transformers import SentenceTransformer
import faiss
import pickle

TEXT_FILE = "/data/all_docs.txt"
INDEX_OUT = "/data/faiss.index"


def chunk_text(txt, size=900):
    words = txt.split()
    for i in range(0, len(words), size):
        yield " ".join(words[i:i+size])


def main():
    with open(TEXT_FILE, encoding="utf8") as f:
        raw = f.read()

    chunks = list(chunk_text(raw))

    model = SentenceTransformer("all-MiniLM-L6-v2")
    vectors = model.encode(chunks)

    dim = vectors.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(vectors)

    faiss.write_index(index, INDEX_OUT)

    with open("/data/chunks.pkl","wb") as f:
        pickle.dump(chunks, f)

    print("✅ FAISS ready:", len(chunks))


if __name__ == "__main__":
    main()
