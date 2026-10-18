# PCOS Patient Assistance Chatbot

AI-powered chatbot for PCOS (Polycystic Ovary Syndrome) patients built with LangChain, OpenRouter, and FastAPI. Features RAG-based medical knowledge retrieval, machine learning-based risk prediction, symptom tracking with cycle analysis, and weight monitoring.

## Features

- **RAG Knowledge Base**: Answers grounded in PCOS medical documents (ChromaDB vector store)
- **Conversational Memory**: Remembers context within a session
- **ML Risk Prediction**: Gradient Boosting model predicts PCOS likelihood from 23 clinical features
- **Symptom & Cycle Tracker**: Daily logging of 20+ symptoms (0-10 scale), period flow, cycle day, lifestyle factors. Automatic cycle analysis: average length, next period prediction, phase detection (menstrual/follicular/luteal), and symptom patterns per phase
- **Weight Tracker**: Log weight, waist, hip measurements. Analytics: BMI, trends, milestones (5%/10% loss), WHtR, WHR, plateau detection
- **Web UI**: React + Vite + Tailwind-like CSS (no framework). Pages: Home, Risk Check, Symptoms, Weight, Chat Assistant
- **REST API**: Ready for mobile app integration
- **Document Upload**: Add your own PDF/TXT/MD documents to the knowledge base
- **Authentication**: Email/password + Google OAuth (cookie-based sessions)

## Project Structure

```
chatbot/
├── backend/
│   ├── app.py                  # FastAPI application
│   ├── config.py               # Settings (env vars)
│   ├── chat/                   # LangChain chat chain, prompts, memory
│   ├── rag/                    # Document loading, vector store, retrieval
│   ├── ml/                     # PCOS prediction model (GradientBoosting)
│   ├── symptoms/               # Symptom tracking + cycle analysis
│   ├── weight/                 # Weight tracking + analytics
│   ├── auth/                   # Auth (email/password, Google OAuth)
│   ├── api/                    # REST API routes
│   ├── knowledge/pcos_docs/    # Medical knowledge base (TXT/MD/PDF)
│   └── chroma_db/              # Vector store (auto-created)
├── train_model.py              # Train the ML prediction model
├── setup_vectordb.py           # Index documents into vector store
├── dataset/                    # PCOS train.csv + test.csv (ML training data)
├── frontend/                   # React + TypeScript + Vite
│   ├── src/
│   │   ├── pages/              # Home, Risk, Symptoms, Weight, Chat, Login
│   │   ├── components/         # UI components, icons, charts
│   │   ├── api.ts              # API client
│   │   └── auth.tsx            # Auth context
│   └── ...
├── requirements.txt
└── .env.example
```

## Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- An OpenRouter API key from [openrouter.ai](https://openrouter.ai)

### 2. Install dependencies

```bash
# Python
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
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

Place `train.csv` and `test.csv` in the `dataset/` folder (all columns used except `PCOS (Y/N)` label), then:

```bash
python train_model.py
```

### 6. Run the servers

```bash
# Terminal 1 - Backend
python -m backend.app
# or: uvicorn backend.app:app --reload

# Terminal 2 - Frontend dev server
cd frontend && npm run dev
```

Open http://localhost:8000 in your browser (production build served by FastAPI) or http://localhost:5173 (Vite dev server with HMR).

> **Note**: Embeddings use ChromaDB's built-in ONNX `all-MiniLM-L6-v2` model
> (downloaded on first use to `~/.cache/chroma/`, no PyTorch needed).
> If the project lives on a network share (e.g. `\\wsl.localhost\...`), the
> ChromaDB SQLite store is automatically persisted to
> `%LOCALAPPDATA%\pcos-chatbot\chroma_db` instead — set `CHROMA_PERSIST_DIR`
> to a local path to control this.

## API Endpoints

### Health
- `GET /api/health` — Server health check

### Authentication
- `POST /api/auth/register` — Register new user
- `POST /api/auth/login` — Login (sets cookie)
- `POST /api/auth/logout` — Logout
- `GET /api/auth/me` — Current user
- `GET /api/auth/config` — OAuth config

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
- `POST /api/ml/predict` — Predict PCOS risk. Body uses exact CSV column names as keys (23 features). Optional `use_symptoms=true` (default) auto-fills binary features from latest symptom entry.
- `POST /api/ml/train` — Train model on `dataset/train.csv`, evaluate on `dataset/test.csv`

### Symptom Tracking
- `GET /api/symptoms/entries` — List symptom entries (optional `?days=30`)
- `POST /api/symptoms/entries` — Create/upsert daily entry (20+ fields)
- `DELETE /api/symptoms/entries/{id}` — Delete entry
- `GET /api/symptoms/analysis` — Cycle analysis: avg length, next period, phase, symptom patterns per phase
- `GET /api/symptoms/ml-features` — Binary features derived from latest symptom entry
- `GET/PUT /api/symptoms/profile` — Typical cycle/period length, last period start
- `GET/POST /api/symptoms/cycle-events` — Manual cycle event logging

### Weight Tracking
- `GET/PUT /api/weight/profile` — Height (for BMI)
- `GET /api/weight/entries` — List weight entries
- `POST /api/weight/entries` — Create/upsert entry (date, weight, waist, hip, notes)
- `DELETE /api/weight/entries/{id}` — Delete entry
- `GET /api/weight/analytics` — Full analytics: BMI, trends, milestones, flags, chart series

### Knowledge Base
- `GET /api/documents/count` — Documents in vector store
- `POST /api/documents/upload` — Upload PDF/TXT/MD
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
| `WEIGHT_DB_PATH` | `./backend/data/weight.db` | Weight/symptom SQLite DB |
| `AUTH_DB_PATH` | `./backend/data/auth.db` | Auth SQLite DB |
| `AUTH_COOKIE_NAME` | `pcos_session` | Session cookie name |
| `SESSION_TTL_DAYS` | `30` | Session expiry |
| `GOOGLE_CLIENT_ID` | — | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | — | Google OAuth secret |
| `GOOGLE_REDIRECT_URI` | — | OAuth redirect URI |

## Roadmap

- [x] RAG-based chat with memory
- [x] ML risk prediction (Gradient Boosting)
- [x] Symptom tracking + cycle analysis
- [x] Weight tracking + analytics
- [x] Web UI (React + Vite)
- [x] REST API for mobile
- [x] User authentication
- [ ] Web app framework (React/Next.js)
- [ ] Mobile app (React Native/Flutter)
- [ ] Conversation storage (database)
- [ ] More advanced ML models (deep learning)

## Disclaimer

This chatbot provides general health information and is **not a substitute for professional medical advice**. Always consult a qualified healthcare provider for diagnosis and treatment decisions.