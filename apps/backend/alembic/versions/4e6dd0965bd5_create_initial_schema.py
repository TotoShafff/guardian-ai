"""create initial schema

Revision ID: 4e6dd0965bd5
Revises:
Create Date: 2026-07-24 11:00:49.031745

Creates the seven tables that back the domain models in
`app.domain.models` / ORM models in `app.persistence.models`, as described
in `docs/ARCHITECTURE.md` Section 12: `reviews`, `evidence`, `findings`,
`finding_evidence`, `fix_attempts`, `validation_results`, `decisions`.

Tables are created in dependency order (parents before children) and
dropped in reverse dependency order, so the migration applies and reverts
cleanly regardless of foreign key enforcement.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4e6dd0965bd5"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all Guardian AI tables."""
    op.create_table(
        "reviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("target_reference", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "approved",
                "blocked",
                "failed",
                name="review_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "evidence",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("review_id", sa.UUID(), nullable=False),
        sa.Column(
            "source",
            sa.Enum(
                "llm",
                "ruff",
                "mypy",
                "pytest",
                "eslint",
                "tsc",
                "vitest",
                name="evidence_source",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum(
                "blocking",
                "non_blocking",
                "info",
                name="evidence_severity",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("line_start", sa.Integer(), nullable=True),
        sa.Column("line_end", sa.Integer(), nullable=True),
        sa.Column("suggested_fix", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_evidence_confidence_range",
        ),
        sa.CheckConstraint(
            "line_end IS NULL OR line_end > 0",
            name="ck_evidence_line_end_positive",
        ),
        sa.CheckConstraint(
            "line_start IS NULL OR line_end IS NULL OR line_end >= line_start",
            name="ck_evidence_line_end_gte_line_start",
        ),
        sa.CheckConstraint(
            "line_start IS NULL OR line_start > 0",
            name="ck_evidence_line_start_positive",
        ),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "findings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("review_id", sa.UUID(), nullable=False),
        sa.Column(
            "severity",
            sa.Enum(
                "blocking",
                "non_blocking",
                "info",
                name="evidence_severity",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_fixable", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "finding_evidence",
        sa.Column("finding_id", sa.UUID(), nullable=False),
        sa.Column("evidence_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("finding_id", "evidence_id"),
    )
    op.create_table(
        "fix_attempts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("finding_id", sa.UUID(), nullable=False),
        sa.Column("patch", sa.Text(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "attempt_number >= 1", name="ck_fix_attempts_attempt_number_min"
        ),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "validation_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("fix_attempt_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "passed",
                "failed",
                "error",
                name="validation_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("tool", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["fix_attempt_id"], ["fix_attempts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "decisions",
        sa.Column("review_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "approved",
                "blocked",
                "failed",
                name="review_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("review_id"),
    )


def downgrade() -> None:
    """Drop all Guardian AI tables in reverse dependency order."""
    op.drop_table("decisions")
    op.drop_table("validation_results")
    op.drop_table("fix_attempts")
    op.drop_table("finding_evidence")
    op.drop_table("findings")
    op.drop_table("evidence")
    op.drop_table("reviews")
