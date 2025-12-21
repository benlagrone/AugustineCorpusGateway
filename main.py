import logging
import os
from typing import Any, Dict

import httpx
from fastapi import Body, FastAPI, HTTPException

CORPUS_BASE_URL = os.getenv("CORPUS_BASE_URL", "http://corpus:8001").rstrip("/")
ROUTE_TIMEOUT = float(os.getenv("ROUTE_TIMEOUT", "120"))


async def _load_dynamic_map() -> dict[str, str]:
    """Fetch authors from base corpus and map them all to the base URL."""
    url = f"{CORPUS_BASE_URL}/v1/authors"
    async with httpx.AsyncClient(timeout=ROUTE_TIMEOUT) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
    mapping: dict[str, str] = {}
    for author in data if isinstance(data, list) else []:
        slug = str(author.get("slug", "")).lower().strip()
        if not slug:
            continue
        mapping[slug] = CORPUS_BASE_URL
    if not mapping:
        raise RuntimeError("No personas loaded from base corpus.")
    return mapping


AUTHOR_CORPUS_URLS: dict[str, str] = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("corpus-gateway")

app = FastAPI(title="Corpus Gateway", version="1.0.0")


@app.on_event("startup")
async def load_mapping():
    global AUTHOR_CORPUS_URLS
    try:
        AUTHOR_CORPUS_URLS = await _load_dynamic_map()
        logger.info("Loaded personas: %s", list(AUTHOR_CORPUS_URLS.keys()))
    except Exception as e:
        logger.error("Failed to load persona map: %s", e)
        raise


def _resolve_target(payload: Dict[str, Any]) -> str:
    slug = payload.get("persona") or payload.get("author")
    if not slug:
        raise HTTPException(status_code=400, detail="Missing persona/author in request")
    slug = str(slug).lower()
    target = AUTHOR_CORPUS_URLS.get(slug)
    if not target:
        raise HTTPException(status_code=404, detail=f"Persona '{slug}' not configured")
    return target, slug


async def _forward(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    target, slug = _resolve_target(payload)
    url = f"{target.rstrip('/')}{path}"
    async with httpx.AsyncClient(timeout=ROUTE_TIMEOUT) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("Upstream error for %s -> %s: %s", slug, url, e)
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            logger.error("Gateway error for %s -> %s: %s", slug, url, e)
            raise HTTPException(status_code=502, detail=str(e))


@app.get("/healthz")
async def healthz():
    return {"ok": True, "personas": list(AUTHOR_CORPUS_URLS.keys())}


@app.get("/v1/authors")
async def authors():
    """Expose configured personas (slugs only)."""
    return [{"slug": slug} for slug in AUTHOR_CORPUS_URLS.keys()]


@app.post("/v1/context")
async def context(payload: Dict[str, Any] = Body(...)):
    return await _forward("/v1/context", payload)


@app.post("/v1/search")
async def search(payload: Dict[str, Any] = Body(...)):
    return await _forward("/v1/search", payload)


@app.post("/v1/embed")
async def embed(payload: Dict[str, Any] = Body(...)):
    return await _forward("/v1/embed", payload)


@app.post("/v1/generate")
async def generate(payload: Dict[str, Any] = Body(...)):
    return await _forward("/v1/generate", payload)
