from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .config import CONFIG
from .retriever import query_context


app = FastAPI(title="Local Repo RAG", version="0.1.0")


class RagQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=CONFIG.top_k_default, ge=1, le=20)


@app.get("/healthz")
def healthz() -> dict:
    return {
        "ok": True,
        "collection": CONFIG.collection_name,
        "index_dir": str(CONFIG.index_dir),
    }


@app.post("/rag/query")
def rag_query(payload: RagQueryRequest) -> dict:
    context = query_context(question=payload.question, k=payload.k)
    return {"context": context}
