"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.reviews import router as reviews_router

app = FastAPI(
    title="Guardian AI API",
    version="0.1.0",
    description=(
        "Backend API for Guardian AI, an agentic code-review system combining "
        "deterministic tool evidence with semantic analysis."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(reviews_router, prefix="/api")


@app.get("/")
def read_root() -> dict[str, str]:
    """Identify the running service and its version."""
    return {"service": "guardian-ai-backend", "version": app.version}