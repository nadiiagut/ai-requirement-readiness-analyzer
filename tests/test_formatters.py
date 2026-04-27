"""Tests for Jira and Confluence formatters."""

import pytest

from src.jira_formatter import format_jira_comment
from src.confluence_formatter import format_confluence_page
from src.schemas import (
    RequirementReadinessReport,
    ScoreBreakdown,
    SuggestedTestScenario,
    TestScenarioType,
    TestScenarioPriority,
    RequirementReadinessRecommendation,
)


@pytest.fixture
def sample_report():
    """Create a sample report for testing."""
    return RequirementReadinessReport(
        original_requirement="Test requirement",
        summary="This is a test requirement that needs clarification.",
        rewritten_user_story="As a user, I want to test something.",
        readiness_score=45,
        recommendation=RequirementReadinessRecommendation.NOT_READY,
        score_breakdown=ScoreBreakdown(
            clarity=50,
            acceptance_criteria_quality=40,
            testability=45,
            edge_case_coverage=35,
            dependency_clarity=55,
            risk_visibility=40,
            observability_expectations=30,
        ),
        missing_information=["Scope definition", "User persona"],
        acceptance_criteria=["User can perform action", "System responds correctly"],
        edge_cases=["Invalid input", "Timeout scenario"],
        product_risks=["Scope creep"],
        qa_risks=["Insufficient test coverage"],
        technical_risks=["Integration complexity"],
        suggested_test_scenarios=[
            SuggestedTestScenario(
                title="Basic test",
                type=TestScenarioType.FUNCTIONAL,
                priority=TestScenarioPriority.HIGH,
                description="Test basic functionality",
            )
        ],
        automation_candidates=["API tests"],
        clarification_questions=["What is the scope?", "Who is the user?"],
        human_review_notes=["Needs product owner review"],
    )


class TestJiraFormatter:
    """Tests for jira_formatter module."""

    def test_format_jira_comment_basic(self, sample_report):
        """Test basic Jira comment formatting uses plain text."""
        result = format_jira_comment(sample_report)
        
        assert "AI Requirement Readiness Analysis" in result
        assert f"Readiness Score: {sample_report.readiness_score}/100" in result
        # Score 43 -> NEEDS REFINEMENT (40-59 range)
        assert "Recommendation: NEEDS REFINEMENT" in result

    def test_format_jira_comment_with_issue_key(self, sample_report):
        """Test Jira comment includes issue key in title."""
        result = format_jira_comment(sample_report, issue_key="QA-123")
        
        assert "QA-123" in result
        assert "AI Requirement Readiness Analysis — QA-123" in result

    def test_format_jira_comment_contains_main_concerns(self, sample_report):
        """Test Jira comment includes main concerns section."""
        result = format_jira_comment(sample_report)
        
        assert "Main Concerns:" in result
        assert "• Scope creep" in result

    def test_format_jira_comment_contains_clarification_questions(self, sample_report):
        """Test Jira comment includes numbered clarification questions."""
        result = format_jira_comment(sample_report)
        
        assert "Clarification Questions:" in result
        assert "1. What is the scope?" in result
        assert "2. Who is the user?" in result

    def test_format_jira_comment_contains_qa_next_step(self, sample_report):
        """Test Jira comment includes QA next step."""
        result = format_jira_comment(sample_report)
        
        assert "QA Next Step:" in result

    def test_format_jira_comment_contains_human_review_note(self, sample_report):
        """Test Jira comment includes human review note."""
        result = format_jira_comment(sample_report)
        
        assert "Needs product owner review" in result

    def test_format_jira_comment_no_wiki_markup(self, sample_report):
        """Test Jira comment does not contain legacy wiki markup."""
        result = format_jira_comment(sample_report)
        
        # Should not contain any Jira wiki markup
        assert "h3" not in result
        assert "h4" not in result
        assert "{color:" not in result
        assert "----" not in result
        assert "*Readiness" not in result

    def test_format_jira_comment_ready_status(self):
        """Test QA next step for ready status."""
        report = RequirementReadinessReport(
            original_requirement="Test",
            summary="Ready requirement",
            rewritten_user_story="As a user...",
            readiness_score=90,
            recommendation=RequirementReadinessRecommendation.READY,
            score_breakdown=ScoreBreakdown(
                clarity=90,
                acceptance_criteria_quality=90,
                testability=90,
                edge_case_coverage=85,
                dependency_clarity=90,
                risk_visibility=85,
                observability_expectations=85,
            ),
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
        result = format_jira_comment(report)
        
        assert "Ready for test planning" in result
        assert "Recommendation: READY" in result

    def test_format_jira_comment_recommendation_formatting(self):
        """Test recommendation enum values are formatted correctly."""
        from src.jira_formatter import _format_recommendation
        
        assert _format_recommendation("ready") == "READY"
        assert _format_recommendation("needs_refinement") == "NEEDS REFINEMENT"
        assert _format_recommendation("high_risk") == "HIGH RISK"
        assert _format_recommendation("not_ready") == "NOT READY"


class TestConfluenceFormatter:
    """Tests for confluence_formatter module."""

    def test_format_confluence_page_basic(self, sample_report):
        """Test basic Confluence page formatting."""
        result = format_confluence_page(sample_report)
        
        assert "page_title" in result
        assert "page_body" in result
        assert result["page_title"] == "Requirement Readiness Report"

    def test_format_confluence_page_with_issue_key(self, sample_report):
        """Test Confluence page title with issue key."""
        result = format_confluence_page(sample_report, issue_key="QA-456")
        
        assert result["page_title"] == "QA-456: Requirement Readiness Report"

    def test_format_confluence_page_with_custom_title(self, sample_report):
        """Test Confluence page with custom title."""
        result = format_confluence_page(sample_report, title="Custom Report Title")
        
        assert result["page_title"] == "Custom Report Title"

    def test_format_confluence_page_contains_executive_summary(self, sample_report):
        """Test Confluence page includes executive summary."""
        result = format_confluence_page(sample_report)
        
        assert "## Executive Summary" in result["page_body"]
        assert "This is a test requirement" in result["page_body"]

    def test_format_confluence_page_contains_readiness_score(self, sample_report):
        """Test Confluence page includes readiness score."""
        result = format_confluence_page(sample_report)
        
        assert "## Readiness Score" in result["page_body"]
        assert "45/100" in result["page_body"]

    def test_format_confluence_page_contains_score_breakdown(self, sample_report):
        """Test Confluence page includes score breakdown table."""
        result = format_confluence_page(sample_report)
        body = result["page_body"]
        
        assert "## Score Breakdown" in body
        assert "| Clarity | 50/100 |" in body
        assert "| Testability | 45/100 |" in body

    def test_format_confluence_page_contains_missing_information(self, sample_report):
        """Test Confluence page includes missing information."""
        result = format_confluence_page(sample_report)
        
        assert "## Missing Information" in result["page_body"]
        assert "Scope definition" in result["page_body"]

    def test_format_confluence_page_contains_acceptance_criteria(self, sample_report):
        """Test Confluence page includes acceptance criteria."""
        result = format_confluence_page(sample_report)
        
        assert "## Acceptance Criteria" in result["page_body"]
        assert "User can perform action" in result["page_body"]

    def test_format_confluence_page_contains_risks_table(self, sample_report):
        """Test Confluence page includes risks table."""
        result = format_confluence_page(sample_report)
        body = result["page_body"]
        
        assert "## Risks" in body
        assert "| Product | Scope creep |" in body
        assert "| QA | Insufficient test coverage |" in body
        assert "| Technical | Integration complexity |" in body

    def test_format_confluence_page_contains_test_scenarios(self, sample_report):
        """Test Confluence page includes test scenarios table."""
        result = format_confluence_page(sample_report)
        body = result["page_body"]
        
        assert "## Suggested Test Scenarios" in body
        assert "| Basic test | functional | high |" in body

    def test_format_confluence_page_contains_clarification_questions(self, sample_report):
        """Test Confluence page includes clarification questions."""
        result = format_confluence_page(sample_report)
        
        assert "## Clarification Questions" in result["page_body"]
        assert "What is the scope?" in result["page_body"]

    def test_format_confluence_page_contains_human_review_notes(self, sample_report):
        """Test Confluence page includes human review notes."""
        result = format_confluence_page(sample_report)
        
        assert "## Human Review Notes" in result["page_body"]
        assert "Needs product owner review" in result["page_body"]

    def test_format_confluence_page_contains_footer(self, sample_report):
        """Test Confluence page includes footer."""
        result = format_confluence_page(sample_report)
        
        assert "AI Requirement Readiness Analyzer" in result["page_body"]

    def test_format_confluence_page_rewritten_user_story(self, sample_report):
        """Test Confluence page includes rewritten user story."""
        result = format_confluence_page(sample_report)
        
        assert "## Rewritten User Story" in result["page_body"]
        assert "As a user, I want to test something" in result["page_body"]
