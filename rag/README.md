# Repo-Scoped RAG (AugustineCorpusGateway)

This package provides local, repo-scoped retrieval for coding prompts.

- Index scope: this repo only (AugustineCorpusGateway)
- Vector store: Chroma in \.rag/AugustineCorpusGateway/
- API: `POST /rag/query`

## What it indexes

- Code/docs files: \.py, \.js, \.jsx, \.ts, \.tsx, \.md, \.json
- Excludes heavy/non-source directories:
  - \.git, \.rag, \.venv, venv, __pycache__, node_modules, dist, build, .next

## Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r rag/requirements.txt
```

## Build Index

Full rebuild:

```bash
rm -rf .rag/AugustineCorpusGateway
python -m rag.indexer --full
```

Incremental update:

```bash
python -m rag.indexer
```

## Run API

```bash
PYTHONPATH=. uvicorn rag.server:app --reload --port 8010
```

Endpoints:

- `GET /healthz`
- `POST /rag/query`

Example:

```bash
curl -s http://127.0.0.1:8010/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Where is persona selection enforced?","k":5}'
```

## Query Script Helpers

Use the wrapper script to query and save context JSON:

```bash
./scripts/rq "Where is persona selection enforced?"
```

Output file is written to \.rag/context/query-<timestamp>.json.

## Prompt Contract

Paste retrieved context above your task prompt:

```text
You are working inside the AugustineCorpusGateway codebase.

Relevant context:
- file: ...
  excerpt: ...

Task:
<your request>
```

## Codex Integration

Run Codex with RAG context injected automatically:

```bash
./scripts/cx "Where is persona selection enforced and how should we refactor it?"
```

Print the composed prompt for VS Code Codex chat paste:

```bash
./scripts/cx --print-prompt "Where is persona selection enforced?"
```

Use a different retrieval question than the task:

```bash
./scripts/cx --question "Where is persona selection enforced?" "Refactor persona selection to a single policy module."
```
