# PCOS Patient Assistance Chatbot

AI-powered chatbot for PCOS (Polycystic Ovary Syndrome) patients built with LangChain, OpenRouter, and FastAPI. Features RAG-based medical knowledge retrieval and machine learning-based risk prediction.

## Features

- **RAG Knowledge Base**: Answers grounded in PCOS medical documents (ChromaDB vector store)
- **Conversational Memory**: Remembers context within a session
- **ML Risk Prediction**: scikit-learn model predicts PCOS likelihood from patient symptoms/measurements
- **Web UI**: Built-in chat interface
- **REST API**: Ready for mobile app integration
- **Document Upload**: Add your own PDF/TXT/MD documents to the knowledge base

## Project Structure

```
chatbot/
├── backend/
│   ├── app.py                  # FastAPI application
│   ├── config.py               # Settings (env vars)
│   ├── chat/                   # LangChain chat chain, prompts, memory
│   ├── rag/                    # Document loading, vector store, retrieval
│   ├── ml/                     # PCOS prediction model
│   ├── api/                    # REST API routes
│   ├── knowledge/pcos_docs/    # Medical knowledge base (TXT/MD/PDF)
│   ├── templates/              # Web chat UI
│   └── chroma_db/              # Vector store (auto-created)
├── train_model.py              # Train the ML prediction model
├── setup_vectordb.py           # Index documents into vector store
├── dataset/                    # PCOS train.csv + test.csv (ML training data)
├── requirements.txt
└── .env.example
```

## Setup

### 1. Prerequisites
- Python 3.10+
- An OpenRouter API key from [openrouter.ai](https://openrouter.ai)

### 2. Install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env → add your OpenRouter API key
```

### 4. Optional: Index knowledge documents

Add your PCOS medical PDFs/TXT/MD files to `backend/knowledge/pcos_docs/`, then:

```bash
python setup_vectordb.py
```

Sample documents are already included.

### 5. Train the ML prediction model

Place `train.csv` and `test.csv` in the `dataset/` folder (all columns are used, except the `PCOS (Y/N)` label), then:

```bash
python train_model.py
```

### 6. Run the server

```bash
python -m backend.app
# or: uvicorn backend.app:app --reload
```

Open http://localhost:8000 in your browser.

> **Note**: Embeddings use ChromaDB's built-in ONNX `all-MiniLM-L6-v2` model
> (downloaded on first use to `~/.cache/chroma/`, no PyTorch needed).
> If the project lives on a network share (e.g. `\\wsl.localhost\...`), the
> ChromaDB SQLite store is automatically persisted to
> `%LOCALAPPDATA%\pcos-chatbot\chroma_db` instead — set `CHROMA_PERSIST_DIR`
> to a local path to control this.

## API Endpoints

### Health
- `GET /api/health` — Server health check

### Chat
- `POST /api/chat/` — Send a message (with optional `session_id` for memory)
  ```json
  {
    "message": "What foods should I eat with PCOS?",
    "session_id": null,
    "use_rag": true
  }
  ```
- `GET /api/chat/stream?message=...&session_id=...` — SSE streaming response
- `GET /api/chat/sessions` — List active sessions
- `DELETE /api/chat/sessions/{id}` — Delete a session

### ML Prediction
- `POST /api/ml/predict` — Predict PCOS risk. Body uses the exact CSV column names as keys (all 23 features):
  ```json
  {
    "Age (yrs)": 24,
    "Cycle(R/I)": 2,
    "Follicle No. (L)": 9,
    "Follicle No. (R)": 6,
    "...": "..."
  }
  ```
- `POST /api/ml/train` — Train the model on `dataset/train.csv`, evaluate on `dataset/test.csv`

### Knowledge Base
- `GET /api/documents/count` — Documents in vector store
- `POST /api/documents/upload` — Upload a PDF/TXT/MD file
- `POST /api/documents/ingest` — Re-index knowledge directory
- `DELETE /api/documents/clear` — Clear vector store

## Mobile App Integration

The FastAPI backend exposes a mobile-friendly REST API. All endpoints return JSON. Use `GET /api/chat/stream` for streaming responses or `POST /api/chat/` for one-shot.

## Configuration

All settings via `.env`:

| Variable | Default | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | — | Your OpenRouter key |
| `OPENROUTER_MODEL` | `google/gemma-3-27b-it` | Model to use |
| `CHROMA_PERSIST_DIR` | `./backend/chroma_db` | Vector store location |
| `KNOWLEDGE_DIR` | `./backend/knowledge/pcos_docs` | Knowledge base folder |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |

## Roadmap

- [x] RAG-based chat with memory
- [x] ML risk prediction
- [x] Web UI
- [x] REST API for mobile
- [ ] Web app framework (React/Next.js)
- [ ] Mobile app (React Native/Flutter)
- [ ] User authentication
- [ ] Conversation storage (database)
- [ ] More advanced ML models (deep learning)

## Disclaimer

This chatbot provides general health information and is **not a substitute for professional medical advice**. Always consult a qualified healthcare provider for diagnosis and treatment decisions.