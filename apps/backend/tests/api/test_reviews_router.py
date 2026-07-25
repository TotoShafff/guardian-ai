"""API tests for the reviews endpoints.

`get_review_service` is always overridden with a mocked `ReviewService`, so
these tests never run the real graph, never touch PostgreSQL/SQLite/
Docker, and require no Ruff/Pytest subprocess, network access, or AI
provider API key.
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_review_service
from app.api.main import app
from app.domain.models import (
    Decision,
    Evidence,
    EvidenceSeverity,
    EvidenceSource,
    Finding,
    FixAttempt,
    Review,
    ReviewStatus,
    ReviewSummary,
    ValidationResult,
    ValidationStatus,
)
from app.persistence.repositories import ReviewResult
from app.services.review_service import ReviewService

_VALID_REQUEST_BODY = {
    "target_reference": "feature/checkout-fix",
    "target_path": "./sample_project",
    "code": "def add(a, b):\n    return a + b\n",
}


@pytest.fixture
def mock_review_service() -> Iterator[MagicMock]:
    service = MagicMock(spec=ReviewService)
    app.dependency_overrides[get_review_service] = lambda: service
    try:
        yield service
    finally:
        app.dependency_overrides.pop(get_review_service, None)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def _make_review(**overrides: object) -> Review:
    defaults: dict[str, object] = {
        "target_reference": "feature/checkout-fix",
        "target_path": "./sample_project",
        "status": ReviewStatus.APPROVED,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "completed_at": datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return Review(**defaults)  # type: ignore[arg-type]


def _make_summary(**overrides: object) -> ReviewSummary:
    defaults: dict[str, object] = {
        "id": uuid4(),
        "target_reference": "feature/checkout-fix",
        "target_path": "./sample_project",
        "status": ReviewStatus.BLOCKED,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "completed_at": datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
        "blocking_findings_count": 2,
        "non_blocking_findings_count": 1,
    }
    defaults.update(overrides)
    return ReviewSummary(**defaults)  # type: ignore[arg-type]


def _make_review_result(review: Review) -> ReviewResult:
    evidence = Evidence(
        review_id=review.id,
        source=EvidenceSource.RUFF,
        severity=EvidenceSeverity.NON_BLOCKING,
        category="F401",
        message="unused import",
    )
    finding = Finding(
        review_id=review.id,
        evidence_ids=(evidence.id,),
        severity=EvidenceSeverity.NON_BLOCKING,
        title="Unused import",
        description="`os` is imported but never used",
        is_fixable=False,
    )
    fix_attempt = FixAttempt(
        finding_id=finding.id,
        patch="--- a\n+++ b\n",
        attempt_number=1,
        validation_results=(
            ValidationResult(
                status=ValidationStatus.PASSED, tool="mock_validator", message="ok"
            ),
        ),
    )
    decision = Decision(
        status=review.status,
        rationale="Revisión aprobada: 0 hallazgos bloqueantes y 0 no bloqueantes.",
        non_blocking_findings=(finding,),
        fix_attempts=(fix_attempt,),
    )
    return ReviewResult(
        review=review,
        evidence=(evidence,),
        findings=(finding,),
        fix_attempts=(fix_attempt,),
        decision=decision,
    )


def _make_empty_review_result(review: Review) -> ReviewResult:
    return ReviewResult(
        review=review, evidence=(), findings=(), fix_attempts=(), decision=None
    )


def test_post_reviews_returns_201(
    client: TestClient, mock_review_service: MagicMock
) -> None:
    review = _make_review()
    mock_review_service.run_review.return_value = _make_review_result(review)

    response = client.post("/api/reviews", json=_VALID_REQUEST_BODY)

    assert response.status_code == 201


@pytest.mark.parametrize("blank_field", ["target_reference", "target_path", "code"])
def test_post_reviews_rejects_blank_required_fields(
    client: TestClient, mock_review_service: MagicMock, blank_field: str
) -> None:
    body = dict(_VALID_REQUEST_BODY)
    body[blank_field] = "   "

    response = client.post("/api/reviews", json=body)

    assert response.status_code == 422
    mock_review_service.run_review.assert_not_called()


def test_post_reviews_response_contains_nested_workflow_output_fields(
    client: TestClient, mock_review_service: MagicMock
) -> None:
    review = _make_review()
    mock_review_service.run_review.return_value = _make_review_result(review)

    response = client.post("/api/reviews", json=_VALID_REQUEST_BODY)

    body = response.json()
    assert body["id"] == str(review.id)
    assert body["target_reference"] == review.target_reference
    assert body["status"] == review.status.value
    assert body["created_at"] is not None
    assert body["updated_at"] is not None
    assert len(body["evidence"]) == 1
    assert body["evidence"][0]["source"] == "ruff"
    assert len(body["findings"]) == 1
    assert body["findings"][0]["title"] == "Unused import"
    assert len(body["fix_attempts"]) == 1
    assert body["fix_attempts"][0]["validation_results"][0]["status"] == "passed"
    assert body["decision"]["status"] == review.status.value
    assert body["decision"]["non_blocking_findings"][0]["title"] == "Unused import"
    assert body["error"] is None


def test_post_reviews_delegates_to_the_service_with_request_fields(
    client: TestClient, mock_review_service: MagicMock
) -> None:
    review = _make_review()
    mock_review_service.run_review.return_value = _make_review_result(review)

    client.post("/api/reviews", json=_VALID_REQUEST_BODY)

    mock_review_service.run_review.assert_called_once_with(
        target_reference="feature/checkout-fix",
        target_path=Path("./sample_project"),
        code="def add(a, b):\n    return a + b\n",
    )


def test_get_review_returns_200_for_an_existing_review(
    client: TestClient, mock_review_service: MagicMock
) -> None:
    review = _make_review()
    mock_review_service.get_review.return_value = _make_empty_review_result(review)

    response = client.get(f"/api/reviews/{review.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(review.id)
    assert body["evidence"] == []
    assert body["findings"] == []
    assert body["fix_attempts"] == []
    assert body["decision"] is None


def test_get_review_returns_nested_persisted_workflow_output(
    client: TestClient, mock_review_service: MagicMock
) -> None:
    review = _make_review()
    mock_review_service.get_review.return_value = _make_review_result(review)

    response = client.get(f"/api/reviews/{review.id}")

    assert response.status_code == 200
    body = response.json()
    assert len(body["evidence"]) == 1
    assert body["evidence"][0]["source"] == "ruff"
    assert len(body["findings"]) == 1
    assert body["findings"][0]["title"] == "Unused import"
    assert len(body["fix_attempts"]) == 1
    assert body["fix_attempts"][0]["validation_results"][0]["status"] == "passed"
    assert body["decision"]["status"] == review.status.value
    assert body["decision"]["non_blocking_findings"][0]["title"] == "Unused import"


def test_get_review_returns_404_for_an_unknown_review(
    client: TestClient, mock_review_service: MagicMock
) -> None:
    mock_review_service.get_review.return_value = None
    unknown_id = uuid4()

    response = client.get(f"/api/reviews/{unknown_id}")

    assert response.status_code == 404


def test_get_review_delegates_to_the_service_with_the_review_id(
    client: TestClient, mock_review_service: MagicMock
) -> None:
    review = _make_review()
    mock_review_service.get_review.return_value = _make_empty_review_result(review)

    client.get(f"/api/reviews/{review.id}")

    mock_review_service.get_review.assert_called_once_with(review.id)
    mock_review_service.run_review.assert_not_called()


def test_get_reviews_returns_empty_history(
    client: TestClient, mock_review_service: MagicMock
) -> None:
    mock_review_service.list_reviews.return_value = ()

    response = client.get("/api/reviews")

    assert response.status_code == 200
    assert response.json() == {"reviews": []}
    mock_review_service.list_reviews.assert_called_once_with()
    mock_review_service.run_review.assert_not_called()


def test_get_reviews_returns_expected_summary_structure(
    client: TestClient, mock_review_service: MagicMock
) -> None:
    summary = _make_summary()
    mock_review_service.list_reviews.return_value = (summary,)

    response = client.get("/api/reviews")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "reviews": [
            {
                "id": str(summary.id),
                "target_reference": summary.target_reference,
                "target_path": summary.target_path,
                "status": "blocked",
                "created_at": "2026-01-01T00:00:00Z",
                "completed_at": "2026-01-01T00:01:00Z",
                "blocking_findings_count": 2,
                "non_blocking_findings_count": 1,
            }
        ]
    }
    mock_review_service.run_review.assert_not_called()


def test_get_historical_review_does_not_run_the_workflow(
    client: TestClient, mock_review_service: MagicMock
) -> None:
    review = _make_review()
    mock_review_service.get_review.return_value = _make_review_result(review)

    response = client.get(f"/api/reviews/{review.id}")

    assert response.status_code == 200
    mock_review_service.get_review.assert_called_once_with(review.id)
    mock_review_service.run_review.assert_not_called()


def test_get_and_post_review_share_the_same_response_schema_keys(
    client: TestClient, mock_review_service: MagicMock
) -> None:
    review = _make_review()
    result = _make_review_result(review)
    mock_review_service.run_review.return_value = result
    mock_review_service.get_review.return_value = result

    post_body = client.post("/api/reviews", json=_VALID_REQUEST_BODY).json()
    get_body = client.get(f"/api/reviews/{review.id}").json()

    assert set(post_body.keys()) == set(get_body.keys())
    assert set(post_body.keys()) == {
        "id",
        "target_reference",
        "status",
        "created_at",
        "updated_at",
        "evidence",
        "findings",
        "fix_attempts",
        "decision",
        "error",
    }
    assert post_body["evidence"][0].keys() == get_body["evidence"][0].keys()
    assert post_body["findings"][0].keys() == get_body["findings"][0].keys()
    assert post_body["fix_attempts"][0].keys() == get_body["fix_attempts"][0].keys()
    assert post_body["decision"].keys() == get_body["decision"].keys()
    mock_review_service.run_review.assert_called_once()
    mock_review_service.get_review.assert_called_once_with(review.id)


def test_get_reviews_preserves_descending_created_at_order(
    client: TestClient, mock_review_service: MagicMock
) -> None:
    newer = _make_summary(
        target_reference="newer",
        created_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    older = _make_summary(
        target_reference="older",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    mock_review_service.list_reviews.return_value = (newer, older)

    response = client.get("/api/reviews")

    assert response.status_code == 200
    references = [item["target_reference"] for item in response.json()["reviews"]]
    assert references == ["newer", "older"]
    mock_review_service.run_review.assert_not_called()
