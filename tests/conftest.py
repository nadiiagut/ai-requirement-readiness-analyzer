import pytest


@pytest.fixture()
def sample_report_payload() -> dict:
    # Choose a score where the derived recommendation is deterministic.
    score = 80
    return {
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
