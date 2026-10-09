import pytest
from langchain_core.documents import Document

from backend.api import routes_chat, routes_ml, routes_rag
from backend.app import app
from backend.config import settings

from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def _authenticate(isolated_app_dbs):
    response = client.post(
        "/api/auth/register",
        json={"email": "api-tester@example.com", "password": "testpassword123"},
    )
    assert response.status_code == 201


def test_health_check():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_predict_returns_prediction(monkeypatch, sample_features):
    class FakePredictor:
        is_loaded = True

        def predict(self, features):
            assert set(features) == set(sample_features)
            return {
                "prediction": 1,
                "diagnosis": "Likely PCOS",
                "probability_pcos": 0.82,
                "probability_no_pcos": 0.18,
                "risk_level": "high",
                "recommendations": ["Consult a gynecologist"],
            }

    monkeypatch.setattr(routes_ml, "get_predictor", lambda: FakePredictor())

    resp = client.post("/api/ml/predict", json=sample_features)

    assert resp.status_code == 200
    body = resp.json()
    assert body["prediction"] == 1
    assert body["diagnosis"] == "Likely PCOS"
    assert body["risk_level"] == "high"
    assert body["recommendations"] == ["Consult a gynecologist"]


def test_predict_rejects_missing_field(monkeypatch, sample_features):
    monkeypatch.setattr(routes_ml, "get_predictor", lambda: None)

    body = dict(sample_features)
    del body["Age (yrs)"]

    resp = client.post("/api/ml/predict", json=body)

    assert resp.status_code == 422
    assert "Age (yrs) is required" in resp.json()["detail"]


def test_predict_rejects_non_numeric_field(monkeypatch, sample_features):
    monkeypatch.setattr(routes_ml, "get_predictor", lambda: None)

    body = dict(sample_features)
    body["Pulse rate(bpm)"] = "not-a-number"

    resp = client.post("/api/ml/predict", json=body)

    assert resp.status_code == 422
    assert "Pulse rate(bpm) must be a number" in resp.json()["detail"]


def test_predict_rejects_out_of_range_field(monkeypatch, sample_features):
    monkeypatch.setattr(routes_ml, "get_predictor", lambda: None)

    body = dict(sample_features)
    body["Age (yrs)"] = 5

    resp = client.post("/api/ml/predict", json=body)

    assert resp.status_code == 422
    assert "Age (yrs) must be >= 10" in resp.json()["detail"]


def test_predict_400_when_model_not_loaded(monkeypatch, sample_features):
    class UnloadedPredictor:
        is_loaded = False

    monkeypatch.setattr(routes_ml, "get_predictor", lambda: UnloadedPredictor())

    resp = client.post("/api/ml/predict", json=sample_features)

    assert resp.status_code == 400
    assert "Model not trained" in resp.json()["detail"]


def test_train_returns_metrics(monkeypatch):
    class FakePredictor:
        def train(self):
            return {
                "accuracy": 0.9,
                "precision": 0.8,
                "recall": 0.7,
                "f1_score": 0.75,
                "roc_auc": 0.85,
                "n_training_samples": 100,
                "n_test_samples": 30,
                "feature_importance": {"Age (yrs)": 0.5},
            }

    monkeypatch.setattr(routes_ml, "get_predictor", lambda: FakePredictor())

    resp = client.post("/api/ml/train")

    assert resp.status_code == 200
    body = resp.json()
    assert body["accuracy"] == 0.9
    assert body["roc_auc"] == 0.85
    assert "feature_importance" not in body


def test_chat_uses_rag_chain(monkeypatch):
    docs = [Document(page_content="ctx", metadata={"source": "pcos.pdf"})]

    def fake_invoke(message):
        return ("RAG response", docs, "sess-1")

    monkeypatch.setattr(
        routes_chat, "create_rag_chain", lambda session_id: (fake_invoke, "sess-1")
    )

    resp = client.post(
        "/api/chat/",
        json={"message": "hello", "session_id": "sess-1", "use_rag": True},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["response"] == "RAG response"
    assert body["session_id"] == "sess-1"
    assert body["sources"] == ["pcos.pdf"]


def test_chat_without_rag(monkeypatch):
    def fake_invoke(message):
        return ("Plain response", "sess-2")

    monkeypatch.setattr(
        routes_chat, "create_chat_chain", lambda session_id: (fake_invoke, "sess-2")
    )

    resp = client.post(
        "/api/chat/",
        json={"message": "hi", "use_rag": False},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["response"] == "Plain response"
    assert body["sources"] == []


def test_chat_propagates_chain_errors_as_500(monkeypatch):
    def boom(message):
        raise ValueError("boom")

    monkeypatch.setattr(
        routes_chat, "create_chat_chain", lambda session_id: (boom, "sess-3")
    )

    resp = client.post("/api/chat/", json={"message": "hi", "use_rag": False})

    assert resp.status_code == 500
    assert "boom" in resp.json()["detail"]


def test_chat_rejects_empty_message():
    resp = client.post("/api/chat/", json={"message": ""})

    assert resp.status_code == 422
    assert "at least 1 character" in resp.json()["detail"]


def test_chat_stream(monkeypatch):
    async def fake_create_streaming(session_id=None):
        async def stream(message):
            for chunk in ("a", "b"):
                yield chunk

        return stream, "stream-sid"

    monkeypatch.setattr(routes_chat, "create_rag_chain_streaming", fake_create_streaming)

    resp = client.get("/api/chat/stream", params={"message": "hello"})

    assert resp.status_code == 200
    assert resp.headers["x-session-id"] == "stream-sid"
    assert "data: a" in resp.text
    assert "data: b" in resp.text
    assert "data: [DONE]" in resp.text


def test_chat_stream_requires_message():
    resp = client.get("/api/chat/stream", params={"message": ""})

    assert resp.status_code == 400
    assert "Message is required" in resp.json()["detail"]


class FakeManager:
    def __init__(self):
        self.sessions = {"a": object()}

    def list_sessions(self):
        return list(self.sessions)

    def delete_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False


def test_sessions_list_and_delete(monkeypatch):
    monkeypatch.setattr(routes_chat, "get_session_manager", lambda: FakeManager())

    resp = client.get("/api/chat/sessions")
    assert resp.status_code == 200
    assert resp.json() == {"sessions": ["a"]}

    resp = client.delete("/api/chat/sessions/a")
    assert resp.status_code == 200
    assert resp.json() == {"message": "Session deleted"}

    resp = client.delete("/api/chat/sessions/missing")
    assert resp.status_code == 404


class FakeCollection:
    def __init__(self, count=42):
        self._count = count

    def count(self):
        return self._count


class FakeVectorStore:
    def __init__(self, count=42):
        self._collection = FakeCollection(count)


def test_document_count(monkeypatch):
    monkeypatch.setattr(routes_rag, "get_vectorstore", lambda: FakeVectorStore(42))

    resp = client.get("/api/documents/count")

    assert resp.status_code == 200
    assert resp.json() == {"count": 42}


def test_upload_ingests_document(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "knowledge_dir", str(tmp_path))
    monkeypatch.setattr(
        routes_rag,
        "load_documents",
        lambda directory=None: [Document(page_content="body", metadata={"source": "guide.txt"})],
    )
    monkeypatch.setattr(routes_rag, "split_documents", lambda docs: docs)
    monkeypatch.setattr(routes_rag, "add_documents", lambda chunks: len(chunks))

    resp = client.post(
        "/api/documents/upload",
        files={"file": ("guide.txt", b"content", "text/plain")},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["documents_added"] == 1
    assert body["chunks_added"] == 1
    assert "guide.txt" in body["message"]


def test_upload_rejects_unsupported_extension():
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("notes.exe", b"data", "application/octet-stream")},
    )

    assert resp.status_code == 400
    assert "Unsupported file type" in resp.json()["detail"]


def test_ingest_no_documents(monkeypatch):
    monkeypatch.setattr(routes_rag, "load_documents", lambda directory=None: [])

    resp = client.post("/api/documents/ingest")

    assert resp.status_code == 200
    assert resp.json() == {
        "message": "No documents found in knowledge directory",
        "documents_added": 0,
        "chunks_added": 0,
    }


def test_clear_documents(monkeypatch):
    class DeletingCollection:
        def __init__(self):
            self.deleted = []

        def delete(self, where=None):
            self.deleted.append(where)

    vs = FakeVectorStore(10)
    monkeypatch.setattr(routes_rag, "get_vectorstore", lambda: vs)
    vs._collection = DeletingCollection()

    resp = client.delete("/api/documents/clear")

    assert resp.status_code == 200
    assert vs._collection.deleted == [{}]
    assert resp.json() == {"message": "All documents cleared from vector store"}