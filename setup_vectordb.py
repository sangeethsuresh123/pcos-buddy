"""Index knowledge documents into the vector store."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def main():
    from backend.rag.loader import load_documents, split_documents
    from backend.rag.vectorstore import add_documents, get_vectorstore
    from backend.config import settings

    vs = get_vectorstore()
    print(f"ChromaDB persist dir: {settings.chroma_persist_dir}")
    print("Loading documents...")

    documents = load_documents()
    if not documents:
        print("No documents found in the knowledge directory.")
        print(f"Please add PDF/TXT/MD files to: backend/knowledge/pcos_docs/")
        return

    print(f"Loaded {len(documents)} document pages.")
    chunks = split_documents(documents)
    print(f"Split into {len(chunks)} chunks.")

    added = add_documents(chunks)
    print(f"Indexed {added} chunks into the vector store.")

    count = vs._collection.count()
    print(f"Total chunks in vector store: {count}")


if __name__ == "__main__":
    main()