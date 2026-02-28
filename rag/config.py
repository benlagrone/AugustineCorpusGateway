from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".md": "markdown",
    ".json": "json",
}


@dataclass(frozen=True)
class RagConfig:
    repo_root: Path = Path(__file__).resolve().parent.parent
    collection_name: str = field(
        default_factory=lambda: f"{Path(__file__).resolve().parent.parent.name}_repo"
    )
    chunk_size_tokens: int = 800
    chunk_overlap_tokens: int = 150
    top_k_default: int = 5
    max_file_bytes: int = 2_000_000
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    allowed_extensions: tuple[str, ...] = tuple(EXTENSION_TO_LANGUAGE.keys())
    excluded_dir_names: tuple[str, ...] = (
        ".git",
        ".rag",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        ".next",
    )
    excluded_globs: tuple[str, ...] = ("*.lock", ".DS_Store")

    @property
    def rag_dir(self) -> Path:
        return self.repo_root / ".rag"

    @property
    def index_dir(self) -> Path:
        return self.rag_dir / self.repo_root.name

    @property
    def state_file(self) -> Path:
        return self.rag_dir / "index_state.json"

    @property
    def context_dir(self) -> Path:
        return self.rag_dir / "context"

    def relative_path(self, path: Path) -> str:
        return path.resolve().relative_to(self.repo_root).as_posix()

    def detect_language(self, path: Path) -> str:
        return EXTENSION_TO_LANGUAGE.get(path.suffix.lower(), "text")

    def is_candidate_file(self, path: Path) -> bool:
        if not path.is_file():
            return False

        rel = self.relative_path(path)
        parts = rel.split("/")
        if any(part in self.excluded_dir_names for part in parts):
            return False

        suffix = path.suffix.lower()
        if suffix not in self.allowed_extensions:
            return False

        for pattern in self.excluded_globs:
            if path.match(pattern):
                return False

        try:
            if path.stat().st_size > self.max_file_bytes:
                return False
        except OSError:
            return False

        return True


CONFIG = RagConfig()
