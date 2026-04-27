"""Tests for Jira comment formatting."""

import pytest

from src.jira_formatter import (
    _format_recommendation,
    _sanitize_issue_key,
    format_jira_comment,
)
from src.schemas import (
    RequirementReadinessRecommendation,
    RequirementReadinessReport,
    ScoreBreakdown,
)


def _create_sample_report(score: int = 75) -> RequirementReadinessReport:
    """Create a sample report for testing."""
    # Adjust breakdown to get approximately the desired score
    breakdown = ScoreBreakdown(
        clarity=score,
        acceptance_criteria_quality=score,
        testability=score,
        edge_case_coverage=score,
        dependency_clarity=score,
        risk_visibility=score,
        observability_expectations=score,
    )
    
    return RequirementReadinessReport(
        original_requirement="Test requirement",
        summary="Test summary",
        rewritten_user_story="As a user, I want X so that Y",
        readiness_score=score,
        score_breakdown=breakdown.model_dump(),
        missing_information=["Missing info 1"],
        acceptance_criteria=["AC-1: Given A, when B, then C"],
        edge_cases=["Edge case 1"],
        product_risks=["Product risk 1"],
        qa_risks=["QA risk 1"],
        technical_risks=["Technical risk 1"],
        suggested_test_scenarios=[],
        automation_candidates=[],
        clarification_questions=["Question 1?", "Question 2?"],
        human_review_notes=["Note 1"],
    )


class TestSanitizeIssueKey:
    """Tests for issue key sanitization."""
    
    def test_removes_equals_prefix(self):
        """Test that '=' prefix is removed from issue key."""
        assert _sanitize_issue_key("=NG-5") == "NG-5"
    
    def test_removes_equals_with_spaces(self):
        """Test that '=' prefix with surrounding spaces is handled."""
        assert _sanitize_issue_key(" =NG-5 ") == "NG-5"
    
    def test_preserves_valid_key(self):
        """Test that valid issue keys are preserved."""
        assert _sanitize_issue_key("PROJ-123") == "PROJ-123"
    
    def test_handles_none(self):
        """Test that None is handled."""
        assert _sanitize_issue_key(None) is None
    
    def test_handles_empty_string(self):
        """Test that empty string returns None."""
        assert _sanitize_issue_key("") is None
    
    def test_handles_only_equals(self):
        """Test that string with only '=' returns None."""
        assert _sanitize_issue_key("=") is None
    
    def test_multiple_equals(self):
        """Test that multiple '=' are stripped."""
        assert _sanitize_issue_key("==NG-5") == "NG-5"


class TestFormatRecommendation:
    """Tests for recommendation formatting."""
    
    def test_ready(self):
        assert _format_recommendation("ready") == "READY"
    
    def test_needs_review(self):
        assert _format_recommendation("needs_review") == "NEEDS REVIEW"
    
    def test_needs_refinement(self):
        assert _format_recommendation("needs_refinement") == "NEEDS REFINEMENT"
    
    def test_not_ready(self):
        assert _format_recommendation("not_ready") == "NOT READY"
    
    def test_unknown_falls_back(self):
        """Test that unknown values are converted to uppercase."""
        assert _format_recommendation("some_other") == "SOME OTHER"


class TestFormatJiraComment:
    """Tests for Jira comment formatting."""
    
    def test_title_without_issue_key(self):
        """Test that title is correct when no issue key provided."""
        report = _create_sample_report()
        comment = format_jira_comment(report)
        assert "AI Requirement Readiness Analysis\n" in comment
        assert " — " not in comment.split("\n")[0]
    
    def test_title_with_issue_key(self):
        """Test that title includes sanitized issue key."""
        report = _create_sample_report()
        comment = format_jira_comment(report, issue_key="PROJ-123")
        assert "AI Requirement Readiness Analysis — PROJ-123" in comment
    
    def test_title_with_equals_prefix_issue_key(self):
        """Test that '=' prefix is removed from issue key in title."""
        report = _create_sample_report()
        comment = format_jira_comment(report, issue_key="=NG-5")
        assert "AI Requirement Readiness Analysis — NG-5" in comment
        assert "=NG-5" not in comment
    
    def test_uses_real_newlines(self):
        """Test that comment uses real newlines, not escaped \\n."""
        report = _create_sample_report()
        comment = format_jira_comment(report)
        # Should have real newlines
        assert "\n" in comment
        # Should not have escaped newlines
        assert "\\n" not in comment
    
    def test_no_wiki_markup(self):
        """Test that comment doesn't contain Jira wiki markup."""
        report = _create_sample_report()
        comment = format_jira_comment(report)
        # No wiki markup
        assert "{panel" not in comment
        assert "{color" not in comment
        assert "h4." not in comment
        assert "h3." not in comment
    
    def test_includes_readiness_score(self):
        """Test that comment includes readiness score."""
        report = _create_sample_report(score=75)
        comment = format_jira_comment(report)
        assert "Readiness Score: 75/100" in comment
    
    def test_includes_recommendation(self):
        """Test that comment includes recommendation."""
        report = _create_sample_report(score=75)
        comment = format_jira_comment(report)
        # Score 75 -> NEEDS REVIEW
        assert "Recommendation: NEEDS REVIEW" in comment
    
    def test_includes_main_concerns(self):
        """Test that comment includes main concerns from risks."""
        report = _create_sample_report()
        comment = format_jira_comment(report)
        assert "Main Concerns:" in comment
        assert "Product risk 1" in comment
    
    def test_includes_clarification_questions(self):
        """Test that comment includes clarification questions."""
        report = _create_sample_report()
        comment = format_jira_comment(report)
        assert "Clarification Questions:" in comment
        assert "1. Question 1?" in comment
        assert "2. Question 2?" in comment
    
    def test_includes_qa_next_step(self):
        """Test that comment includes QA next step."""
        report = _create_sample_report()
        comment = format_jira_comment(report)
        assert "QA Next Step:" in comment
    
    def test_includes_ai_note(self):
        """Test that comment includes AI note."""
        report = _create_sample_report()
        comment = format_jira_comment(report)
        assert "AI Note:" in comment
    
    def test_qa_next_step_ready(self):
        """Test QA next step for score >= 80."""
        report = _create_sample_report(score=85)
        comment = format_jira_comment(report)
        assert "Ready for test planning." in comment
    
    def test_qa_next_step_needs_review(self):
        """Test QA next step for score 60-79."""
        report = _create_sample_report(score=65)
        comment = format_jira_comment(report)
        assert "Address clarification questions before test planning." in comment
    
    def test_qa_next_step_needs_refinement(self):
        """Test QA next step for score 40-59."""
        report = _create_sample_report(score=50)
        comment = format_jira_comment(report)
        assert "Significant gaps" in comment
    
    def test_qa_next_step_not_ready(self):
        """Test QA next step for score < 40."""
        report = _create_sample_report(score=30)
        comment = format_jira_comment(report)
        assert "Not ready — return to Product Owner" in comment


class TestAcceptanceCriteriaInComment:
    """Tests for acceptance criteria in Jira comment."""
    
    def test_includes_ac_from_report(self):
        """Test that AC from report is included."""
        report = _create_sample_report()
        comment = format_jira_comment(report)
        assert "Suggested Acceptance Criteria:" in comment
        assert "AC-1:" in comment or "Given A" in comment
    
    def test_includes_explicit_ac(self):
        """Test that explicit AC list is included."""
        report = _create_sample_report()
        ac_list = [
            {"id": "AC-1", "given": "user is logged in", "when": "user clicks save", "then": "data is saved"}
        ]
        comment = format_jira_comment(report, acceptance_criteria=ac_list)
        assert "Suggested Acceptance Criteria:" in comment
        assert "AC-1:" in comment
        assert "Given: user is logged in" in comment
        assert "When: user clicks save" in comment
        assert "Then: data is saved" in comment
    
    def test_explicit_ac_takes_precedence(self):
        """Test that explicit AC list takes precedence over report AC."""
        report = _create_sample_report()
        ac_list = [
            {"id": "AC-EXPLICIT", "given": "explicit given", "when": "explicit when", "then": "explicit then"}
        ]
        comment = format_jira_comment(report, acceptance_criteria=ac_list)
        assert "AC-EXPLICIT:" in comment
        assert "explicit given" in comment


class TestMissingOptionalFields:
    """Tests for handling missing optional fields."""
    
    def test_no_risks(self):
        """Test comment generation when no risks present."""
        report = RequirementReadinessReport(
            original_requirement="Test",
            summary="Test summary",
            rewritten_user_story="As a user...",
            readiness_score=80,
            score_breakdown={
                "clarity": 80,
                "acceptance_criteria_quality": 80,
                "testability": 80,
                "edge_case_coverage": 80,
                "dependency_clarity": 80,
                "risk_visibility": 80,
                "observability_expectations": 80,
            },
            missing_information=[],
            acceptance_criteria=[],
            edge_cases=[],
            product_risks=[],
            qa_risks=[],
            technical_risks=[],
            suggested_test_scenarios=[],
            automation_candidates=[],
            clarification_questions=[],
            human_review_notes=[],
        )
        comment = format_jira_comment(report)
        # Should not fail and should not have "Main Concerns:" section
        assert "AI Requirement Readiness Analysis" in comment
        assert "Main Concerns:" not in comment
    
    def test_no_clarification_questions(self):
        """Test comment generation when no clarification questions."""
        report = RequirementReadinessReport(
            original_requirement="Test",
            summary="Test summary",
            rewritten_user_story="As a user...",
            readiness_score=80,
            score_breakdown={
                "clarity": 80,
                "acceptance_criteria_quality": 80,
                "testability": 80,
                "edge_case_coverage": 80,
                "dependency_clarity": 80,
                "risk_visibility": 80,
                "observability_expectations": 80,
            },
            missing_information=[],
            acceptance_criteria=[],
            edge_cases=[],
            product_risks=["Risk 1"],
            qa_risks=[],
            technical_risks=[],
            suggested_test_scenarios=[],
            automation_candidates=[],
            clarification_questions=[],
            human_review_notes=[],
        )
        comment = format_jira_comment(report)
        assert "Clarification Questions:" not in comment
    
    def test_empty_ac_list(self):
        """Test that empty AC list doesn't break formatter."""
        report = _create_sample_report()
        report.acceptance_criteria = []
        comment = format_jira_comment(report, acceptance_criteria=[])
        assert "AI Requirement Readiness Analysis" in comment
