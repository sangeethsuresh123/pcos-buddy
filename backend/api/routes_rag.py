from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from backend.config import settings
from backend.rag.loader import load_documents, split_documents
from backend.rag.vectorstore import add_documents, get_vectorstore

router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentCountResponse(BaseModel):
    count: int


class IngestResponse(BaseModel):
    message: str
    documents_added: int
    chunks_added: int


@router.get("/count", response_model=DocumentCountResponse)
async def document_count():
    vs = get_vectorstore()
    count = vs._collection.count()
    return DocumentCountResponse(count=count)


@router.post("/upload", response_model=IngestResponse)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    allowed_ext = {".pdf", ".txt", ".md"}
    import os
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {allowed_ext}",
        )

    save_dir = settings.knowledge_dir
    import os
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, file.filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        documents = load_documents(save_dir)
        chunks = split_documents(documents)
        added = add_documents(chunks)
        return IngestResponse(
            message=f"Successfully ingested {file.filename}",
            documents_added=len(documents),
            chunks_added=added,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest", response_model=IngestResponse)
async def ingest_all_documents():
    try:
        documents = load_documents()
        if not documents:
            return IngestResponse(
                message="No documents found in knowledge directory",
                documents_added=0,
                chunks_added=0,
            )
        chunks = split_documents(documents)
        added = add_documents(chunks)
        return IngestResponse(
            message=f"Ingested {len(documents)} documents",
            documents_added=len(documents),
            chunks_added=added,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_documents():
    vs = get_vectorstore()
    vs._collection.delete(where={})
    return {"message": "All documents cleared from vector store"}
