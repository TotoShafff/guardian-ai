"""add reviews.target_path

Revision ID: c3a91f2e8b04
Revises: 7d72d643d597
Create Date: 2026-07-25 15:40:00.000000

Persists the review request's `target_path` so the history listing can show
the project path without re-running a review. Existing rows receive an empty
string via the server default.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3a91f2e8b04"
down_revision: str | Sequence[str] | None = "7d72d643d597"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add `target_path` to `reviews`."""
    with op.batch_alter_table("reviews") as batch_op:
        batch_op.add_column(
            sa.Column(
                "target_path",
                sa.String(),
                nullable=False,
                server_default="",
            )
        )


def downgrade() -> None:
    """Remove `target_path` from `reviews`."""
    with op.batch_alter_table("reviews") as batch_op:
        batch_op.drop_column("target_path")
