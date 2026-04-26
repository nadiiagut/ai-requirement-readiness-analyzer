"""Tests for the FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.api import app


client = TestClient(app)


def test_health_endpoint():
    """Test the health check endpoint returns expected response."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_analyze_endpoint_demo_mode():
    """Test the analyze endpoint with demo mode."""
    response = client.post(
        "/analyze?demo_mode=true",
        json={
            "issue_key": "QA-123",
            "title": "Test requirement",
            "description": "User should be able to do something"
        }
    )
    assert response.status_code == 200
    data = response.json()
    
    assert data["issue_key"] == "QA-123"
    assert "readiness_score" in data
    assert "recommendation" in data
    assert "report" in data
    
    report = data["report"]
    assert "summary" in report
    assert "missing_information" in report
    assert "acceptance_criteria" in report
    assert "suggested_test_scenarios" in report


def test_analyze_endpoint_missing_title():
    """Test the analyze endpoint rejects requests without title."""
    response = client.post(
        "/analyze?demo_mode=true",
        json={
            "description": "User should be able to do something"
        }
    )
    assert response.status_code == 422


def test_analyze_endpoint_missing_description():
    """Test the analyze endpoint rejects requests without description."""
    response = client.post(
        "/analyze?demo_mode=true",
        json={
            "title": "Test requirement"
        }
    )
    assert response.status_code == 422


def test_analyze_endpoint_optional_issue_key():
    """Test the analyze endpoint works without issue_key."""
    response = client.post(
        "/analyze?demo_mode=true",
        json={
            "title": "Test requirement",
            "description": "User should be able to do something"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["issue_key"] is None


def test_analyze_endpoint_jira_like_payload():
    """Test the analyze endpoint accepts Jira-like payload with all fields."""
    response = client.post(
        "/analyze?demo_mode=true",
        json={
            "issue_key": "QA-123",
            "title": "Delayed AC charging",
            "description": "User should be able to delay AC charging by 4 hours",
            "issue_type": "Story",
            "priority": "High",
            "labels": ["ev-charging", "backend"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["issue_key"] == "QA-123"
    assert "readiness_score" in data
    assert "recommendation" in data


def test_jira_comment_endpoint_demo_mode():
    """Test the jira-comment endpoint returns formatted comment."""
    response = client.post(
        "/analyze/jira-comment?demo_mode=true",
        json={
            "issue_key": "QA-456",
            "title": "Test feature",
            "description": "User wants to do something"
        }
    )
    assert response.status_code == 200
    data = response.json()
    
    assert data["issue_key"] == "QA-456"
    assert "jira_comment" in data
    
    comment = data["jira_comment"]
    assert "h3. AI Requirement Readiness Analysis" in comment
    assert "Readiness Score:" in comment
    assert "Recommendation:" in comment


def test_jira_comment_endpoint_contains_sections():
    """Test the jira-comment includes key sections."""
    response = client.post(
        "/analyze/jira-comment?demo_mode=true",
        json={
            "title": "Feature request",
            "description": "Some vague requirement"
        }
    )
    assert response.status_code == 200
    data = response.json()
    comment = data["jira_comment"]
    
    assert "Clarification Questions" in comment or "Missing Information" in comment
    assert "AI Note:" in comment or "Human review" in comment


def test_confluence_page_endpoint_demo_mode():
    """Test the confluence-page endpoint returns page content."""
    response = client.post(
        "/analyze/confluence-page?demo_mode=true",
        json={
            "issue_key": "QA-789",
            "title": "New feature",
            "description": "Detailed feature description"
        }
    )
    assert response.status_code == 200
    data = response.json()
    
    assert data["issue_key"] == "QA-789"
    assert "page_title" in data
    assert "page_body" in data
    assert "QA-789" in data["page_title"]
    assert "Readiness Report" in data["page_title"]


def test_confluence_page_endpoint_contains_xhtml():
    """Test the confluence-page returns valid XHTML structure."""
    response = client.post(
        "/analyze/confluence-page?demo_mode=true",
        json={
            "title": "Test requirement",
            "description": "Test description"
        }
    )
    assert response.status_code == 200
    data = response.json()
    body = data["page_body"]
    
    assert "## Executive Summary" in body
    assert "## Readiness Score" in body
    assert "| Dimension |" in body or "## Risks" in body
    assert "AI Requirement Readiness Analyzer" in body


def test_confluence_page_without_issue_key():
    """Test confluence-page works without issue_key."""
    response = client.post(
        "/analyze/confluence-page?demo_mode=true",
        json={
            "title": "Generic requirement",
            "description": "Some description"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["issue_key"] is None
    assert "Requirement Readiness Report" in data["page_title"]
    assert ":" not in data["page_title"].split("Requirement")[0]
