#!/usr/bin/env bash

mkdir -p /data/docs

if [ ! -f /data/faiss.index ]; then
    echo "🧠 Building FAISS knowledge base..."

    python src/rag/parse_docs.py
    python src/rag/build_faiss.py

else
    echo "✅ FAISS index already exists, skipping rebuild."
fi

python src/main.py
