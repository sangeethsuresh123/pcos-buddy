import os
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from langchain_chroma import Chroma

from backend.config import settings

_embedding_instance = None
_vectorstore: Chroma | None = None


class ChromaEmbeddingAdapter:
    def __init__(self, ef):
        self._ef = ef

    def __call__(self, texts):
        return self._ef(texts)

    def embed_documents(self, texts):
        return self._ef(texts)

    def embed_query(self, text):
        return self._ef([text])[0]


def _resolve_persist_dir() -> Path:
    raw = settings.chroma_persist_dir
    p = Path(raw)
    resolved = p.resolve()
    resolved_str = str(resolved)

    is_unc = resolved_str.startswith(("\\\\", "//")) or (
        resolved.drive and len(resolved.drive) > 2 and resolved.drive[1] != ":"
    )

    if is_unc:
        local_base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local")))
        local_dir = local_base / "pcos-chatbot" / "chroma_db"
        local_dir.mkdir(parents=True, exist_ok=True)
        print(f"[vectorstore] Path on network share ({resolved_str}). Persisting to {local_dir}")
        return local_dir

    p.mkdir(parents=True, exist_ok=True)
    return p


def get_embeddings() -> ChromaEmbeddingAdapter:
    global _embedding_instance
    if _embedding_instance is None:
        _embedding_instance = ChromaEmbeddingAdapter(DefaultEmbeddingFunction())
    return _embedding_instance


def get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        persist_dir = _resolve_persist_dir()

        client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        _vectorstore = Chroma(
            client=client,
            collection_name="pcos_knowledge",
            embedding_function=get_embeddings(),
        )
    return _vectorstore


def add_documents(documents: list) -> int:
    vs = get_vectorstore()
    ids = vs.add_documents(documents)
    return len(ids)


def get_retriever(search_k: int | None = None):
    vs = get_vectorstore()
    return vs.as_retriever(
        search_type="mmr",
        search_kwargs={"k": search_k or settings.retrieval_top_k},
    )
