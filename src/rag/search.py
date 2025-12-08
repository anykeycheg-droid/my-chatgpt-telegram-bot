import faiss
import pickle
from sentence_transformers import SentenceTransformer

MODEL = SentenceTransformer("all-MiniLM-L6-v2")

INDEX = faiss.read_index("/data/faiss.index")
CHUNKS = pickle.load(open("/data/chunks.pkl","rb"))

def search(query, top_k=5):
    v = MODEL.encode([query])
    d,i = INDEX.search(v, top_k)
    return [ CHUNKS[ix] for ix in i[0] ]
