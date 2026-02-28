#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 \"your question\"" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_URL="${RAG_BASE_URL:-http://127.0.0.1:8010}"
QUESTION="$*"

OUT_DIR="$REPO_ROOT/.rag/context"
mkdir -p "$OUT_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_FILE="$OUT_DIR/query-$STAMP.json"

PAYLOAD="$(python3 -c 'import json,sys; print(json.dumps({"question": " ".join(sys.argv[1:])}))' "$@")"
RESPONSE="$(curl -fsS "$BASE_URL/rag/query" -H "Content-Type: application/json" -d "$PAYLOAD")"
printf '%s\n' "$RESPONSE" > "$OUT_FILE"

python3 - "$OUT_FILE" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
ctx = data.get("context", [])

print(f"saved: {path}")
print(f"results: {len(ctx)}")
for i, row in enumerate(ctx, 1):
    file_path = row.get("file", "")
    excerpt = " ".join((row.get("excerpt", "") or "").split())
    excerpt = excerpt[:180] + ("..." if len(excerpt) > 180 else "")
    print(f"{i}. {file_path}")
    print(f"   {excerpt}")
PY
