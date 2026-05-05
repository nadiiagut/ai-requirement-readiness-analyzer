"""Tests for /format/confluence-sprint-page endpoint."""

import pytest
import re
from fastapi.testclient import TestClient

from src.api import (
    app,
    _render_confluence_sprint_page,
    _render_confluence_sprint_body,
    SprintAnalysisResponse,
    SprintScopeEntry,
    DecisionEntry,
    RiskyEntry,
    ConfluenceSprintPageRequest,
)


client = TestClient(app)


def _sample_sprint_analysis(
    sprint_name: str = "Sprint 1",
    sprint_health_score: int = 75,
    delivery_confidence: str = "Medium",
    total_issues: int = 5,
    high_risk_count: int = 1,
    clarification_count: int = 2,
    sprint_scope: list = None,
    qa_focus_areas: list = None,
    decisions_needed: list = None,
    executive_summary: str = None,
) -> SprintAnalysisResponse:
    """Create a sample sprint analysis for testing."""
    if sprint_scope is None:
        sprint_scope = [
            SprintScopeEntry(
                issue_key="T-1",
                title="Test Issue",
                assignee="Developer",
                status="To Do",
                risk="Low",
                reason="No QA risk detected",
                notes="Ready for QA test planning",
                issue_url=None
            )
        ]
    if qa_focus_areas is None:
        qa_focus_areas = []
    if decisions_needed is None:
        decisions_needed = []
    if executive_summary is None:
        executive_summary = f"This sprint focuses on various improvements. Delivery confidence is medium. Health: {sprint_health_score}/100."

    # Generate confluence page
    confluence_page_title, confluence_page_body_storage = _render_confluence_sprint_body(
        sprint_name=sprint_name,
        executive_summary=executive_summary,
        sprint_health_score=sprint_health_score,
        delivery_confidence=delivery_confidence,
        total_issues=total_issues,
        high_risk_count=high_risk_count,
        clarification_count=clarification_count,
        sprint_scope=sprint_scope,
        qa_focus_areas=qa_focus_areas,
        decisions_needed=decisions_needed,
    )

    return SprintAnalysisResponse(
        sprint_name=sprint_name,
        context_distribution={"generic_web": total_issues},
        sprint_health_score=sprint_health_score,
        delivery_confidence=delivery_confidence,
        total_issues=total_issues,
        high_risk_count=high_risk_count,
        clarification_count=clarification_count,
        ready_count=3,
        needs_review_count=1,
        needs_refinement_count=1,
        not_ready_count=0,
        sprint_scope=sprint_scope,
        risky_entries=[],
        top_risks=[],
        qa_focus_areas=qa_focus_areas,
        blocked_candidates=[],
        recommended_actions=[],
        decisions_needed=decisions_needed,
        executive_summary=executive_summary,
        confluence_page_title=confluence_page_title,
        confluence_page_body_storage=confluence_page_body_storage
    )


class TestRenderConfluenceSprintPage:
    """Tests for _render_confluence_sprint_page helper function."""
    
    def test_page_title_format(self):
        """Test that page title is '{Sprint Name} Dashboard' with no leading '='."""
        analysis = _sample_sprint_analysis(sprint_name="NG Sprint 1")
        result = _render_confluence_sprint_page(analysis)
        assert result["page_title"] == "NG Sprint 1 Dashboard"
        assert not result["page_title"].startswith("=")
    
    def test_page_title_strips_leading_equals(self):
        """Test that leading '=' is removed from sprint name."""
        analysis = _sample_sprint_analysis(sprint_name="=Test Sprint")
        result = _render_confluence_sprint_page(analysis)
        assert result["page_title"] == "Test Sprint Dashboard"
        assert "=" not in result["page_title"]
    
    def test_body_contains_h1_title(self):
        """Test that body starts with h1 title (not 'Quality Dashboard')."""
        analysis = _sample_sprint_analysis(sprint_name="My Sprint")
        result = _render_confluence_sprint_page(analysis)
        assert "<h1>My Sprint Dashboard</h1>" in result["page_body_storage"]
        assert "My Sprint Quality Dashboard" not in result["page_body_storage"]
    
    def test_body_contains_executive_summary(self):
        """Test that body contains executive summary section."""
        analysis = _sample_sprint_analysis(executive_summary="This is the summary.")
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<h2>Executive Summary</h2>" in body
        assert "<p>This is the summary.</p>" in body
    
    def test_body_contains_sprint_metrics_table(self):
        """Test that body contains Sprint Metrics table with required fields."""
        analysis = _sample_sprint_analysis(
            sprint_health_score=82,
            delivery_confidence="High",
            total_issues=10,
            high_risk_count=2,
            clarification_count=3
        )
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<h2>Sprint Metrics</h2>" in body
        assert "Sprint Health Score" in body
        assert "82/100" in body
        assert "Delivery Confidence" in body
        assert "High" in body
        assert "Total Issues" in body
        assert "10" in body
        assert "High Risk Items" in body
        assert "Items Needing Clarification" in body
    
    def test_body_contains_sprint_scope_table(self):
        """Test that body contains Sprint Scope table (not 'Risky Sprint Entries')."""
        scope_entry = SprintScopeEntry(
            issue_key="NG-1",
            title="Test Feature",
            assignee="John Doe",
            status="In Progress",
            risk="High",
            reason="Missing acceptance criteria",
            notes="AC missing — requires refinement",
            issue_url=None
        )
        analysis = _sample_sprint_analysis(sprint_scope=[scope_entry])
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<h2>Sprint Scope</h2>" in body
        assert "Risky Sprint Entries" not in body
        assert "NG-1" in body
        assert "Test Feature" in body
        assert "John Doe" in body
        assert "In Progress" in body
        assert "High" in body
    
    def test_body_contains_issue_links(self):
        """Test that issues are rendered as links when issue_url is provided."""
        scope_entry = SprintScopeEntry(
            issue_key="NG-7",
            title="Link Feature",
            assignee="Dev",
            status="To Do",
            risk="Low",
            reason="No QA risk detected",
            notes="Ready for QA test planning",
            issue_url="https://nadingut.atlassian.net/browse/NG-7"
        )
        analysis = _sample_sprint_analysis(sprint_scope=[scope_entry])
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert '<a href="https://nadingut.atlassian.net/browse/NG-7">NG-7</a>' in body
    
    def test_body_contains_status_column(self):
        """Test that Status column exists in Sprint Scope table."""
        analysis = _sample_sprint_analysis()
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<th>Status</th>" in body
        assert "To Do" in body  # From default sprint_scope
    
    def test_body_does_not_contain_removed_sections(self):
        """Test that removed sections are not present."""
        analysis = _sample_sprint_analysis()
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        # These sections should NOT exist
        assert "Readiness Distribution" not in body
        assert "Story Breakdown" not in body
        assert "Context Distribution" not in body
        assert "Risky Sprint Entries" not in body
    
    def test_body_contains_qa_focus_areas(self):
        """Test that body contains QA / Delivery Focus Areas (renamed section)."""
        analysis = _sample_sprint_analysis(
            qa_focus_areas=["Edge case testing", "Integration testing"]
        )
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<h2>QA / Delivery Focus Areas</h2>" in body
        assert "<li>Edge case testing</li>" in body

    def test_qa_section_contains_97_percent_target(self):
        """QA section must always include the 97% pass-rate target as a bullet."""
        analysis = _sample_sprint_analysis(qa_focus_areas=[])
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<li>Maintain 97% pass rate on new feature tests and regression suite.</li>" in body

    def test_qa_section_97_target_present_alongside_dynamic_areas(self):
        """Static 97% target appears before dynamic focus areas, both present."""
        analysis = _sample_sprint_analysis(qa_focus_areas=["Integration testing"])
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        target = "<li>Maintain 97% pass rate on new feature tests and regression suite.</li>"
        dynamic = "<li>Integration testing</li>"
        assert target in body
        assert dynamic in body
        assert body.index(target) < body.index(dynamic)

    def test_body_contains_stakeholders(self):
        """Test that Stakeholders section is present with default rows."""
        analysis = _sample_sprint_analysis()
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<h2>Stakeholders</h2>" in body
        assert "Product / Delivery Owner" in body
        assert "@Nadin Gut" in body

    def test_body_contains_progress_snapshot(self):
        """Test that Progress Snapshot section is present."""
        scope = [
            SprintScopeEntry(issue_key="T-1", title="A", assignee=None,
                             status="To Do", risk="Low", reason="r", notes="n", issue_url=None),
            SprintScopeEntry(issue_key="T-2", title="B", assignee=None,
                             status="In Progress", risk="Low", reason="r", notes="n", issue_url=None),
            SprintScopeEntry(issue_key="T-3", title="C", assignee=None,
                             status="Done", risk="Low", reason="r", notes="n", issue_url=None),
        ]
        analysis = _sample_sprint_analysis(sprint_scope=scope)
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<h2>Progress Snapshot</h2>" in body
        assert "<td>To Do</td><td>1</td>" in body
        assert "<td>In Progress</td><td>1</td>" in body
        assert "<td>Done</td><td>1</td>" in body
        assert "Blocked / Flagged" in body

    def test_body_contains_decision_needed(self):
        """Test that Decision Needed section is present."""
        decisions = [
            DecisionEntry(
                issue_key="NG-1",
                issue_url="https://nadingut.atlassian.net/browse/NG-1",
                title="Role Setup",
                decision_needed="Define role and permission boundaries",
                why_it_matters="Without defined permissions, implementation may not match expectations.",
            )
        ]
        analysis = _sample_sprint_analysis(decisions_needed=decisions)
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "<h2>Decision Needed</h2>" in body
        assert "NG-1" in body
        assert "Define role and permission boundaries" in body

    def test_body_empty_decisions_shows_message(self):
        """Test message when no decisions are needed."""
        analysis = _sample_sprint_analysis(decisions_needed=[])
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "No stakeholder decisions currently detected." in body

    def test_body_no_recommended_actions_section(self):
        """Test that Recommended Actions section is removed."""
        analysis = _sample_sprint_analysis()
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "Recommended Actions" not in body

    def test_issue_link_generated_when_no_url(self):
        """Test that issue link is auto-generated when issue_url is None."""
        scope = [
            SprintScopeEntry(issue_key="NG-42", title="T", assignee=None,
                             status="To Do", risk="Low", reason="r", notes="n", issue_url=None)
        ]
        analysis = _sample_sprint_analysis(sprint_scope=scope)
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert '<a href="https://nadingut.atlassian.net/browse/NG-42">NG-42</a>' in body


class TestConfluenceSprintPageHTMLValidity:
    """Tests to ensure valid HTML output and no markdown."""
    
    def test_no_markdown_table_syntax(self):
        """Test that output has no markdown table syntax."""
        analysis = _sample_sprint_analysis()
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        # No markdown table delimiters
        assert "|---" not in body
    
    def test_no_markdown_headers(self):
        """Test that output has no markdown header syntax."""
        analysis = _sample_sprint_analysis()
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        # No markdown headers
        assert not body.startswith("#")
        assert not body.startswith("=")
        assert "\n#" not in body
        assert "## " not in body
    
    def test_no_markdown_lists(self):
        """Test that output has no markdown list syntax."""
        analysis = _sample_sprint_analysis(
            qa_focus_areas=["Area 1"],
        )
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        # Check for markdown list at line starts (after > which ends tags)
        lines = body.split(">")
        for line in lines:
            stripped = line.strip()
            # Shouldn't start with markdown list markers
            assert not stripped.startswith("- ") or "<" in stripped
            assert not stripped.startswith("* ")
    
    def test_no_escaped_newlines(self):
        """Test that output has no escaped newline sequences."""
        analysis = _sample_sprint_analysis()
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        assert "\\n" not in body
        assert "\\r" not in body
    
    def test_uses_only_safe_tags(self):
        """Test that output uses only allowed HTML tags (including 'a' for links)."""
        scope_entry = SprintScopeEntry(
            issue_key="X-1",
            title="Test",
            assignee="Dev",
            status="To Do",
            risk="High",
            reason="Reason",
            notes="Notes",
            issue_url="https://example.com/X-1"
        )
        analysis = _sample_sprint_analysis(
            sprint_scope=[scope_entry],
            qa_focus_areas=["Area 1"],
        )
        result = _render_confluence_sprint_page(analysis)
        body = result["page_body_storage"]
        
        # Allowed tags (includes 'a' for issue links)
        allowed_tags = {"h1", "h2", "p", "ul", "li", "table", "tr", "th", "td", "strong", "a"}

        # Check that only allowed opening tags are present
        opening_tags = re.findall(r"<([a-z0-9]+)[^>]*>", body, re.IGNORECASE)
        for tag in opening_tags:
            assert tag.lower() in allowed_tags, f"Unexpected tag: {tag}"
    
    def test_html_tags_are_properly_closed(self):
        """Test that HTML tags are properly structured."""
        analysis = _sample_sprint_analysis(
            qa_focus_areas=["Area 1"]
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
                    "high_risk_count": 1,
                    "clarification_count": 2,
                    "ready_count": 3,
                    "needs_review_count": 1,
                    "needs_refinement_count": 1,
                    "not_ready_count": 0,
                    "sprint_scope": [],
                    "risky_entries": [],
                    "top_risks": [],
                    "qa_focus_areas": [],
                    "blocked_candidates": [],
                    "recommended_actions": ["Monitor progress"],
                    "executive_summary": "Sprint is on track.",
                    "confluence_page_title": "Sprint 1 Dashboard",
                    "confluence_page_body_storage": "<h1>Sprint 1 Dashboard</h1>"
                }
            }
        )
        assert response.status_code == 200
    
    def test_endpoint_returns_page_title(self):
        """Test that endpoint returns page_title in new format."""
        response = client.post(
            "/format/confluence-sprint-page",
            json={
                "sprint_analysis": {
                    "sprint_name": "My Sprint",
                    "context_distribution": {"generic_web": 3},
                    "sprint_health_score": 80,
                    "delivery_confidence": "High",
                    "total_issues": 3,
                    "high_risk_count": 0,
                    "clarification_count": 0,
                    "ready_count": 3,
                    "needs_review_count": 0,
                    "needs_refinement_count": 0,
                    "not_ready_count": 0,
                    "sprint_scope": [],
                    "risky_entries": [],
                    "top_risks": [],
                    "qa_focus_areas": [],
                    "blocked_candidates": [],
                    "recommended_actions": [],
                    "executive_summary": "Well prepared.",
                    "confluence_page_title": "My Sprint Dashboard",
                    "confluence_page_body_storage": "<h1>My Sprint Dashboard</h1>"
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "page_title" in data
        # Title should be "{Sprint Name} Dashboard" with no leading "="
        assert data["page_title"] == "My Sprint Dashboard"
        assert not data["page_title"].startswith("=")
    
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
                    "high_risk_count": 1,
                    "clarification_count": 1,
                    "ready_count": 1,
                    "needs_review_count": 1,
                    "needs_refinement_count": 0,
                    "not_ready_count": 0,
                    "sprint_scope": [],
                    "risky_entries": [],
                    "top_risks": [],
                    "qa_focus_areas": [],
                    "blocked_candidates": [],
                    "recommended_actions": [],
                    "executive_summary": "Moderate risk.",
                    "confluence_page_title": "Test Sprint Dashboard",
                    "confluence_page_body_storage": "<h1>Test Sprint Dashboard</h1>"
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "page_body_storage" in data
        assert "<h1>" in data["page_body_storage"]
    
    def test_endpoint_with_sprint_scope(self):
        """Test endpoint with sprint_scope entries (replaced risky_entries)."""
        response = client.post(
            "/format/confluence-sprint-page",
            json={
                "sprint_analysis": {
                    "sprint_name": "Scope Sprint",
                    "context_distribution": {"generic_web": 3},
                    "sprint_health_score": 65,
                    "delivery_confidence": "Medium",
                    "total_issues": 3,
                    "high_risk_count": 1,
                    "clarification_count": 1,
                    "ready_count": 1,
                    "needs_review_count": 1,
                    "needs_refinement_count": 1,
                    "not_ready_count": 0,
                    "sprint_scope": [
                        {
                            "issue_key": "NG-10",
                            "title": "Complex Feature",
                            "assignee": "Developer",
                            "status": "To Do",
                            "risk": "High",
                            "reason": "Missing requirements",
                            "notes": "AC missing — requires refinement",
                            "issue_url": "https://nadingut.atlassian.net/browse/NG-10"
                        }
                    ],
                    "risky_entries": [],
                    "top_risks": [],
                    "qa_focus_areas": ["Integration testing"],
                    "blocked_candidates": [],
                    "recommended_actions": ["Schedule refinement"],
                    "executive_summary": "High risk sprint.",
                    "confluence_page_title": "Scope Sprint Dashboard",
                    "confluence_page_body_storage": "<h1>Scope Sprint Dashboard</h1>"
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        body = data["page_body_storage"]
        # Should have Sprint Scope table
        assert "Sprint Scope" in body
        # Issue should be rendered as link
        assert '<a href="https://nadingut.atlassian.net/browse/NG-10">NG-10</a>' in body
        assert "Complex Feature" in body
        assert "To Do" in body  # Status column
    
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
    
    def test_endpoint_body_has_correct_sections(self):
        """Test that response body contains only the required sections (no removed sections)."""
        response = client.post(
            "/format/confluence-sprint-page",
            json={
                "sprint_analysis": {
                    "sprint_name": "Full Sprint",
                    "context_distribution": {"generic_web": 5},
                    "sprint_health_score": 70,
                    "delivery_confidence": "Medium",
                    "total_issues": 5,
                    "high_risk_count": 1,
                    "clarification_count": 2,
                    "ready_count": 3,
                    "needs_review_count": 1,
                    "needs_refinement_count": 1,
                    "not_ready_count": 0,
                    "sprint_scope": [
                        {
                            "issue_key": "X-1",
                            "title": "Test",
                            "assignee": "Dev",
                            "status": "In Progress",
                            "risk": "Medium",
                            "reason": "Test reason",
                            "notes": "Notes",
                            "issue_url": None
                        }
                    ],
                    "risky_entries": [],
                    "top_risks": [],
                    "qa_focus_areas": ["Area 1"],
                    "blocked_candidates": [],
                    "recommended_actions": ["Action 1"],
                    "executive_summary": "Summary here.",
                    "confluence_page_title": "Full Sprint Dashboard",
                    "confluence_page_body_storage": "<h1>Full Sprint Dashboard</h1>"
                }
            }
        )
        assert response.status_code == 200
        body = response.json()["page_body_storage"]
        
        # Required sections should be present
        assert "<h1>" in body
        assert "Dashboard" in body
        assert "Executive Summary" in body
        assert "Stakeholders" in body
        assert "Sprint Metrics" in body
        assert "Progress Snapshot" in body
        assert "Sprint Scope" in body
        assert "QA / Delivery Focus Areas" in body
        assert "Decision Needed" in body

        # Removed sections should NOT be present
        assert "Readiness Distribution" not in body
        assert "Story Breakdown" not in body
        assert "Risky Sprint Entries" not in body
        assert "Context Distribution" not in body
        assert "Recommended Actions" not in body
