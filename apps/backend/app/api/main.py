"FastAPI application entry point."

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

# Allows the local Vite dev server (`apps/frontend`) to call this API from the
# browser. Limited to local dev origins only; the Docker Compose setup will
# serve the built frontend from the same origin as the API in production, at
# which point cross-origin requests will not be involved (see `docs/ROADMAP.md`
# Phase 6).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(reviews_router, prefix="/api")


@app.get("/")
def read_root() -> dict[str, str]:
    """Identify the running service and its version."""
    return {"service": "guardian-ai-backend", "version": app.version}
