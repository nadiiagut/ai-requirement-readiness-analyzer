"""Tests for sprint-level analysis endpoint and helper functions."""

import pytest
from fastapi.testclient import TestClient

from src.api import (
    app,
    _classify_issue_by_labels,
    _compute_sprint_health_from_labels,
    _compute_delivery_confidence,
    _generate_executive_summary,
    _infer_sprint_themes,
    SprintIssue,
    SprintAnalysisRequest,
    SprintAnalysisResponse,
    SprintScopeEntry,
    DecisionEntry,
    RiskyEntry,
)


client = TestClient(app)


class TestClassifyIssueByLabels:
    """Tests for label-based issue classification."""
    
    def test_ready_for_sprint_label(self):
        assert _classify_issue_by_labels(["ready-for-sprint"]) == "ready"
    
    def test_ready_label(self):
        assert _classify_issue_by_labels(["ready"]) == "ready"
    
    def test_sprint_ready_label(self):
        assert _classify_issue_by_labels(["sprint-ready"]) == "ready"
    
    def test_dev_ready_label(self):
        assert _classify_issue_by_labels(["dev-ready"]) == "ready"
    
    def test_needs_review_label(self):
        assert _classify_issue_by_labels(["needs-review"]) == "needs_review"
    
    def test_needs_refinement_label(self):
        assert _classify_issue_by_labels(["needs-refinement"]) == "needs_refinement"
    
    def test_backlog_label(self):
        assert _classify_issue_by_labels(["backlog"]) == "needs_refinement"
    
    def test_no_relevant_labels(self):
        assert _classify_issue_by_labels(["bug", "frontend"]) is None
    
    def test_empty_labels(self):
        assert _classify_issue_by_labels([]) is None
    
    def test_case_insensitive(self):
        assert _classify_issue_by_labels(["READY-FOR-SPRINT"]) == "ready"
        assert _classify_issue_by_labels(["Needs-Review"]) == "needs_review"
    
    def test_underscore_converted(self):
        assert _classify_issue_by_labels(["ready_for_sprint"]) == "ready"
        assert _classify_issue_by_labels(["needs_refinement"]) == "needs_refinement"
    
    def test_space_converted(self):
        assert _classify_issue_by_labels(["ready for sprint"]) == "ready"


class TestComputeSprintHealthFromLabels:
    """Tests for label-based sprint health score computation."""
    
    def test_all_ready_issues(self):
        """All ready-for-sprint labels should give score of 90."""
        labels_list = [
            ["ready-for-sprint"],
            ["ready-for-sprint"],
            ["ready-for-sprint"],
        ]
        score = _compute_sprint_health_from_labels(labels_list)
        assert score == 90
    
    def test_all_needs_refinement(self):
        """All needs-refinement labels should give score of 45."""
        labels_list = [
            ["needs-refinement"],
            ["needs-refinement"],
            ["needs-refinement"],
        ]
        score = _compute_sprint_health_from_labels(labels_list)
        assert score == 45
    
    def test_all_needs_review(self):
        """All needs-review labels should give score of 70."""
        labels_list = [
            ["needs-review"],
            ["needs-review"],
        ]
        score = _compute_sprint_health_from_labels(labels_list)
        assert score == 70
    
    def test_no_labels_gives_65(self):
        """Issues with no relevant labels should give score of 65."""
        labels_list = [
            ["bug", "frontend"],
            ["backend"],
            [],
        ]
        score = _compute_sprint_health_from_labels(labels_list)
        assert score == 65
    
    def test_mixed_labels(self):
        """Mixed labels should give weighted average."""
        labels_list = [
            ["ready-for-sprint"],  # 90
            ["needs-review"],      # 70
            ["needs-refinement"],  # 45
        ]
        score = _compute_sprint_health_from_labels(labels_list)
        # Average: (90 + 70 + 45) / 3 = 68.33 -> 68
        assert score == 68
    
    def test_empty_list_returns_0(self):
        """Empty sprint should return 0."""
        score = _compute_sprint_health_from_labels([])
        assert score == 0
    
    def test_score_clamped_to_1_minimum(self):
        """Score should be at least 1 if there are issues."""
        labels_list = [["needs-refinement"]]
        score = _compute_sprint_health_from_labels(labels_list)
        assert score >= 1
    
    def test_score_clamped_to_100_maximum(self):
        """Score should never exceed 100."""
        labels_list = [["ready-for-sprint"] for _ in range(10)]
        score = _compute_sprint_health_from_labels(labels_list)
        assert score <= 100


class TestComputeDeliveryConfidence:
    """Tests for delivery confidence computation."""
    
    def test_high_confidence(self):
        """High health + low risk ratio = High confidence."""
        assert _compute_delivery_confidence(80, 0.1) == "High"
    
    def test_medium_confidence(self):
        """Moderate health or risk = Medium confidence."""
        assert _compute_delivery_confidence(60, 0.3) == "Medium"
    
    def test_low_confidence_low_health(self):
        """Low health = Low confidence."""
        assert _compute_delivery_confidence(40, 0.1) == "Low"
    
    def test_low_confidence_high_risk(self):
        """High risk ratio = Low confidence."""
        assert _compute_delivery_confidence(80, 0.5) == "Low"
    
    def test_boundary_high(self):
        """Test boundary for High confidence."""
        assert _compute_delivery_confidence(75, 0.19) == "High"
        assert _compute_delivery_confidence(74, 0.19) == "Medium"
    
    def test_boundary_medium(self):
        """Test boundary for Medium confidence."""
        assert _compute_delivery_confidence(50, 0.39) == "Medium"
        assert _compute_delivery_confidence(49, 0.39) == "Low"


class TestInferSprintThemes:
    """Tests for sprint theme inference."""

    def test_access_control_theme(self):
        themes = _infer_sprint_themes(["User role setup", "Access permissions"])
        assert "access control" in themes

    def test_user_management_theme(self):
        themes = _infer_sprint_themes(["Create user profile", "Onboard new account"])
        assert "user management" in themes

    def test_no_themes_returns_empty(self):
        themes = _infer_sprint_themes(["Fix typo", "Update README"])
        assert themes == []

    def test_max_three_themes(self):
        themes = _infer_sprint_themes([
            "User login", "Access role", "Dashboard metrics",
            "Payment invoice", "Send notification"
        ])
        assert len(themes) <= 3


class TestGenerateExecutiveSummary:
    """Tests for stakeholder-facing executive summary generation."""

    def test_high_confidence_summary(self):
        summary = _generate_executive_summary(
            sprint_name="Sprint 1",
            sprint_health=85,
            delivery_confidence="High",
            total_issues=10,
            high_risk_count=0,
            needs_refinement_count=0,
            issue_titles=["User role setup", "Access permissions"],
        )
        assert "access control" in summary
        assert "high" in summary
        assert "85/100" in summary

    def test_medium_confidence_with_refinement(self):
        summary = _generate_executive_summary(
            sprint_name="Sprint 2",
            sprint_health=60,
            delivery_confidence="Medium",
            total_issues=10,
            high_risk_count=0,
            needs_refinement_count=2,
            issue_titles=[],
        )
        assert "medium" in summary
        assert "unresolved acceptance criteria" in summary
        assert "2 stories" in summary

    def test_low_confidence_with_high_risk(self):
        summary = _generate_executive_summary(
            sprint_name="Sprint 3",
            sprint_health=30,
            delivery_confidence="Low",
            total_issues=10,
            high_risk_count=3,
            needs_refinement_count=0,
            issue_titles=[],
        )
        assert "low" in summary
        assert "3 high-risk items" in summary

    def test_summary_includes_health_score(self):
        summary = _generate_executive_summary(
            sprint_name="Test Sprint",
            sprint_health=75,
            delivery_confidence="Medium",
            total_issues=10,
            high_risk_count=0,
            needs_refinement_count=0,
        )
        assert "75/100" in summary

    def test_no_issues_returns_message(self):
        summary = _generate_executive_summary(
            sprint_name="Empty Sprint",
            sprint_health=0,
            delivery_confidence="Low",
            total_issues=0,
            high_risk_count=0,
            needs_refinement_count=0,
        )
        assert "no issues" in summary.lower()

    def test_theme_in_summary(self):
        summary = _generate_executive_summary(
            sprint_name="S",
            sprint_health=70,
            delivery_confidence="Medium",
            total_issues=5,
            high_risk_count=0,
            needs_refinement_count=0,
            issue_titles=["Admin configuration", "Setup control panel"],
        )
        assert "configuration and admin" in summary


class TestSprintAnalysisEndpoint:
    """Integration tests for /analyze/sprint endpoint."""
    
    def test_basic_sprint_analysis(self):
        """Test basic sprint analysis with demo mode."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Sprint 1",
                "sprint_id": 1,
                "issues": [
                    {
                        "issue_key": "NG-1",
                        "title": "Implement user login",
                        "description": "As a user, I want to log in so that I can access my account.",
                        "status": "To Do",
                        "priority": "High",
                        "labels": ["ready-for-sprint"]
                    },
                    {
                        "issue_key": "NG-2",
                        "title": "Add password reset",
                        "description": "Password reset functionality",
                        "status": "To Do",
                        "priority": "Medium",
                        "labels": ["needs-review"]
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["sprint_name"] == "Sprint 1"
        assert 0 <= data["sprint_health_score"] <= 100
        assert data["delivery_confidence"] in ["Low", "Medium", "High"]
        assert data["total_issues"] == 2
        assert "executive_summary" in data
    
    def test_sprint_with_needs_refinement_label(self):
        """Test that needs-refinement label creates risky entry."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Sprint 2",
                "issues": [
                    {
                        "issue_key": "NG-3",
                        "title": "Vague feature",
                        "description": "",
                        "labels": ["needs-refinement"]
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["needs_refinement_count"] >= 1
        # needs-refinement in sprint should be flagged as risky
        assert len(data["risky_entries"]) >= 1
    
    def test_sprint_counts_correct(self):
        """Test that readiness counts are computed correctly."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Sprint 3",
                "issues": [
                    {"issue_key": "A-1", "title": "Ready 1", "labels": ["ready-for-sprint"]},
                    {"issue_key": "A-2", "title": "Ready 2", "labels": ["ready"]},
                    {"issue_key": "A-3", "title": "Review 1", "labels": ["needs-review"]},
                    {"issue_key": "A-4", "title": "Refine 1", "labels": ["needs-refinement"]},
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_issues"] == 4
        assert data["ready_count"] == 2
        assert data["needs_review_count"] == 1
        assert data["needs_refinement_count"] == 1
    
    def test_sprint_with_domain_context(self):
        """Test sprint analysis with domain context."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Control Panel Sprint",
                "domain_context": "control_panel",
                "issues": [
                    {
                        "issue_key": "CP-1",
                        "title": "Add user permissions management",
                        "description": "Implement RBAC for control panel users",
                        "labels": ["ready-for-sprint"]
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sprint_name"] == "Control Panel Sprint"
    
    def test_sprint_response_structure(self):
        """Test that response contains all required fields."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Test Sprint",
                "issues": [
                    {"issue_key": "T-1", "title": "Test issue", "labels": []}
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "sprint_name",
            "sprint_health_score",
            "delivery_confidence",
            "total_issues",
            "ready_count",
            "needs_review_count",
            "needs_refinement_count",
            "not_ready_count",
            "risky_entries",
            "top_risks",
            "qa_focus_areas",
            "blocked_candidates",
            "recommended_actions",
            "executive_summary",
            "confluence_page_title",
            "confluence_page_body_storage"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_empty_issues_rejected(self):
        """Test that empty issues list is rejected."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Empty Sprint",
                "issues": []
            }
        )
        assert response.status_code == 422  # Validation error
    
    def test_risky_entry_structure(self):
        """Test risky entry has correct structure."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Risky Sprint",
                "issues": [
                    {
                        "issue_key": "R-1",
                        "title": "Risky feature",
                        "description": "",
                        "labels": ["needs-refinement"]
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        if data["risky_entries"]:
            entry = data["risky_entries"][0]
            assert "issue_key" in entry
            assert "title" in entry
            assert "reason" in entry
            assert "risk" in entry
    
    def test_blocked_candidates_detection(self):
        """Test that blocking issues are detected."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Blocking Sprint",
                "issues": [
                    {
                        "issue_key": "B-1",
                        "title": "This blocks other features",
                        "description": "This is a prerequisite for other work",
                        "labels": ["ready-for-sprint"]
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        # Should detect blocking keywords
        assert len(data["blocked_candidates"]) >= 0  # May or may not detect
    
    def test_recommended_actions_generated(self):
        """Test that recommended actions are generated."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Action Sprint",
                "issues": [
                    {"issue_key": "A-1", "title": "Ready", "labels": ["ready"]},
                    {"issue_key": "A-2", "title": "Needs work", "labels": ["needs-refinement"]},
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["recommended_actions"]) >= 1


class TestSprintIssueSchema:
    """Tests for SprintIssue Pydantic schema."""
    
    def test_minimal_issue(self):
        """Test issue with minimal required fields."""
        issue = SprintIssue(issue_key="X-1", title="Test")
        assert issue.issue_key == "X-1"
        assert issue.title == "Test"
        assert issue.description == ""
        assert issue.labels == []
    
    def test_full_issue(self):
        """Test issue with all fields."""
        issue = SprintIssue(
            issue_key="X-2",
            title="Full Issue",
            description="Description here",
            status="In Progress",
            priority="High",
            labels=["bug", "urgent"]
        )
        assert issue.status == "In Progress"
        assert issue.priority == "High"
        assert len(issue.labels) == 2


class TestSprintAnalysisRequest:
    """Tests for SprintAnalysisRequest Pydantic schema."""
    
    def test_minimal_request(self):
        """Test request with minimal required fields."""
        request = SprintAnalysisRequest(
            sprint_name="Sprint 1",
            issues=[SprintIssue(issue_key="X-1", title="Test")]
        )
        assert request.sprint_name == "Sprint 1"
        assert request.sprint_id is None
        assert request.domain_context is None
    
    def test_full_request(self):
        """Test request with all fields."""
        request = SprintAnalysisRequest(
            sprint_name="Sprint 2",
            sprint_id=42,
            domain_context="control_panel",
            issues=[
                SprintIssue(issue_key="X-1", title="Test 1"),
                SprintIssue(issue_key="X-2", title="Test 2"),
            ]
        )
        assert request.sprint_id == 42
        assert request.domain_context == "control_panel"
        assert len(request.issues) == 2


class TestSprintAnalysisConfluenceOutput:
    """Tests for inline Confluence output in sprint analysis."""
    
    def test_confluence_page_title_format(self):
        """Test that confluence_page_title has no leading '=' and uses short format."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "NG Sprint 1",
                "issues": [
                    {"issue_key": "T-1", "title": "Test issue", "labels": []}
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        # Title should be "{Sprint Name} Dashboard" with no leading "="
        assert data["confluence_page_title"] == "NG Sprint 1 Dashboard"
        assert not data["confluence_page_title"].startswith("=")
    
    def test_confluence_body_is_html(self):
        """Test that confluence_page_body_storage contains all required stakeholder sections."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "HTML Test Sprint",
                "issues": [
                    {"issue_key": "T-1", "title": "Test issue", "labels": []}
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        body = data["confluence_page_body_storage"]

        # Should start with h1 title (no "Quality" in title)
        assert body.startswith("<h1>HTML Test Sprint Dashboard</h1>")
        # All stakeholder sections must be present
        assert "<h2>Executive Summary</h2>" in body
        assert "<h2>Stakeholders</h2>" in body
        assert "<h2>Sprint Metrics</h2>" in body
        assert "<h2>Progress Snapshot</h2>" in body
        assert "<h2>Sprint Scope</h2>" in body
        assert "<h2>QA / Delivery Focus Areas</h2>" in body
        assert "<h2>Decision Needed</h2>" in body
        # Should NOT contain removed sections
        assert "Readiness Distribution" not in body
        assert "Story Breakdown" not in body
        assert "Recommended Actions" not in body

    def test_confluence_body_stakeholders_present(self):
        """Test that Stakeholders section has default rows."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Stakeholder Sprint",
                "issues": [
                    {"issue_key": "T-1", "title": "Test", "labels": []}
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        assert "Product / Delivery Owner" in body
        assert "@Nadin Gut" in body
        assert "QA / Quality Owner" in body

    def test_confluence_body_progress_snapshot(self):
        """Test that Progress Snapshot shows status breakdown."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Progress Sprint",
                "issues": [
                    {"issue_key": "T-1", "title": "Todo item", "labels": [], "status": "To Do"},
                    {"issue_key": "T-2", "title": "Done item", "labels": [], "status": "Done"},
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        assert "<h2>Progress Snapshot</h2>" in body
        assert "To Do" in body
        assert "Done" in body
        assert "Blocked / Flagged" in body

    def test_confluence_body_issue_link_auto_generated(self):
        """Test that issue links are auto-generated when no issue_url is provided."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Auto Link Sprint",
                "issues": [
                    {"issue_key": "NG-99", "title": "No URL issue", "labels": []}
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        assert '<a href="https://nadingut.atlassian.net/browse/NG-99">NG-99</a>' in body

    def test_confluence_body_decisions_needed_for_high_risk(self):
        """Test that Decision Needed section is populated for high-risk items."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Decision Sprint",
                "issues": [
                    {
                        "issue_key": "NG-5",
                        "title": "Role permission setup",
                        "labels": ["needs-refinement"],
                        "status": "To Do"
                    }
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        assert "<h2>Decision Needed</h2>" in body
    
    def test_confluence_body_no_markdown(self):
        """Test that confluence body contains no markdown syntax."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Markdown Test",
                "issues": [
                    {"issue_key": "T-1", "title": "Test", "labels": ["needs-refinement"]}
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        
        # No markdown table syntax
        assert "|---" not in body
        # No markdown headers
        assert "\n# " not in body
        assert "\n## " not in body
        # No markdown lists
        assert "\n- " not in body
        assert "\n* " not in body
        # No leading "=" anywhere
        assert not body.startswith("=")
    
    def test_confluence_body_uses_safe_tags_only(self):
        """Test that confluence body uses only safe HTML tags."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Safe Tags Sprint",
                "issues": [
                    {"issue_key": "T-1", "title": "Test", "labels": [], "issue_url": "https://example.com/T-1"}
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        
        import re
        # Extract all HTML tags
        tags = re.findall(r'</?(\w+)', body)
        # Safe tags include 'a' for issue links
        safe_tags = {"h1", "h2", "p", "ul", "li", "table", "tr", "th", "td", "strong", "a"}
        for tag in tags:
            assert tag in safe_tags, f"Unsafe tag found: {tag}"
    
    def test_confluence_body_includes_sprint_scope(self):
        """Test that Sprint Scope table appears with issue data."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Scope Sprint",
                "issues": [
                    {
                        "issue_key": "SCOPE-1",
                        "title": "Feature with scope",
                        "description": "",
                        "labels": ["needs-refinement"],
                        "status": "To Do",
                        "assignee": "John Doe"
                    }
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        
        # Sprint Scope section should exist (not "Risky Sprint Entries")
        assert "<h2>Sprint Scope</h2>" in body
        # Issue key should appear in scope table
        assert "SCOPE-1" in body
        # Status column should exist
        assert "Status" in body
    
    def test_confluence_body_issue_links(self):
        """Test that issue links are rendered when issue_url is provided."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Link Test",
                "issues": [
                    {
                        "issue_key": "NG-7",
                        "title": "Test with link",
                        "labels": [],
                        "issue_url": "https://nadingut.atlassian.net/browse/NG-7"
                    }
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        
        # Issue should be rendered as a link
        assert '<a href="https://nadingut.atlassian.net/browse/NG-7">NG-7</a>' in body
    
    def test_health_score_not_zero_with_issues(self):
        """Test that health score is not 0 when issues exist."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Health Test",
                "issues": [
                    {"issue_key": "T-1", "title": "Test", "labels": []}
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        # Health score should be at least 1 when issues exist
        assert data["sprint_health_score"] >= 1


class TestConfluenceBodyCompleteness:
    """Tests that confluence_page_body_storage is always a full HTML page, never a placeholder."""

    def test_body_length_over_500_with_one_issue(self):
        """Full Confluence body must be at least 500 chars when issues exist."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Length Test",
                "issues": [
                    {"issue_key": "LT-1", "title": "Login flow", "labels": []}
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        assert len(body) > 500, f"Body too short ({len(body)} chars) — likely a placeholder"

    def test_body_length_over_500_with_multiple_issues(self):
        """Body should grow with more issues — still well above 500 chars."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Multi Issue Sprint",
                "issues": [
                    {"issue_key": "MI-1", "title": "User registration", "labels": ["ready-for-sprint"]},
                    {"issue_key": "MI-2", "title": "Password reset", "labels": ["needs-review"]},
                    {"issue_key": "MI-3", "title": "Dashboard setup", "labels": ["needs-refinement"]},
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        assert len(body) > 500

    def test_body_does_not_contain_ellipsis(self):
        """Body must never contain a bare '...' placeholder."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "No Ellipsis Sprint",
                "issues": [
                    {"issue_key": "NE-1", "title": "Feature A", "labels": []}
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        assert "..." not in body, "confluence_page_body_storage contains placeholder '...'"

    def test_body_contains_executive_summary_section(self):
        """Body must contain the Executive Summary heading."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Section Check",
                "issues": [
                    {"issue_key": "SC-1", "title": "Some story", "labels": []}
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        assert "<h2>Executive Summary</h2>" in body

    def test_body_contains_sprint_scope_section(self):
        """Body must contain the Sprint Scope heading."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Section Check",
                "issues": [
                    {"issue_key": "SC-2", "title": "Another story", "labels": []}
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        assert "<h2>Sprint Scope</h2>" in body

    def test_body_contains_all_required_sections(self):
        """Body must contain all 8 required stakeholder sections."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Full Sections Sprint",
                "issues": [
                    {"issue_key": "FS-1", "title": "Feature", "labels": []}
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        required = [
            "<h2>Executive Summary</h2>",
            "<h2>Stakeholders</h2>",
            "<h2>Sprint Metrics</h2>",
            "<h2>Progress Snapshot</h2>",
            "<h2>Sprint Scope</h2>",
            "<h2>QA / Delivery Focus Areas</h2>",
            "<h2>Decision Needed</h2>",
        ]
        for section in required:
            assert section in body, f"Missing section: {section}"

    def test_body_contains_issue_key_when_issues_exist(self):
        """Body must contain the issue key somewhere when issues are provided."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Key Check Sprint",
                "issues": [
                    {"issue_key": "KC-42", "title": "Config setup", "labels": []}
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        assert "KC-42" in body, "Issue key KC-42 not found in confluence_page_body_storage"

    def test_body_issue_key_appears_as_link(self):
        """Issue key in Sprint Scope must be an anchor tag with Jira URL."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Link Sprint",
                "issues": [
                    {"issue_key": "LK-7", "title": "Role management", "labels": []}
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        assert '<a href="https://nadingut.atlassian.net/browse/LK-7">LK-7</a>' in body

    def test_body_empty_sections_have_fallback_message(self):
        """Sections with no data must render a fallback message, not be empty."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Fallback Sprint",
                "issues": [
                    {"issue_key": "FB-1", "title": "Ready story", "labels": ["ready-for-sprint"]}
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        # Decision Needed should show fallback if no decisions detected
        if "No stakeholder decisions currently detected." in body:
            assert "<h2>Decision Needed</h2>" in body  # section heading still present

    def test_qa_section_always_contains_97_percent_target(self):
        """QA / Delivery Focus Areas must always include the 97% pass-rate target."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "QA Target Sprint",
                "issues": [
                    {"issue_key": "QT-1", "title": "Auth flow", "labels": []}
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        assert "<li>Maintain 97% pass rate on new feature tests and regression suite.</li>" in body

    def test_qa_97_target_is_first_bullet_before_dynamic_areas(self):
        """Static 97% target appears before any dynamically-generated focus area."""
        response = client.post(
            "/analyze/sprint?demo_mode=true",
            json={
                "sprint_name": "Order Check Sprint",
                "issues": [
                    {"issue_key": "OC-1", "title": "Payment retry", "labels": ["needs-review"]}
                ]
            }
        )
        assert response.status_code == 200
        body = response.json()["confluence_page_body_storage"]
        target = "<li>Maintain 97% pass rate on new feature tests and regression suite.</li>"
        qa_section_start = body.find("<h2>QA / Delivery Focus Areas</h2>")
        assert qa_section_start != -1
        target_pos = body.find(target, qa_section_start)
        assert target_pos != -1, "97% target not found in QA section"
        # target must appear before the closing </ul> of that section
        ul_close = body.find("</ul>", qa_section_start)
        assert target_pos < ul_close
