import pytest

from src.schemas import (
    RequirementReadinessRecommendation,
    RequirementReadinessReport,
    ScoreBreakdown,
)


def _sample_report_payload(*, breakdown_scores: dict = None, model_score: int = None) -> dict:
    """
    Create a sample report payload.
    
    Args:
        breakdown_scores: Dict of dimension scores (0-100 each)
        model_score: The readiness_score the model claims (may differ from calculated)
    """
    if breakdown_scores is None:
        breakdown_scores = {
            "clarity": 80,
            "acceptance_criteria_quality": 80,
            "testability": 80,
            "edge_case_coverage": 80,
            "dependency_clarity": 80,
            "risk_visibility": 80,
            "observability_expectations": 80,
        }
    
    # Calculate expected weighted score
    breakdown = ScoreBreakdown(**breakdown_scores)
    calculated = breakdown.weighted_score()
    
    payload: dict = {
        "original_requirement": "The system should do X.",
        "summary": "Build X for users so they can achieve Y.",
        "rewritten_user_story": "As a user, I want X, so that Y.",
        "readiness_score": model_score if model_score is not None else calculated,
        "score_breakdown": breakdown_scores,
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
    return payload


def test_schema_validation_success_and_derived_recommendation():
    """Test that score is calculated from breakdown and recommendation is derived."""
    data = _sample_report_payload()
    report = RequirementReadinessReport(**data)
    # All dimensions at 80 -> weighted score = 80 -> READY (80+ is READY)
    assert report.readiness_score == 80
    assert report.recommendation == RequirementReadinessRecommendation.READY


def test_mismatched_model_score_is_adjusted():
    """Test that mismatched model score is adjusted to calculated value with warning."""
    data = _sample_report_payload(model_score=99)  # Model claims 99, breakdown gives 80
    report = RequirementReadinessReport(**data)
    
    # Score should be calculated from breakdown, not model value
    assert report.readiness_score == 80
    
    # Warning should be added to human_review_notes
    assert any("Score adjusted" in note for note in report.human_review_notes)
    assert any("model provided 99" in note for note in report.human_review_notes)


def test_out_of_range_model_score_is_handled():
    """Test that out-of-range model scores are handled gracefully."""
    data = _sample_report_payload(model_score=150)  # Invalid score
    report = RequirementReadinessReport(**data)
    
    # Should not raise, should use calculated score
    assert report.readiness_score == 80
    assert any("Score adjusted" in note for note in report.human_review_notes)


def test_negative_model_score_is_handled():
    """Test that negative model scores are handled gracefully."""
    data = _sample_report_payload(model_score=-10)
    report = RequirementReadinessReport(**data)
    
    assert report.readiness_score == 80
    assert any("Score adjusted" in note for note in report.human_review_notes)


def test_out_of_range_breakdown_scores_are_clamped():
    """Test that out-of-range breakdown scores are clamped to 0-100."""
    breakdown_scores = {
        "clarity": 150,  # Over 100
        "acceptance_criteria_quality": -20,  # Negative
        "testability": 80,
        "edge_case_coverage": 80,
        "dependency_clarity": 200,  # Way over
        "risk_visibility": 80,
        "observability_expectations": 80,
    }
    data = _sample_report_payload(breakdown_scores=breakdown_scores)
    report = RequirementReadinessReport(**data)
    
    # Verify clamping occurred
    assert report.score_breakdown.clarity == 100  # Clamped from 150
    assert report.score_breakdown.acceptance_criteria_quality == 0  # Clamped from -20
    assert report.score_breakdown.dependency_clarity == 100  # Clamped from 200
    
    # Score should be calculated from clamped values
    # clarity=100, ac_quality=0, testability=80, edge=80, dep=100, risk=80, obs=80
    # = (100/100)*20 + (0/100)*20 + (80/100)*20 + (80/100)*15 + (100/100)*10 + (80/100)*10 + (80/100)*5
    # = 20 + 0 + 16 + 12 + 10 + 8 + 4 = 70
    assert report.readiness_score == 70


def test_missing_breakdown_scores_use_defaults():
    """Test that missing breakdown fields use default value of 0."""
    breakdown_scores = {
        "clarity": 100,
        # Other fields missing - should default to 0
    }
    data = _sample_report_payload(breakdown_scores=breakdown_scores)
    report = RequirementReadinessReport(**data)
    
    # Only clarity contributes: (100/100)*20 = 20
    assert report.readiness_score == 20
    assert report.recommendation == RequirementReadinessRecommendation.NOT_READY


def test_recommendation_derived_from_calculated_score():
    """Test that recommendation is always derived from final calculated score."""
    # High scores -> READY
    high_scores = {k: 90 for k in ScoreBreakdown.WEIGHTS.keys()}
    data = _sample_report_payload(breakdown_scores=high_scores, model_score=10)
    report = RequirementReadinessReport(**data)
    assert report.readiness_score == 90
    assert report.recommendation == RequirementReadinessRecommendation.READY
    
    # Low scores -> NOT_READY
    low_scores = {k: 30 for k in ScoreBreakdown.WEIGHTS.keys()}
    data = _sample_report_payload(breakdown_scores=low_scores, model_score=99)
    report = RequirementReadinessReport(**data)
    assert report.readiness_score == 30
    assert report.recommendation == RequirementReadinessRecommendation.NOT_READY


def test_no_warning_when_score_matches():
    """Test that no warning is added when model score matches calculated."""
    data = _sample_report_payload()  # model_score will match calculated
    initial_notes = data["human_review_notes"].copy()
    report = RequirementReadinessReport(**data)
    
    # No score adjustment warning should be added
    adjustment_warnings = [n for n in report.human_review_notes if "Score adjusted" in n]
    assert len(adjustment_warnings) == 0
    
    # Original notes should still be present
    assert "Assumption: Single-tenant app." in report.human_review_notes


@pytest.mark.parametrize(
    "score,expected",
    [
        # 80-100: READY
        (100, RequirementReadinessRecommendation.READY),
        (80, RequirementReadinessRecommendation.READY),
        # 60-79: NEEDS_REVIEW
        (79, RequirementReadinessRecommendation.NEEDS_REVIEW),
        (60, RequirementReadinessRecommendation.NEEDS_REVIEW),
        # 40-59: NEEDS_REFINEMENT
        (59, RequirementReadinessRecommendation.NEEDS_REFINEMENT),
        (40, RequirementReadinessRecommendation.NEEDS_REFINEMENT),
        # 0-39: NOT_READY
        (39, RequirementReadinessRecommendation.NOT_READY),
        (0, RequirementReadinessRecommendation.NOT_READY),
    ],
)
def test_recommendation_thresholds(score: int, expected: RequirementReadinessRecommendation):
    """Test recommendation threshold boundaries with new calibration."""
    assert RequirementReadinessReport.derive_recommendation(score) == expected


def test_weighted_score_calculation():
    """Test that weighted score calculation follows the specified weights."""
    # Perfect scores in all dimensions
    perfect = ScoreBreakdown(
        clarity=100,
        acceptance_criteria_quality=100,
        testability=100,
        edge_case_coverage=100,
        dependency_clarity=100,
        risk_visibility=100,
        observability_expectations=100,
    )
    assert perfect.weighted_score() == 100
    
    # Zero scores in all dimensions
    zero = ScoreBreakdown()
    assert zero.weighted_score() == 0
    
    # Only clarity at 100 (weight=20)
    clarity_only = ScoreBreakdown(clarity=100)
    assert clarity_only.weighted_score() == 20
    
    # 50% in all dimensions
    half = ScoreBreakdown(
        clarity=50,
        acceptance_criteria_quality=50,
        testability=50,
        edge_case_coverage=50,
        dependency_clarity=50,
        risk_visibility=50,
        observability_expectations=50,
    )
    assert half.weighted_score() == 50
