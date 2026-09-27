"""No-key Ask replay with original sources and saved audits; no ML runtime."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from medrag.api.routes.audit import router as audit_router
from medrag.api.routes.conversations import router as conversation_router
from medrag.api.routes.research import router as research_router
from medrag.api.routes.replay_chunks import router as chunk_router

app = FastAPI(title="VeritasMed saved conversation replay", version="0.8.0")


@app.middleware("http")
async def saved_only(request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        return JSONResponse(status_code=409, content={
            "detail": "Saved replay makes no model calls. Start the full Ask service to run a new question or audit.",
        })
    return await call_next(request)


app.include_router(conversation_router)
app.include_router(audit_router)
app.include_router(research_router)
app.include_router(chunk_router)
