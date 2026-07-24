"""SQLAlchemy ORM models for the Guardian AI backend.

Defines the persistence schema (`reviews`, `evidence`, `findings`,
`finding_evidence`, `fix_attempts`, `validation_results`, `decisions`)
described in `docs/ARCHITECTURE.md` Section 12, using SQLAlchemy 2.x typed
declarative mappings. This module only defines table structure — no
repositories, no conversion to/from the domain models in `app.domain.models`,
and no migrations (see `docs/ROADMAP.md` for when those are added).

Enum columns reuse the domain enums (`EvidenceSource`, `EvidenceSeverity`,
`ReviewStatus`, `ValidationStatus`) purely as the set of allowed string
values for storage; no domain validation logic is duplicated here beyond
the database constraints explicitly required for data integrity.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models import (
    EvidenceSeverity,
    EvidenceSource,
    ReviewStatus,
    ValidationStatus,
)
from app.persistence.database import Base


def _utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)


class ReviewModel(Base):
    """A single review request and its current lifecycle/outcome status."""

    __tablename__ = "reviews"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    target_reference: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(
            ReviewStatus,
            name="review_status",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    evidence: Mapped[list["EvidenceModel"]] = relationship(
        "EvidenceModel",
        back_populates="review",
        cascade="all, delete-orphan",
    )
    findings: Mapped[list["FindingModel"]] = relationship(
        "FindingModel",
        back_populates="review",
        cascade="all, delete-orphan",
    )
    decision: Mapped["DecisionModel | None"] = relationship(
        "DecisionModel",
        back_populates="review",
        uselist=False,
        cascade="all, delete-orphan",
    )


class EvidenceModel(Base):
    """A single, normalized piece of evidence about a code change."""

    __tablename__ = "evidence"
    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_evidence_confidence_range",
        ),
        CheckConstraint(
            "line_start IS NULL OR line_start > 0",
            name="ck_evidence_line_start_positive",
        ),
        CheckConstraint(
            "line_end IS NULL OR line_end > 0",
            name="ck_evidence_line_end_positive",
        ),
        CheckConstraint(
            "line_start IS NULL OR line_end IS NULL OR line_end >= line_start",
            name="ck_evidence_line_end_gte_line_start",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    review_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[EvidenceSource] = mapped_column(
        Enum(
            EvidenceSource,
            name="evidence_source",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    severity: Mapped[EvidenceSeverity] = mapped_column(
        Enum(
            EvidenceSeverity,
            name="evidence_severity",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str | None] = mapped_column(nullable=True)
    line_start: Mapped[int | None] = mapped_column(nullable=True)
    line_end: Mapped[int | None] = mapped_column(nullable=True)
    suggested_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    review: Mapped["ReviewModel"] = relationship(
        "ReviewModel", back_populates="evidence"
    )
    findings: Mapped[list["FindingModel"]] = relationship(
        "FindingModel",
        secondary="finding_evidence",
        back_populates="evidence",
    )


class FindingModel(Base):
    """A classified, human-facing finding derived from one or more evidence items."""

    __tablename__ = "findings"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    review_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    severity: Mapped[EvidenceSeverity] = mapped_column(
        Enum(
            EvidenceSeverity,
            name="evidence_severity",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_fixable: Mapped[bool] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    review: Mapped["ReviewModel"] = relationship(
        "ReviewModel", back_populates="findings"
    )
    evidence: Mapped[list["EvidenceModel"]] = relationship(
        "EvidenceModel",
        secondary="finding_evidence",
        back_populates="findings",
    )
    fix_attempts: Mapped[list["FixAttemptModel"]] = relationship(
        "FixAttemptModel",
        back_populates="finding",
        cascade="all, delete-orphan",
    )


class FindingEvidenceModel(Base):
    """Association table linking a finding to the evidence items it is based on."""

    __tablename__ = "finding_evidence"

    finding_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("findings.id", ondelete="CASCADE"),
        primary_key=True,
    )
    evidence_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="CASCADE"),
        primary_key=True,
    )


class FixAttemptModel(Base):
    """One bounded attempt to propose and validate a correction for a finding."""

    __tablename__ = "fix_attempts"
    __table_args__ = (
        CheckConstraint(
            "attempt_number >= 1", name="ck_fix_attempts_attempt_number_min"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    finding_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False,
    )
    patch: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_number: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    finding: Mapped["FindingModel"] = relationship(
        "FindingModel", back_populates="fix_attempts"
    )
    validation_results: Mapped[list["ValidationResultModel"]] = relationship(
        "ValidationResultModel",
        back_populates="fix_attempt",
        cascade="all, delete-orphan",
    )


class ValidationResultModel(Base):
    """Outcome of re-running one deterministic tool against a proposed fix."""

    __tablename__ = "validation_results"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    fix_attempt_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("fix_attempts.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[ValidationStatus] = mapped_column(
        Enum(
            ValidationStatus,
            name="validation_status",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    tool: Mapped[str] = mapped_column(nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    fix_attempt: Mapped["FixAttemptModel"] = relationship(
        "FixAttemptModel", back_populates="validation_results"
    )


class DecisionModel(Base):
    """The Decision Agent's consolidated output for a review."""

    __tablename__ = "decisions"

    review_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(
            ReviewStatus,
            name="review_status",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)

    review: Mapped["ReviewModel"] = relationship(
        "ReviewModel", back_populates="decision"
    )
