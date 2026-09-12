from langchain_core.retrievers import BaseRetriever

from backend.rag.vectorstore import get_retriever


def get_pcos_retriever() -> BaseRetriever:
    return get_retriever()
