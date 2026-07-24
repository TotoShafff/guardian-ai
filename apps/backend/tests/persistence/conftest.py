"""Test setup for the persistence package.

`app.persistence.database` builds its SQLAlchemy engine from `get_settings()`
at import time, so a syntactically valid `DATABASE_URL` must be present
*before* that module is first imported. No real database connection is
required for these tests: SQLAlchemy engines connect lazily, so this URL is
never actually dialed.
"""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://guardian:guardian@localhost:5432/guardian_test",
)
