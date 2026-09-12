import uuid

from langchain_openrouter import ChatOpenRouter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from backend.config import settings
from backend.chat.memory import SessionManager
from backend.chat.prompts import (
    get_chat_prompt,
    get_rag_chain_prompt,
    get_condense_prompt,
)
from backend.rag.retriever import get_pcos_retriever

_session_manager = SessionManager(max_turns=settings.max_memory_turns)


def _get_llm() -> ChatOpenRouter:
    return ChatOpenRouter(
        model=settings.openrouter_model,
        api_key=settings.openrouter_api_key,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )


def _format_docs(docs: list) -> str:
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


def create_chat_chain(session_id: str | None = None):
    if session_id is None:
        session_id = str(uuid.uuid4())

    memory = _session_manager.get_memory(session_id)
    llm = _get_llm()
    prompt = get_chat_prompt()

    chain = prompt | llm | StrOutputParser()

    def invoke(user_input: str) -> tuple[str, str]:
        chat_history = memory.get_history()
        response = chain.invoke({
            "input": user_input,
            "chat_history": chat_history,
        })
        memory.add_user_message(user_input)
        memory.add_ai_message(response)
        return response, session_id

    return invoke, session_id


def create_rag_chain(session_id: str | None = None):
    if session_id is None:
        session_id = str(uuid.uuid4())

    memory = _session_manager.get_memory(session_id)
    llm = _get_llm()
    retriever = get_pcos_retriever()
    prompt = get_rag_chain_prompt()

    chain = prompt | llm | StrOutputParser()

    def invoke(user_input: str) -> tuple[str, list, str]:
        chat_history = memory.get_history()
        docs = retriever.invoke(user_input)
        context = _format_docs(docs)

        response = chain.invoke({
            "input": user_input,
            "chat_history": chat_history,
            "context": context,
        })

        memory.add_user_message(user_input)
        memory.add_ai_message(response)
        return response, docs, session_id

    return invoke, session_id


async def create_rag_chain_streaming(session_id: str | None = None):
    if session_id is None:
        session_id = str(uuid.uuid4())

    memory = _session_manager.get_memory(session_id)
    llm = _get_llm()
    retriever = get_pcos_retriever()
    prompt = get_rag_chain_prompt()

    chain = prompt | llm

    async def stream(user_input: str):
        chat_history = memory.get_history()
        docs = retriever.invoke(user_input)
        context = _format_docs(docs)

        full_response = ""
        async for chunk in chain.astream({
            "input": user_input,
            "chat_history": chat_history,
            "context": context,
        }):
            token = chunk.content if hasattr(chunk, "content") else str(chunk)
            full_response += token
            yield token

        memory.add_user_message(user_input)
        memory.add_ai_message(full_response)

    return stream, session_id


def get_session_manager() -> SessionManager:
    return _session_manager
