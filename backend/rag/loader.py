from langchain_community.document_loaders import (
    DirectoryLoader,
    PyPDFLoader,
    TextLoader,
)
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import settings


def load_documents(directory: str | None = None) -> list[Document]:
    directory = directory or settings.knowledge_dir

    loaders = {
        "*.pdf": (PyPDFLoader, {}),
        "*.txt": (TextLoader, {"encoding": "utf-8"}),
        "*.md": (TextLoader, {"encoding": "utf-8"}),
    }

    documents: list[Document] = []
    for pattern, (loader_cls, loader_kwargs) in loaders.items():
        loader = DirectoryLoader(
            directory,
            glob=pattern,
            loader_cls=loader_cls,
            loader_kwargs=loader_kwargs,
            show_progress=True,
            use_multithreading=True,
        )
        documents.extend(loader.load())

    return documents


def split_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        length_function=len,
        add_start_index=True,
    )
    return splitter.split_documents(documents)
