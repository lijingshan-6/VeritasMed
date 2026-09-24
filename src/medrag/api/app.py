"""
VeritasMed FastAPI application — pure API, no frontend serving.

Development:
  PYTHONPATH=src uvicorn medrag.api.app:app --host 0.0.0.0 --port 8000

Production:
  Same command. Serve the built frontend separately (nginx / container).
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root before any module reads os.environ
load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env")

# sentence_transformers MUST be imported before qdrant_client — importing
# qdrant_client first initialises grpcio's native C++ runtime which conflicts
# with PyTorch's internal threads and causes a segfault on Windows.
# The route modules pull in qdrant_client at import time, so we pre-empt here.
import pyarrow  # noqa: F401 -- Arrow must precede the ML/native runtime on Windows
import sentence_transformers  # noqa: F401

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from medrag.api.routes import ask, audit, chunk, corpus, document, history, search

app = FastAPI(
    title="VeritasMed API",
    description="Self-verifying medical literature QA backend",
    version="0.4.0",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Allow any origin so the frontend can be served from any dev port or CDN.
# Tighten to specific origins in production via CORS_ORIGINS env var.
_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_origins != ["*"],  # credentials require explicit origins
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ───────────────────────────────────────────────────────────────
app.include_router(ask.router)
app.include_router(search.router)
app.include_router(document.router)
app.include_router(chunk.router)
app.include_router(history.router)
app.include_router(corpus.router)
app.include_router(audit.router)
