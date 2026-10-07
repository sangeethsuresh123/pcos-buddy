import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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


class _Constraint:
    def __init__(self):
        self.low = None
        self.high = None
        self.low_exclusive = False
        self.high_exclusive = False


_CONSTRAINT_TYPES = {
    "greater_than_equal": ("low", False),
    "greater_than": ("low", True),
    "less_than_equal": ("high", False),
    "less_than": ("high", True),
}

_FIELD_ERROR_TYPES = {
    "missing": "is required",
    "float_parsing": "must be a number",
    "int_parsing": "must be a number",
    "float_type": "must be a number",
    "int_type": "must be a number",
}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    by_field: dict[str, list[dict]] = {}
    for err in exc.errors():
        field = ".".join(str(part) for part in err["loc"] if part != "body")
        by_field.setdefault(field, []).append(err)

    details = []
    for field, errors in sorted(by_field.items()):
        name = field or "request"
        constraint = _Constraint()
        generic = []

        for e in errors:
            err_type = e.get("type", "")
            ctx = e.get("ctx") or {}

            if err_type in _CONSTRAINT_TYPES:
                bound, exclusive = _CONSTRAINT_TYPES[err_type]
                value = ctx.get("ge") or ctx.get("gt") or ctx.get("le") or ctx.get("lt")
                setattr(constraint, bound, value)
                if bound == "low":
                    constraint.low_exclusive = exclusive
                else:
                    constraint.high_exclusive = exclusive
            elif err_type in _FIELD_ERROR_TYPES:
                generic.append(f"{name} {_FIELD_ERROR_TYPES[err_type]}")
            else:
                generic.append(f"{name}: {e.get('msg', 'invalid value')}")

        if constraint.low is not None and constraint.high is not None:
            low = f"{'>' if constraint.low_exclusive else '>='} {constraint.low}"
            high = f"{'<' if constraint.high_exclusive else '<='} {constraint.high}"
            generic.append(f"{name} must satisfy {low} and {high}")
        elif constraint.low is not None:
            op = ">" if constraint.low_exclusive else ">="
            generic.append(f"{name} must be {op} {constraint.low}")
        elif constraint.high is not None:
            op = "<" if constraint.high_exclusive else "<="
            generic.append(f"{name} must be {op} {constraint.high}")

        details.extend(generic)

    return JSONResponse(
        status_code=422,
        content={"detail": " ".join(details) or "Invalid request body."},
    )


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
