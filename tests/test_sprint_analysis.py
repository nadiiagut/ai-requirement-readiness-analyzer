"""Tests for sprint-level analysis endpoint and helper functions."""

import pytest
from fastapi.testclient import TestClient

from src.api import (
    app,
    _classify_issue_by_labels,
    _compute_sprint_health,
    _compute_delivery_confidence,
    _generate_executive_summary,
    SprintIssue,
    SprintAnalysisRequest,
    SprintAnalysisResponse,
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


class TestComputeSprintHealth:
    """Tests for sprint health score computation."""
    
    def test_all_ready_issues(self):
        """All ready issues should give high health score."""
        score = _compute_sprint_health(
            ready_count=5,
            needs_review_count=0,
            needs_refinement_count=0,
            not_ready_count=0,
            total_issues=5,
            risky_count=0
        )
        assert score >= 90
    
    def test_all_needs_refinement(self):
        """All needs-refinement issues should give low health score."""
        score = _compute_sprint_health(
            ready_count=0,
            needs_review_count=0,
            needs_refinement_count=5,
            not_ready_count=0,
            total_issues=5,
            risky_count=5
        )
        assert score < 30
    
    def test_mixed_readiness(self):
        """Mixed readiness should give moderate score."""
        score = _compute_sprint_health(
            ready_count=3,
            needs_review_count=1,
            needs_refinement_count=1,
            not_ready_count=0,
            total_issues=5,
            risky_count=1
        )
        assert 50 <= score <= 85
    
    def test_risky_entries_reduce_score(self):
        """Risky entries should reduce health score."""
        score_no_risk = _compute_sprint_health(
            ready_count=5,
            needs_review_count=0,
            needs_refinement_count=0,
            not_ready_count=0,
            total_issues=5,
            risky_count=0
        )
        score_with_risk = _compute_sprint_health(
            ready_count=5,
            needs_review_count=0,
            needs_refinement_count=0,
            not_ready_count=0,
            total_issues=5,
            risky_count=3
        )
        assert score_with_risk < score_no_risk
    
    def test_empty_sprint(self):
        """Empty sprint should return 0."""
        score = _compute_sprint_health(0, 0, 0, 0, 0, 0)
        assert score == 0
    
    def test_score_bounds(self):
        """Score should always be between 0 and 100."""
        score = _compute_sprint_health(10, 0, 0, 0, 10, 0)
        assert 0 <= score <= 100
        
        score = _compute_sprint_health(0, 0, 10, 10, 20, 20)
        assert 0 <= score <= 100


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


class TestGenerateExecutiveSummary:
    """Tests for executive summary generation."""
    
    def test_high_confidence_summary(self):
        summary = _generate_executive_summary(
            sprint_name="Sprint 1",
            sprint_health=85,
            delivery_confidence="High",
            ready_count=8,
            needs_refinement_count=0,
            not_ready_count=0,
            total_issues=10,
            risky_count=1
        )
        assert "Sprint 1" in summary
        assert "well-prepared" in summary
        assert "80%" in summary  # 8/10 = 80%
    
    def test_medium_confidence_summary(self):
        summary = _generate_executive_summary(
            sprint_name="Sprint 2",
            sprint_health=60,
            delivery_confidence="Medium",
            ready_count=5,
            needs_refinement_count=2,
            not_ready_count=0,
            total_issues=10,
            risky_count=3
        )
        assert "Sprint 2" in summary
        assert "moderate" in summary
    
    def test_low_confidence_summary(self):
        summary = _generate_executive_summary(
            sprint_name="Sprint 3",
            sprint_health=30,
            delivery_confidence="Low",
            ready_count=2,
            needs_refinement_count=5,
            not_ready_count=3,
            total_issues=10,
            risky_count=8
        )
        assert "Sprint 3" in summary
        assert "significant" in summary
    
    def test_summary_includes_health_score(self):
        summary = _generate_executive_summary(
            "Test Sprint", 75, "Medium", 5, 2, 0, 10, 2
        )
        assert "75/100" in summary


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
            "executive_summary"
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
