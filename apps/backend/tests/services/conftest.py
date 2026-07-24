"""Test setup for the services package.

`ReviewService` imports `ReviewRepository`, which transitively imports
`app.persistence.database` — that module builds its SQLAlchemy engine from
`get_settings()` at import time, so a syntactically valid `DATABASE_URL`
must be present *before* it is first imported. No real database connection
is required for these tests: SQLAlchemy engines connect lazily, so this URL
is never actually dialed, and `ReviewRepository` itself is always mocked.
"""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://guardian:guardian@localhost:5432/guardian_test",
)
