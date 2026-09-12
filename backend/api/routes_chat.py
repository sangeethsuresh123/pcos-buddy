from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.chat.chain import (
    create_chat_chain,
    create_rag_chain,
    create_rag_chain_streaming,
    get_session_manager,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    session_id: str | None = None
    use_rag: bool = True


class ChatResponse(BaseModel):
    response: str
    session_id: str
    sources: list[str] = []


class SessionListResponse(BaseModel):
    sessions: list[str]


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        if request.use_rag:
            invoke, session_id = create_rag_chain(request.session_id)
            response, docs, session_id = invoke(request.message)
            sources = [
                doc.metadata.get("source", "unknown")
                for doc in docs
                if hasattr(doc, "metadata")
            ]
        else:
            invoke, session_id = create_chat_chain(request.session_id)
            response, session_id = invoke(request.message)
            sources = []

        return ChatResponse(
            response=response,
            session_id=session_id,
            sources=sources,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream")
async def chat_stream(message: str, session_id: str | None = None):
    from fastapi.responses import StreamingResponse

    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    stream_fn, session_id = await create_rag_chain_streaming(session_id)

    async def event_generator():
        async for chunk in stream_fn(message):
            yield f"data: {chunk}\n\n"
        yield f"data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "X-Session-Id": session_id,
            "Cache-Control": "no-cache",
        },
    )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions():
    manager = get_session_manager()
    return SessionListResponse(sessions=manager.list_sessions())


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    manager = get_session_manager()
    if manager.delete_session(session_id):
        return {"message": "Session deleted"}
    raise HTTPException(status_code=404, detail="Session not found")
