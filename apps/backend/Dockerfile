# Guardian AI backend — FastAPI + LangGraph + Alembic
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy install metadata first for better layer caching.
COPY pyproject.toml ./
# setuptools requires the README path declared in pyproject.toml.
RUN printf '%s\n' 'Guardian AI backend' > README.md

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# Runtime deps from pyproject.toml, plus [dev] for the deterministic tools
# invoked as subprocesses (`python -m ruff`, `python -m pytest`).
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[dev]"

EXPOSE 8000

# Migrations run at container start (not during image build).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.api.main:app --host 0.0.0.0 --port 8000"]
