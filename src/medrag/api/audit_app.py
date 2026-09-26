"""Small local audit service: no Qdrant, embeddings, GPU, or retrieval imports."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from medrag.api.routes.audit import router
from medrag.api.routes.research import router as research_router

app = FastAPI(title="VeritasMed answer audit", version="0.7.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5174", "http://localhost:5174"],
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
app.include_router(router)
app.include_router(research_router)
