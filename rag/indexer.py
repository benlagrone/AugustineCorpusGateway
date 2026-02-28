from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Iterator

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from .config import CONFIG, RagConfig


def iter_source_files(cfg: RagConfig) -> Iterator[Path]:
    for root, dirs, files in os.walk(cfg.repo_root):
        dirs[:] = [d for d in dirs if d not in cfg.excluded_dir_names]
        for filename in files:
            path = Path(root) / filename
            if cfg.is_candidate_file(path):
                yield path


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    tokens = text.split()
    if not tokens:
        return []

    if overlap >= chunk_size:
        raise ValueError("chunk overlap must be smaller than chunk size")

    step = chunk_size - overlap
    chunks: list[str] = []

    for i in range(0, len(tokens), step):
        block = tokens[i : i + chunk_size]
        if not block:
            break
        chunks.append(" ".join(block))
        if i + chunk_size >= len(tokens):
            break

    return chunks


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "files": {}}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def signature_for(path: Path, text: str) -> dict:
    stat = path.stat()
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {"mtime_ns": stat.st_mtime_ns, "size": stat.st_size, "sha256": digest}


def get_collection(cfg: RagConfig, reset: bool = False):
    cfg.index_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(cfg.index_dir))
    if reset:
        try:
            client.delete_collection(cfg.collection_name)
        except Exception:
            pass

    embedding_fn = SentenceTransformerEmbeddingFunction(model_name=cfg.embedding_model)
    return client.get_or_create_collection(
        name=cfg.collection_name,
        embedding_function=embedding_fn,
    )


def upsert_file_chunks(collection, rel_path: str, language: str, file_hash: str, chunks: list[str]) -> int:
    collection.delete(where={"file": rel_path})

    if not chunks:
        return 0

    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict] = []

    for i, chunk in enumerate(chunks):
        raw_id = f"{rel_path}:{i}:{file_hash}"
        chunk_id = hashlib.sha1(raw_id.encode("utf-8")).hexdigest()
        ids.append(chunk_id)
        docs.append(chunk)
        metas.append(
            {
                "file": rel_path,
                "language": language,
                "chunk_index": i,
                "sha256": file_hash,
            }
        )

    batch_size = 128
    for start in range(0, len(ids), batch_size):
        end = start + batch_size
        collection.add(
            ids=ids[start:end],
            documents=docs[start:end],
            metadatas=metas[start:end],
        )

    return len(ids)


def build_index(cfg: RagConfig, full: bool) -> dict:
    collection = get_collection(cfg, reset=full)
    previous_state = {"version": 1, "files": {}} if full else load_state(cfg.state_file)
    old_files = previous_state.get("files", {})

    current_files: dict[str, dict] = {}
    indexed_files = 0
    skipped_files = 0
    indexed_chunks = 0

    for path in iter_source_files(cfg):
        rel_path = cfg.relative_path(path)
        text = read_text(path)
        signature = signature_for(path, text)
        current_files[rel_path] = signature

        if not full and old_files.get(rel_path) == signature:
            skipped_files += 1
            continue

        chunks = chunk_text(
            text=text,
            chunk_size=cfg.chunk_size_tokens,
            overlap=cfg.chunk_overlap_tokens,
        )
        language = cfg.detect_language(path)
        indexed_chunks += upsert_file_chunks(
            collection=collection,
            rel_path=rel_path,
            language=language,
            file_hash=signature["sha256"],
            chunks=chunks,
        )
        indexed_files += 1

    removed_files = sorted(set(old_files.keys()) - set(current_files.keys()))
    for rel_path in removed_files:
        collection.delete(where={"file": rel_path})

    save_state(cfg.state_file, {"version": 1, "files": current_files})

    return {
        "indexed_files": indexed_files,
        "skipped_files": skipped_files,
        "removed_files": len(removed_files),
        "indexed_chunks": indexed_chunks,
        "tracked_files": len(current_files),
        "collection_count": collection.count(),
        "index_dir": str(cfg.index_dir),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build or update the local repo-scoped RAG index.")
    parser.add_argument("--full", action="store_true", help="Rebuild from scratch.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stats = build_index(cfg=CONFIG, full=args.full)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
