#!/usr/bin/env bash
set -ex

# Убираем тяжёлый .git, чтобы не занимать место/память в контейнере
rm -rf .git

# Ограничиваем количество потоков у BLAS/NumPy/FAISS — экономим память
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

echo "✅ Starting bot with prebuilt FAISS index (mmap mode)"

exec python -u src/main.py
