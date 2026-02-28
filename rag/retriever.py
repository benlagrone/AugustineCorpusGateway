from __future__ import annotations

import argparse
import json

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from .config import CONFIG, RagConfig


def get_collection(cfg: RagConfig):
    cfg.index_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(cfg.index_dir))
    embedding_fn = SentenceTransformerEmbeddingFunction(model_name=cfg.embedding_model)
    return client.get_or_create_collection(
        name=cfg.collection_name,
        embedding_function=embedding_fn,
    )


def query_context(question: str, k: int, cfg: RagConfig = CONFIG) -> list[dict]:
    collection = get_collection(cfg)
    if collection.count() == 0:
        return []

    result = collection.query(query_texts=[question], n_results=k)
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]

    context = []
    for doc, meta in zip(docs, metas):
        context.append(
            {
                "file": meta.get("file", ""),
                "language": meta.get("language", ""),
                "excerpt": doc,
            }
        )
    return context


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query local RAG index for relevant code/doc context.")
    parser.add_argument("--question", required=True, help="Natural language question.")
    parser.add_argument("--k", type=int, default=CONFIG.top_k_default, help="Number of results to return.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    context = query_context(question=args.question, k=args.k)
    print(json.dumps({"context": context}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
