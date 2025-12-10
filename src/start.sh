#!/usr/bin/env bash

set -e

echo "✅ Starting bot with prebuilt FAISS index"

exec python -u src/main.py
