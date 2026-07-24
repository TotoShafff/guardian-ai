"""add workflow output ordering and decision links

Revision ID: 7d72d643d597
Revises: 4e6dd0965bd5
Create Date: 2026-07-24 15:13:38.023627

Adds an explicit `order_index` column to every table whose rows must be
reconstructed back into an ordered domain tuple (`evidence`, `findings`,
`finding_evidence`, `fix_attempts`, `validation_results`), and two new
association tables — `decision_findings` and `decision_fix_attempts` —
recording exactly which findings (and whether each is blocking) and which
fix attempts a `Decision` consolidated, in order. No existing table is
dropped or renamed, and the `reviews` table/migration history is untouched.

`order_index` columns are added as `NOT NULL` with a `0` server default so
the migration applies cleanly even against a non-empty table; application
code always supplies an explicit, meaningful `order_index` when inserting
new rows (see `app.persistence.repositories.ReviewRepository.
save_workflow_output`).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d72d643d597"
down_revision: str | Sequence[str] | None = "4e6dd0965bd5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Tables that gain an `order_index` column in this migration, and whether
#: an existing table needs `batch_alter_table` (used for every one of them,
#: for portable `ADD COLUMN`/`DROP COLUMN` across PostgreSQL and SQLite).
_ORDERED_TABLES = (
    "evidence",
    "findings",
    "finding_evidence",
    "fix_attempts",
    "validation_results",
)


def upgrade() -> None:
    """Add ordering columns and the decision association tables."""
    for table_name in _ORDERED_TABLES:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "order_index",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                )
            )

    for table_name in _ORDERED_TABLES:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                "order_index",
                server_default=None,
            )

    op.create_table(
        "decision_findings",
        sa.Column("decision_review_id", sa.UUID(), nullable=False),
        sa.Column("finding_id", sa.UUID(), nullable=False),
        sa.Column("is_blocking", sa.Boolean(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["decision_review_id"],
            ["decisions.review_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["finding_id"],
            ["findings.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "decision_review_id",
            "finding_id",
        ),
    )

    op.create_table(
        "decision_fix_attempts",
        sa.Column("decision_review_id", sa.UUID(), nullable=False),
        sa.Column("fix_attempt_id", sa.UUID(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["decision_review_id"],
            ["decisions.review_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["fix_attempt_id"],
            ["fix_attempts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "decision_review_id",
            "fix_attempt_id",
        ),
    )


def downgrade() -> None:
    """Drop the decision association tables and the ordering columns."""
    op.drop_table("decision_fix_attempts")
    op.drop_table("decision_findings")

    for table_name in reversed(_ORDERED_TABLES):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column("order_index")
