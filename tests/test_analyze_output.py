"""Tests for /analyze endpoint output fields."""

import pytest

from src.api import (
    _compute_risk_level,
    _compute_qa_complexity,
    _compute_automation_candidate,
)
from src.schemas import (
    RequirementReadinessReport,
    ScoreBreakdown,
    SuggestedTestScenario,
)


def _create_report(
    product_risks: list = None,
    qa_risks: list = None,
    technical_risks: list = None,
    missing_information: list = None,
    edge_cases: list = None,
    suggested_test_scenarios: list = None,
    acceptance_criteria: list = None,
    clarification_questions: list = None,
    automation_candidates: list = None,
    testability: int = 70,
) -> RequirementReadinessReport:
    """Create a sample report for testing."""
    breakdown = ScoreBreakdown(
        clarity=70,
        acceptance_criteria_quality=70,
        testability=testability,
        edge_case_coverage=70,
        dependency_clarity=70,
        risk_visibility=70,
        observability_expectations=70,
    )
    
    scenarios = []
    if suggested_test_scenarios:
        for s in suggested_test_scenarios:
            scenarios.append(SuggestedTestScenario(
                title=s.get("title", "Test"),
                type=s.get("type", "functional"),
                priority=s.get("priority", "medium"),
                description=s.get("description", "Test description"),
            ))
    
    return RequirementReadinessReport(
        original_requirement="Test requirement",
        summary="Test summary",
        rewritten_user_story="As a user, I want X so that Y",
        readiness_score=70,
        score_breakdown=breakdown.model_dump(),
        missing_information=missing_information or [],
        acceptance_criteria=acceptance_criteria or [],
        edge_cases=edge_cases or [],
        product_risks=product_risks or [],
        qa_risks=qa_risks or [],
        technical_risks=technical_risks or [],
        suggested_test_scenarios=scenarios,
        automation_candidates=automation_candidates or [],
        clarification_questions=clarification_questions or [],
        human_review_notes=[],
    )


class TestComputeRiskLevel:
    """Tests for risk level computation."""
    
    def test_low_risk_no_risks(self):
        """Test Low risk when no risks identified."""
        report = _create_report()
        assert _compute_risk_level(report) == "Low"
    
    def test_medium_risk_few_risks(self):
        """Test Medium risk with 2-4 weighted risks."""
        report = _create_report(
            product_risks=["Risk 1"],
            qa_risks=["Risk 2"],
        )
        assert _compute_risk_level(report) == "Medium"
    
    def test_high_risk_several_risks(self):
        """Test High risk with 5-7 weighted risks."""
        report = _create_report(
            product_risks=["Risk 1", "Risk 2"],
            qa_risks=["Risk 3", "Risk 4"],
            technical_risks=["Risk 5"],  # Weighted 1.5x
        )
        assert _compute_risk_level(report) == "High"
    
    def test_critical_risk_many_risks(self):
        """Test Critical risk with 8+ weighted risks."""
        report = _create_report(
            product_risks=["Risk 1", "Risk 2", "Risk 3"],
            qa_risks=["Risk 4", "Risk 5"],
            technical_risks=["Risk 6", "Risk 7"],  # Weighted 1.5x = 3
        )
        assert _compute_risk_level(report) == "Critical"
    
    def test_missing_info_adds_risk(self):
        """Test that missing information increases risk level."""
        report = _create_report(
            product_risks=["Risk 1"],
            missing_information=["Missing 1", "Missing 2", "Missing 3", "Missing 4"],
        )
        # 1 product + 4*0.5 missing = 3 -> Medium
        assert _compute_risk_level(report) == "Medium"
    
    def test_technical_risks_weighted_higher(self):
        """Test that technical risks are weighted 1.5x."""
        report = _create_report(
            technical_risks=["Tech 1", "Tech 2", "Tech 3", "Tech 4"],  # 4 * 1.5 = 6
        )
        assert _compute_risk_level(report) == "High"


class TestComputeQAComplexity:
    """Tests for QA complexity computation."""
    
    def test_low_complexity_minimal_items(self):
        """Test Low complexity with minimal items."""
        report = _create_report()
        assert _compute_qa_complexity(report) == "Low"
    
    def test_medium_complexity(self):
        """Test Medium complexity with moderate items."""
        report = _create_report(
            edge_cases=["EC1", "EC2", "EC3"],  # 3 * 2 = 6
            acceptance_criteria=["AC1", "AC2"],  # 2
        )
        # Total = 8 -> Medium
        assert _compute_qa_complexity(report) == "Medium"
    
    def test_high_complexity_many_items(self):
        """Test High complexity with many items."""
        report = _create_report(
            edge_cases=["EC1", "EC2", "EC3", "EC4"],  # 4 * 2 = 8
            suggested_test_scenarios=[
                {"title": "S1"}, {"title": "S2"}, {"title": "S3"}
            ],  # 3 * 1.5 = 4.5
            acceptance_criteria=["AC1", "AC2", "AC3"],  # 3
        )
        # Total = 15.5 -> High
        assert _compute_qa_complexity(report) == "High"
    
    def test_edge_cases_weight_double(self):
        """Test that edge cases are weighted 2x."""
        report = _create_report(
            edge_cases=["EC1", "EC2", "EC3", "EC4"],  # 4 * 2 = 8
        )
        assert _compute_qa_complexity(report) == "Medium"
    
    def test_clarification_questions_add_complexity(self):
        """Test that clarification questions add complexity."""
        report = _create_report(
            edge_cases=["EC1", "EC2", "EC3"],  # 6
            clarification_questions=["Q1", "Q2", "Q3", "Q4"],  # 4 * 0.5 = 2
        )
        # Total = 8 -> Medium
        assert _compute_qa_complexity(report) == "Medium"


class TestComputeAutomationCandidate:
    """Tests for automation candidate computation."""
    
    def test_true_with_explicit_automation_candidates(self):
        """Test True when automation_candidates list is populated."""
        report = _create_report(
            automation_candidates=["Candidate 1"]
        )
        assert _compute_automation_candidate(report) is True
    
    def test_true_with_high_testability_and_ac(self):
        """Test True when testability >= 70 and >= 2 acceptance criteria."""
        report = _create_report(
            testability=75,
            acceptance_criteria=["AC1", "AC2", "AC3"],
        )
        assert _compute_automation_candidate(report) is True
    
    def test_true_with_multiple_test_scenarios(self):
        """Test True when >= 3 test scenarios exist."""
        report = _create_report(
            suggested_test_scenarios=[
                {"title": "S1"}, {"title": "S2"}, {"title": "S3"}
            ]
        )
        assert _compute_automation_candidate(report) is True
    
    def test_false_with_low_testability(self):
        """Test False when testability is low and no other indicators."""
        report = _create_report(
            testability=50,
            acceptance_criteria=["AC1"],
        )
        assert _compute_automation_candidate(report) is False
    
    def test_false_with_insufficient_ac(self):
        """Test False when testability is high but insufficient AC."""
        report = _create_report(
            testability=80,
            acceptance_criteria=["AC1"],  # Only 1 AC
        )
        assert _compute_automation_candidate(report) is False
    
    def test_false_with_few_scenarios(self):
        """Test False when only 2 test scenarios."""
        report = _create_report(
            testability=50,
            suggested_test_scenarios=[
                {"title": "S1"}, {"title": "S2"}
            ]
        )
        assert _compute_automation_candidate(report) is False


class TestClarificationCount:
    """Tests for clarification_count derivation."""
    
    def test_count_zero(self):
        """Test count is 0 when no questions."""
        report = _create_report(clarification_questions=[])
        assert len(report.clarification_questions) == 0
    
    def test_count_matches_list_length(self):
        """Test count matches list length."""
        report = _create_report(
            clarification_questions=["Q1", "Q2", "Q3", "Q4", "Q5"]
        )
        assert len(report.clarification_questions) == 5
    
    def test_count_single_question(self):
        """Test count with single question."""
        report = _create_report(
            clarification_questions=["What is the scope?"]
        )
        assert len(report.clarification_questions) == 1


class TestAnalyzeResponseIntegration:
    """Integration tests for full AnalyzeResponse output."""
    
    def test_all_new_fields_present(self):
        """Test that all new fields are computed for a report."""
        report = _create_report(
            product_risks=["Risk 1", "Risk 2"],
            qa_risks=["Risk 3"],
            edge_cases=["EC1", "EC2", "EC3"],
            clarification_questions=["Q1", "Q2", "Q3"],
            acceptance_criteria=["AC1", "AC2"],
            automation_candidates=["Auto 1"],
        )
        
        risk_level = _compute_risk_level(report)
        qa_complexity = _compute_qa_complexity(report)
        clarification_count = len(report.clarification_questions)
        automation_candidate = _compute_automation_candidate(report)
        
        assert risk_level in ["Low", "Medium", "High", "Critical"]
        assert qa_complexity in ["Low", "Medium", "High"]
        assert clarification_count == 3
        assert automation_candidate is True
    
    def test_risk_independent_of_readiness(self):
        """Test that risk_level is computed independently of readiness_score."""
        # High readiness but many risks
        report = _create_report(
            product_risks=["R1", "R2", "R3"],
            qa_risks=["R4", "R5"],
            technical_risks=["R6", "R7"],
        )
        report.readiness_score = 85  # High readiness
        
        risk_level = _compute_risk_level(report)
        # Should still be Critical due to risk count
        assert risk_level == "Critical"
