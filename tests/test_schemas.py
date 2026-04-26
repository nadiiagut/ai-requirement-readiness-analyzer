import pytest

from src.schemas import (
    RequirementReadinessRecommendation,
    RequirementReadinessReport,
)


def _sample_report_payload(*, score: int, include_recommendation: bool = False) -> dict:
    payload: dict = {
        "original_requirement": "The system should do X.",
        "summary": "Build X for users so they can achieve Y.",
        "rewritten_user_story": "As a user, I want X, so that Y.",
        "readiness_score": score,
        "score_breakdown": {
            "clarity": score,
            "acceptance_criteria_quality": score,
            "testability": score,
            "edge_case_coverage": score,
            "dependency_clarity": score,
            "risk_visibility": score,
            "observability_expectations": score,
        },
        "missing_information": ["Unknown rate limits"],
        "acceptance_criteria": ["Given A, when B, then C"],
        "edge_cases": ["Network timeout"],
        "product_risks": ["User confusion"],
        "qa_risks": ["Hard to simulate provider downtime"],
        "technical_risks": ["Third-party API instability"],
        "suggested_test_scenarios": [
            {
                "title": "Happy path",
                "type": "functional",
                "priority": "high",
                "description": "Verify core flow works end-to-end.",
            }
        ],
        "automation_candidates": ["Smoke test for main flow"],
        "clarification_questions": ["What is the target user segment?"],
        "human_review_notes": ["Assumption: Single-tenant app."],
    }

    if include_recommendation:
        payload["recommendation"] = RequirementReadinessReport.derive_recommendation(score)
    return payload


def test_schema_validation_success_and_derived_recommendation():
    data = _sample_report_payload(score=80, include_recommendation=False)
    report = RequirementReadinessReport(**data)
    assert report.readiness_score == 80
    assert report.recommendation == RequirementReadinessRecommendation.NEEDS_REFINEMENT


def test_readiness_score_range_validation():
    data = _sample_report_payload(score=80)
    data["readiness_score"] = 101
    with pytest.raises(Exception):
        RequirementReadinessReport(**data)


def test_breakdown_weighted_score_must_match_readiness_score():
    data = _sample_report_payload(score=80)
    data["readiness_score"] = 10
    with pytest.raises(ValueError, match="weighted score"):
        RequirementReadinessReport(**data)


@pytest.mark.parametrize(
    "score,expected",
    [
        (85, RequirementReadinessRecommendation.READY),
        (84, RequirementReadinessRecommendation.NEEDS_REFINEMENT),
        (70, RequirementReadinessRecommendation.NEEDS_REFINEMENT),
        (69, RequirementReadinessRecommendation.HIGH_RISK),
        (50, RequirementReadinessRecommendation.HIGH_RISK),
        (49, RequirementReadinessRecommendation.NOT_READY),
    ],
)
def test_recommendation_thresholds(score: int, expected: RequirementReadinessRecommendation):
    assert RequirementReadinessReport.derive_recommendation(score) == expected
