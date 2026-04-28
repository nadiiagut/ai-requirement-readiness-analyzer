"""Tests for /format/confluence-sprint-page endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.api import (
    app,
    _render_confluence_sprint_page,
    SprintAnalysisResponse,
    RiskyEntry,
    ConfluenceSprintPageRequest,
)


client = TestClient(app)


def _sample_sprint_analysis(
    sprint_name: str = "Sprint 1",
    context_distribution: dict = None,
    sprint_health_score: int = 75,
    delivery_confidence: str = "Medium",
    total_issues: int = 5,
    ready_count: int = 3,
    needs_review_count: int = 1,
    needs_refinement_count: int = 1,
    not_ready_count: int = 0,
    risky_entries: list = None,
    top_risks: list = None,
    qa_focus_areas: list = None,
    blocked_candidates: list = None,
    recommended_actions: list = None,
    executive_summary: str = None,
) -> SprintAnalysisResponse:
    """Create a sample sprint analysis for testing."""
    if context_distribution is None:
        context_distribution = {"generic_web": 5}
    if risky_entries is None:
        risky_entries = []
    if top_risks is None:
        top_risks = []
    if qa_focus_areas is None:
        qa_focus_areas = []
    if blocked_candidates is None:
        blocked_candidates = []
    if recommended_actions is None:
        recommended_actions = ["Monitor sprint progress"]
    if executive_summary is None:
        executive_summary = f"Sprint '{sprint_name}' has moderate delivery risk. Health score: {sprint_health_score}/100."
    
    return SprintAnalysisResponse(
        sprint_name=sprint_name,
        context_distribution=context_distribution,
        sprint_health_score=sprint_health_score,
        delivery_confidence=delivery_confidence,
        total_issues=total_issues,
        ready_count=ready_count,
        needs_review_count=needs_review_count,
        needs_refinement_count=needs_refinement_count,
        not_ready_count=not_ready_count,
        risky_entries=[RiskyEntry(**r) if isinstance(r, dict) else r for r in risky_entries],
        top_risks=top_risks,
        qa_focus_areas=qa_focus_areas,
        blocked_candidates=blocked_candidates,
        recommended_actions=recommended_actions,
        executive_summary=executive_summary
    )


class TestRenderConfluenceSprintPage:
    """Tests for _render_confluence_sprint_page helper function."""
    
    def test_page_title_includes_sprint_name(self):
        """Test that page title includes sprint name."""
        analysis = _sample_sprint_analysis(sprint_name="Q1 Sprint 3")
        result = _render_confluence_sprint_page(analysis)
        assert result["page_title"] == "Q1 Sprint 3 Quality Dashboard"
    
    def test_body_contains_h1_title(self):
        """Test that body starts with h1 title."""
        analysis = _sample_sprint_analysis(sprint_name="My Sprint")
        result = _render_confluence_sprint_page(analysis)
        assert "<h1>My Sprint Quality Dashboard</h1>" in result["page_body_storage"]
    
    def test_body_contains_executive_summary(self):
        """Test that body contains executive summary section."""
        analysis = _sample_sprint_analysis(executive_summary="This is the summary.")
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<h2>Executive Summary</h2>" in body
        assert "<p>This is the summary.</p>" in body
    
    def test_body_contains_health_score(self):
        """Test that body contains health score section."""
        analysis = _sample_sprint_analysis(sprint_health_score=82)
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<h2>Sprint Health Score</h2>" in body
        assert "82/100" in body
    
    def test_body_contains_delivery_confidence(self):
        """Test that body contains delivery confidence section."""
        analysis = _sample_sprint_analysis(delivery_confidence="High")
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<h2>Delivery Confidence</h2>" in body
        assert "<strong>High</strong>" in body
    
    def test_body_contains_readiness_distribution_table(self):
        """Test that body contains readiness distribution table."""
        analysis = _sample_sprint_analysis(
            ready_count=3,
            needs_review_count=1,
            needs_refinement_count=1,
            total_issues=5
        )
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<h2>Readiness Distribution</h2>" in body
        assert "<table>" in body
        assert "<th>Status</th>" in body
        assert "<td>Ready</td>" in body
        assert "<td>3</td>" in body
    
    def test_body_contains_risky_entries_table(self):
        """Test that body contains risky entries when present."""
        analysis = _sample_sprint_analysis(
            risky_entries=[
                {"issue_key": "NG-1", "title": "Risky Feature", "risk": "High", "reason": "Missing specs"}
            ]
        )
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<h2>Risky Sprint Entries</h2>" in body
        assert "NG-1" in body
        assert "Risky Feature" in body
        assert "High" in body
    
    def test_body_contains_no_risky_entries_message(self):
        """Test message when no risky entries."""
        analysis = _sample_sprint_analysis(risky_entries=[])
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "No risky entries identified." in body
    
    def test_body_contains_top_risks_list(self):
        """Test that body contains top risks as list."""
        analysis = _sample_sprint_analysis(
            top_risks=["Risk A", "Risk B"]
        )
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<h2>Top Risks</h2>" in body
        assert "<ul>" in body
        assert "<li>Risk A</li>" in body
        assert "<li>Risk B</li>" in body
    
    def test_body_contains_qa_focus_areas(self):
        """Test that body contains QA focus areas."""
        analysis = _sample_sprint_analysis(
            qa_focus_areas=["Edge case testing", "Integration testing"]
        )
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<h2>QA Focus Areas</h2>" in body
        assert "<li>Edge case testing</li>" in body
    
    def test_body_contains_recommended_actions(self):
        """Test that body contains recommended actions."""
        analysis = _sample_sprint_analysis(
            recommended_actions=["Schedule refinement", "Review blockers"]
        )
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<h2>Recommended Actions</h2>" in body
        assert "<li>Schedule refinement</li>" in body
    
    def test_body_contains_story_breakdown(self):
        """Test that body contains story breakdown section."""
        analysis = _sample_sprint_analysis(total_issues=10, ready_count=7)
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<h2>Story Breakdown</h2>" in body
        assert "<h3>Summary</h3>" in body
        assert "Total Issues" in body
    
    def test_body_contains_blocked_candidates_when_present(self):
        """Test that blocked candidates are shown when present."""
        analysis = _sample_sprint_analysis(
            blocked_candidates=["NG-5: Blocking issue"]
        )
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<h3>Potential Blockers</h3>" in body
        assert "NG-5: Blocking issue" in body


class TestConfluenceSprintPageHTMLValidity:
    """Tests to ensure valid HTML output and no markdown."""
    
    def test_no_markdown_table_syntax(self):
        """Test that output has no markdown table syntax."""
        analysis = _sample_sprint_analysis(
            risky_entries=[
                {"issue_key": "X-1", "title": "Test", "risk": "High", "reason": "Test reason"}
            ]
        )
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        # No markdown table delimiters
        assert "|---" not in body
        assert "| " not in body or "<td>" in body  # Allow | in content but not as table delimiter
        assert "---" not in body or "---" in analysis.executive_summary  # Only if in content
    
    def test_no_markdown_headers(self):
        """Test that output has no markdown header syntax."""
        analysis = _sample_sprint_analysis()
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        # No markdown headers
        assert not body.startswith("#")
        assert "\n#" not in body
        assert "## " not in body
        assert "### " not in body
    
    def test_no_markdown_lists(self):
        """Test that output has no markdown list syntax."""
        analysis = _sample_sprint_analysis(
            top_risks=["Risk 1", "Risk 2"],
            recommended_actions=["Action 1"]
        )
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        # No markdown list markers at start of lines
        lines = body.split(">")
        for line in lines:
            stripped = line.strip()
            # Shouldn't start with markdown list markers
            assert not stripped.startswith("- ") or stripped.startswith("-") and "<" in stripped
            assert not stripped.startswith("* ")
    
    def test_no_escaped_newlines(self):
        """Test that output has no escaped newline sequences."""
        analysis = _sample_sprint_analysis()
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "\\n" not in body
        assert "\\r" not in body
    
    def test_uses_only_safe_tags(self):
        """Test that output uses only allowed HTML tags."""
        analysis = _sample_sprint_analysis(
            risky_entries=[
                {"issue_key": "X-1", "title": "Test", "risk": "High", "reason": "Reason"}
            ],
            top_risks=["Risk 1"],
            qa_focus_areas=["Area 1"],
            recommended_actions=["Action 1"],
            blocked_candidates=["Blocker 1"]
        )
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        
        # Allowed tags
        allowed_tags = ["h1", "h2", "h3", "p", "ul", "li", "table", "tr", "th", "td", "strong"]
        
        # Check that only allowed opening tags are present
        import re
        opening_tags = re.findall(r"<([a-z0-9]+)[^>]*>", body, re.IGNORECASE)
        for tag in opening_tags:
            assert tag.lower() in allowed_tags, f"Unexpected tag: {tag}"
    
    def test_html_tags_are_properly_closed(self):
        """Test that HTML tags are properly structured."""
        analysis = _sample_sprint_analysis(
            risky_entries=[
                {"issue_key": "X-1", "title": "Test", "risk": "High", "reason": "Reason"}
            ],
            top_risks=["Risk 1"]
        )
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        
        # Count opening and closing tags for key elements
        assert body.count("<table>") == body.count("</table>")
        assert body.count("<ul>") == body.count("</ul>")
        assert body.count("<tr>") == body.count("</tr>")
        assert body.count("<h1>") == body.count("</h1>")
        assert body.count("<h2>") == body.count("</h2>")


class TestConfluenceSprintPageEndpoint:
    """Integration tests for /format/confluence-sprint-page endpoint."""
    
    def test_endpoint_returns_200(self):
        """Test that endpoint returns 200 for valid input."""
        response = client.post(
            "/format/confluence-sprint-page",
            json={
                "sprint_analysis": {
                    "sprint_name": "Sprint 1",
                    "context_distribution": {"generic_web": 5},
                    "sprint_health_score": 75,
                    "delivery_confidence": "Medium",
                    "total_issues": 5,
                    "ready_count": 3,
                    "needs_review_count": 1,
                    "needs_refinement_count": 1,
                    "not_ready_count": 0,
                    "risky_entries": [],
                    "top_risks": [],
                    "qa_focus_areas": [],
                    "blocked_candidates": [],
                    "recommended_actions": ["Monitor progress"],
                    "executive_summary": "Sprint is on track."
                }
            }
        )
        assert response.status_code == 200
    
    def test_endpoint_returns_page_title(self):
        """Test that endpoint returns page_title field."""
        response = client.post(
            "/format/confluence-sprint-page",
            json={
                "sprint_analysis": {
                    "sprint_name": "My Sprint",
                    "context_distribution": {"generic_web": 3},
                    "sprint_health_score": 80,
                    "delivery_confidence": "High",
                    "total_issues": 3,
                    "ready_count": 3,
                    "needs_review_count": 0,
                    "needs_refinement_count": 0,
                    "not_ready_count": 0,
                    "risky_entries": [],
                    "top_risks": [],
                    "qa_focus_areas": [],
                    "blocked_candidates": [],
                    "recommended_actions": [],
                    "executive_summary": "Well prepared."
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "page_title" in data
        assert data["page_title"] == "My Sprint Quality Dashboard"
    
    def test_endpoint_returns_page_body_storage(self):
        """Test that endpoint returns page_body_storage field."""
        response = client.post(
            "/format/confluence-sprint-page",
            json={
                "sprint_analysis": {
                    "sprint_name": "Test Sprint",
                    "context_distribution": {"generic_web": 2},
                    "sprint_health_score": 60,
                    "delivery_confidence": "Medium",
                    "total_issues": 2,
                    "ready_count": 1,
                    "needs_review_count": 1,
                    "needs_refinement_count": 0,
                    "not_ready_count": 0,
                    "risky_entries": [],
                    "top_risks": [],
                    "qa_focus_areas": [],
                    "blocked_candidates": [],
                    "recommended_actions": [],
                    "executive_summary": "Moderate risk."
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "page_body_storage" in data
        assert "<h1>" in data["page_body_storage"]
    
    def test_endpoint_with_risky_entries(self):
        """Test endpoint with risky entries."""
        response = client.post(
            "/format/confluence-sprint-page",
            json={
                "sprint_analysis": {
                    "sprint_name": "Risky Sprint",
                    "context_distribution": {"generic_web": 3},
                    "sprint_health_score": 40,
                    "delivery_confidence": "Low",
                    "total_issues": 3,
                    "ready_count": 1,
                    "needs_review_count": 0,
                    "needs_refinement_count": 2,
                    "not_ready_count": 0,
                    "risky_entries": [
                        {
                            "issue_key": "NG-10",
                            "title": "Complex Feature",
                            "risk": "High",
                            "reason": "Missing requirements"
                        }
                    ],
                    "top_risks": ["Scope creep", "Resource constraints"],
                    "qa_focus_areas": ["Integration testing"],
                    "blocked_candidates": [],
                    "recommended_actions": ["Schedule refinement"],
                    "executive_summary": "High risk sprint."
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        body = data["page_body_storage"]
        assert "NG-10" in body
        assert "Complex Feature" in body
        assert "Scope creep" in body
    
    def test_endpoint_validation_error(self):
        """Test that endpoint returns 422 for invalid input."""
        response = client.post(
            "/format/confluence-sprint-page",
            json={
                "sprint_analysis": {
                    "sprint_name": "Invalid Sprint"
                    # Missing required fields
                }
            }
        )
        assert response.status_code == 422
    
    def test_endpoint_body_has_all_sections(self):
        """Test that response body contains all required sections."""
        response = client.post(
            "/format/confluence-sprint-page",
            json={
                "sprint_analysis": {
                    "sprint_name": "Full Sprint",
                    "context_distribution": {"generic_web": 4, "cdn_edge_networking": 1},
                    "sprint_health_score": 70,
                    "delivery_confidence": "Medium",
                    "total_issues": 5,
                    "ready_count": 3,
                    "needs_review_count": 1,
                    "needs_refinement_count": 1,
                    "not_ready_count": 0,
                    "risky_entries": [
                        {"issue_key": "X-1", "title": "Test", "risk": "Medium", "reason": "Test"}
                    ],
                    "top_risks": ["Risk 1"],
                    "qa_focus_areas": ["Area 1"],
                    "blocked_candidates": ["Blocker 1"],
                    "recommended_actions": ["Action 1"],
                    "executive_summary": "Summary here."
                }
            }
        )
        assert response.status_code == 200
        body = response.json()["page_body_storage"]
        
        # All 10 sections should be present
        assert "<h1>" in body  # 1. Title
        assert "Executive Summary" in body  # 2
        assert "Sprint Health Score" in body  # 3
        assert "Delivery Confidence" in body  # 4
        assert "Readiness Distribution" in body  # 5
        assert "Risky Sprint Entries" in body  # 6
        assert "Top Risks" in body  # 7
        assert "QA Focus Areas" in body  # 8
        assert "Recommended Actions" in body  # 9
        assert "Story Breakdown" in body  # 10
