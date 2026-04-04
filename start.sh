#!/bin/bash
set -e

# Start the FastAPI game API on port 8000 in the background
PYTHONPATH=src uvicorn src.api:app --host 0.0.0.0 --port 8000 &

# Start Streamlit on the port Railway expects (defaults to 8501 locally)
streamlit run src/game1.py \
  --server.address=0.0.0.0 \
  --server.port="${PORT:-8501}" \
  --server.headless=true
