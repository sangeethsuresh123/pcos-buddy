import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.api.routes_chat import router as chat_router
from backend.api.routes_ml import router as ml_router
from backend.api.routes_rag import router as rag_router
from backend.config import settings

app = FastAPI(
    title="PCOS Patient Assistance Chatbot",
    description="AI-powered chatbot for PCOS patient support with RAG and ML prediction",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(ml_router)
app.include_router(rag_router)


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "model": settings.openrouter_model,
    }


templates_dir = Path(__file__).parent / "templates"
if templates_dir.exists():
    app.mount("/", StaticFiles(directory=str(templates_dir), html=True), name="static")


def main():
    uvicorn.run(
        "backend.app:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
