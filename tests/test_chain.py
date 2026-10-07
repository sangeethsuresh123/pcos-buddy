import asyncio

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda

from backend.chat import chain

FAKE_RESPONSE = "Fake answer"


def _fake_llm():
    return RunnableLambda(lambda _: FAKE_RESPONSE)


def test_create_chat_chain_generates_session_id(monkeypatch):
    monkeypatch.setattr(chain, "_get_llm", _fake_llm)

    invoke, session_id = chain.create_chat_chain()
    assert session_id and isinstance(session_id, str)

    response, returned_session = invoke("hello")
    assert response == FAKE_RESPONSE
    assert returned_session == session_id


def test_create_chat_chain_uses_session_and_stores_memory(monkeypatch):
    monkeypatch.setattr(chain, "_get_llm", _fake_llm)

    invoke, session_id = chain.create_chat_chain("sess-chat-history")
    assert session_id == "sess-chat-history"

    invoke("hello there")

    history = chain.get_session_manager().get_memory("sess-chat-history").get_history()
    assert len(history) == 2
    assert isinstance(history[0], HumanMessage)
    assert history[0].content == "hello there"
    assert isinstance(history[1], AIMessage)
    assert history[1].content == FAKE_RESPONSE


def test_create_chat_chain_naive_does_not_retrieve_documents(monkeypatch):
    monkeypatch.setattr(chain, "_get_llm", _fake_llm)
    monkeypatch.setattr(chain, "get_pcos_retriever", lambda: (_ for _ in ()).throw(AssertionError("must not call retriever")))

    invoke, _ = chain.create_chat_chain("sess-chat-naive")
    response, _ = invoke("hi")
    assert response == FAKE_RESPONSE


class _FakeRetriever:
    def __init__(self, docs):
        self.docs = docs
        self.queries = []

    def invoke(self, query):
        self.queries.append(query)
        return self.docs


def test_create_rag_chain_returns_docs_and_session(monkeypatch):
    monkeypatch.setattr(chain, "_get_llm", _fake_llm)
    docs = [Document(page_content="PCOS facts", metadata={"source": "pcos.pdf"})]
    retriever = _FakeRetriever(docs)
    monkeypatch.setattr(chain, "get_pcos_retriever", lambda: retriever)

    invoke, session_id = chain.create_rag_chain("sess-rag")
    response, returned_docs, returned_session = invoke("what is PCOS?")

    assert session_id == "sess-rag"
    assert retriever.queries == ["what is PCOS?"]
    assert response == FAKE_RESPONSE
    assert returned_docs == docs
    assert returned_session == session_id


def test_create_rag_chain_injects_context_into_prompt(monkeypatch):
    captured = {}

    def llm_recording_context():
        def func(messages):
            captured["content"] = messages.to_string()
            return FAKE_RESPONSE

        return RunnableLambda(func)

    monkeypatch.setattr(chain, "_get_llm", llm_recording_context)
    monkeypatch.setattr(
        chain,
        "get_pcos_retriever",
        lambda: _FakeRetriever([Document(page_content="CONTEXT_SNIPPET")]),
    )

    invoke, _ = chain.create_rag_chain("sess-rag-context")
    invoke("question")

    assert "CONTEXT_SNIPPET" in captured["content"]


def test_create_rag_chain_streaming(monkeypatch):
    monkeypatch.setattr(chain, "_get_llm", _fake_llm)
    monkeypatch.setattr(
        chain,
        "get_pcos_retriever",
        lambda: _FakeRetriever([Document(page_content="streaming context")]),
    )

    async def collect():
        stream_fn, session_id = await chain.create_rag_chain_streaming("sess-stream")
        chunks = []
        async for chunk in stream_fn("hello"):
            chunks.append(chunk)
        return chunks, session_id

    chunks, session_id = asyncio.run(collect())

    assert session_id == "sess-stream"
    assert "".join(chunks) == FAKE_RESPONSE

    history = chain.get_session_manager().get_memory("sess-stream").get_history()
    assert len(history) == 2
    assert history[0].content == "hello"
    assert history[1].content == FAKE_RESPONSE