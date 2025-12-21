# Corpus Gateway (persona router)

A lightweight FastAPI proxy that routes persona-tagged requests to the correct corpus service URL.

## Routing map
- Dynamic: on startup the gateway calls `CORPUS_BASE_URL/v1/authors` and maps all returned slugs to `CORPUS_BASE_URL`.

## Endpoints (proxy)
- `POST /v1/context` (requires `author` or `persona` in body)
- `POST /v1/search`  (requires `author` or `persona` in body)
- `POST /v1/embed`   (requires `author` or `persona` in body)
- `POST /v1/generate` (requires `persona` in body)

Utility:
- `GET /v1/authors` returns the configured persona slugs.
- `GET /healthz` reports readiness and configured personas.

## Run locally
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8002
```

## Docker
```bash
docker build -t corpus-gateway .
docker run -p 8002:8001 corpus-gateway
```

## Notes
- This router is optional; the API can call the multi-author corpus directly. Use the gateway if you want a stable endpoint while scaling/sharding corpora per author.
