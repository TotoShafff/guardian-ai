"""Metadata-only tests for the SQLAlchemy ORM persistence models.

These tests inspect the SQLAlchemy `Table`/`Mapper` metadata that is built
when `app.persistence.models` is imported. They do not open a database
connection, run migrations, or call `Base.metadata.create_all()` — table
and constraint definitions can be fully verified from the Python-side
metadata objects alone.
"""

from sqlalchemy import CheckConstraint, DateTime, Enum
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.persistence.database import Base
from app.persistence.models import (
    DecisionFindingModel,
    DecisionFixAttemptModel,
    DecisionModel,
    EvidenceModel,
    FindingEvidenceModel,
    FindingModel,
    FixAttemptModel,
    ReviewModel,
    ValidationResultModel,
)


def _foreign_key_targets(table_name: str) -> set[tuple[str, str, str]]:
    """Return (source_column, target_table, target_column) for each FK on a table."""
    table = Base.metadata.tables[table_name]
    return {
        (fk.parent.name, fk.column.table.name, fk.column.name)
        for fk in table.foreign_keys
    }


def _check_constraint_names(table_name: str) -> set[str]:
    table = Base.metadata.tables[table_name]
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint) and constraint.name is not None
    }


def test_expected_tables_exist() -> None:
    expected_tables = {
        "reviews",
        "evidence",
        "findings",
        "finding_evidence",
        "fix_attempts",
        "validation_results",
        "decisions",
        "decision_findings",
        "decision_fix_attempts",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_ordered_tables_have_an_order_index_column() -> None:
    ordered_tables = (
        "evidence",
        "findings",
        "finding_evidence",
        "fix_attempts",
        "validation_results",
        "decision_findings",
        "decision_fix_attempts",
    )

    for table_name in ordered_tables:
        table = Base.metadata.tables[table_name]
        assert table.columns["order_index"].nullable is False


def test_reviews_table_primary_key_and_columns() -> None:
    table = Base.metadata.tables["reviews"]

    assert table.primary_key.columns.keys() == ["id"]
    assert isinstance(table.columns["id"].type, PGUUID)
    assert isinstance(table.columns["status"].type, Enum)
    assert table.columns["status"].type.native_enum is False
    assert isinstance(table.columns["created_at"].type, DateTime)
    assert table.columns["created_at"].type.timezone is True
    assert table.columns["completed_at"].nullable is True


def test_evidence_table_primary_key_and_foreign_key() -> None:
    table = Base.metadata.tables["evidence"]

    assert table.primary_key.columns.keys() == ["id"]
    assert ("review_id", "reviews", "id") in _foreign_key_targets("evidence")
    assert table.columns["review_id"].nullable is False


def test_evidence_table_check_constraints_exist() -> None:
    constraint_names = _check_constraint_names("evidence")

    assert "ck_evidence_confidence_range" in constraint_names
    assert "ck_evidence_line_start_positive" in constraint_names
    assert "ck_evidence_line_end_positive" in constraint_names
    assert "ck_evidence_line_end_gte_line_start" in constraint_names


def test_findings_table_primary_key_and_foreign_key() -> None:
    table = Base.metadata.tables["findings"]

    assert table.primary_key.columns.keys() == ["id"]
    assert ("review_id", "reviews", "id") in _foreign_key_targets("findings")


def test_finding_evidence_association_table_has_composite_primary_key() -> None:
    table = Base.metadata.tables["finding_evidence"]

    assert set(table.primary_key.columns.keys()) == {"finding_id", "evidence_id"}
    targets = _foreign_key_targets("finding_evidence")
    assert ("finding_id", "findings", "id") in targets
    assert ("evidence_id", "evidence", "id") in targets


def test_fix_attempts_table_primary_key_foreign_key_and_constraint() -> None:
    table = Base.metadata.tables["fix_attempts"]

    assert table.primary_key.columns.keys() == ["id"]
    assert ("finding_id", "findings", "id") in _foreign_key_targets("fix_attempts")
    assert "ck_fix_attempts_attempt_number_min" in _check_constraint_names(
        "fix_attempts"
    )


def test_validation_results_table_primary_key_and_foreign_key() -> None:
    table = Base.metadata.tables["validation_results"]

    assert table.primary_key.columns.keys() == ["id"]
    assert ("fix_attempt_id", "fix_attempts", "id") in _foreign_key_targets(
        "validation_results"
    )


def test_decisions_table_primary_key_is_also_a_foreign_key() -> None:
    table = Base.metadata.tables["decisions"]

    assert table.primary_key.columns.keys() == ["review_id"]
    assert ("review_id", "reviews", "id") in _foreign_key_targets("decisions")


def test_decision_findings_table_composite_key_and_foreign_keys() -> None:
    table = Base.metadata.tables["decision_findings"]

    assert set(table.primary_key.columns.keys()) == {
        "decision_review_id",
        "finding_id",
    }
    targets = _foreign_key_targets("decision_findings")
    assert ("decision_review_id", "decisions", "review_id") in targets
    assert ("finding_id", "findings", "id") in targets
    assert table.columns["is_blocking"].nullable is False


def test_decision_fix_attempts_table_composite_key_and_foreign_keys() -> None:
    table = Base.metadata.tables["decision_fix_attempts"]

    assert set(table.primary_key.columns.keys()) == {
        "decision_review_id",
        "fix_attempt_id",
    }
    targets = _foreign_key_targets("decision_fix_attempts")
    assert ("decision_review_id", "decisions", "review_id") in targets
    assert ("fix_attempt_id", "fix_attempts", "id") in targets


def test_review_model_relationships() -> None:
    relationship_names = sa_inspect(ReviewModel).relationships.keys()

    assert set(relationship_names) == {"evidence", "findings", "decision"}


def test_finding_model_relationships() -> None:
    relationship_names = sa_inspect(FindingModel).relationships.keys()

    assert {"review", "evidence", "fix_attempts"}.issubset(relationship_names)


def test_fix_attempt_model_relationships() -> None:
    relationship_names = sa_inspect(FixAttemptModel).relationships.keys()

    assert {"finding", "validation_results"}.issubset(relationship_names)


def test_decision_model_relationships() -> None:
    relationship_names = sa_inspect(DecisionModel).relationships.keys()

    assert {"review", "finding_links", "fix_attempt_links"}.issubset(relationship_names)


def test_owned_child_relationships_cascade_delete_orphan() -> None:
    review_mapper = sa_inspect(ReviewModel)
    finding_mapper = sa_inspect(FindingModel)
    fix_attempt_mapper = sa_inspect(FixAttemptModel)
    decision_mapper = sa_inspect(DecisionModel)

    assert "delete-orphan" in review_mapper.relationships["evidence"].cascade
    assert "delete-orphan" in review_mapper.relationships["findings"].cascade
    assert "delete-orphan" in review_mapper.relationships["decision"].cascade
    assert "delete-orphan" in finding_mapper.relationships["fix_attempts"].cascade
    assert (
        "delete-orphan"
        in fix_attempt_mapper.relationships["validation_results"].cascade
    )
    assert "delete-orphan" in decision_mapper.relationships["finding_links"].cascade
    assert "delete-orphan" in decision_mapper.relationships["fix_attempt_links"].cascade


def test_ordered_relationships_declare_an_explicit_order_by() -> None:
    review_mapper = sa_inspect(ReviewModel)
    finding_mapper = sa_inspect(FindingModel)
    fix_attempt_mapper = sa_inspect(FixAttemptModel)
    decision_mapper = sa_inspect(DecisionModel)

    assert review_mapper.relationships["evidence"].order_by is not False
    assert review_mapper.relationships["findings"].order_by is not False
    assert finding_mapper.relationships["evidence"].order_by is not False
    assert finding_mapper.relationships["fix_attempts"].order_by is not False
    assert fix_attempt_mapper.relationships["validation_results"].order_by is not False
    assert decision_mapper.relationships["finding_links"].order_by is not False
    assert decision_mapper.relationships["fix_attempt_links"].order_by is not False


def test_all_orm_models_share_the_declarative_base() -> None:
    for model in (
        ReviewModel,
        EvidenceModel,
        FindingModel,
        FindingEvidenceModel,
        FixAttemptModel,
        ValidationResultModel,
        DecisionModel,
        DecisionFindingModel,
        DecisionFixAttemptModel,
    ):
        assert issubclass(model, Base)
