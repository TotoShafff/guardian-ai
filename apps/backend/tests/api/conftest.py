"""Test setup for the api package.

Importing `app.api.main` (directly, or via `app.api.reviews` /
`app.api.dependencies`) transitively imports `app.persistence.database`,
which builds its SQLAlchemy engine from `get_settings()` at import time, so
a syntactically valid `DATABASE_URL` must be present *before* that happens.
No real database connection is required for these tests: SQLAlchemy
engines connect lazily, and every test here overrides `get_review_service`
so the real session/repository/graph dependency chain is never exercised.
"""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://guardian:guardian@localhost:5432/guardian_test",
)
