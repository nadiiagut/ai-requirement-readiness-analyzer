"""Tests for duplicate requirement detection."""

import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.duplicate_detector import (
    find_duplicates,
    _semantic_similarity,
    _extract_key_phrases,
    _detect_conflict,
    MatchType
)


client = TestClient(app)


class TestSemanticSimilarity:
    """Tests for semantic similarity functions."""

    def test_identical_text_high_similarity(self):
        """Identical text should have high similarity."""
        text = "Create user management feature with roles and permissions"
        similarity = _semantic_similarity(text, text)
        assert similarity >= 0.9

    def test_similar_intent_different_wording(self):
        """Similar intent with different wording should have decent similarity."""
        text1 = "Implement user authentication with login and logout"
        text2 = "Create login functionality for users to authenticate"
        similarity = _semantic_similarity(text1, text2)
        assert similarity >= 0.4

    def test_unrelated_text_low_similarity(self):
        """Unrelated text should have low similarity."""
        text1 = "Create user authentication system"
        text2 = "Generate monthly sales report with charts"
        similarity = _semantic_similarity(text1, text2)
        assert similarity < 0.3

    def test_empty_text_zero_similarity(self):
        """Empty text should have zero similarity."""
        assert _semantic_similarity("", "some text") == 0.0
        assert _semantic_similarity("some text", "") == 0.0
        assert _semantic_similarity("", "") == 0.0

    def test_key_phrase_extraction(self):
        """Test key phrase extraction removes stop words."""
        text = "The user should be able to create a new account"
        phrases = _extract_key_phrases(text)
        
        assert "the" not in phrases
        assert "should" not in phrases
        assert "be" not in phrases
        assert "to" not in phrases
        assert "a" not in phrases
        assert "create" in phrases or "account" in phrases or "new" in phrases


class TestConflictDetection:
    """Tests for conflict detection."""

    def test_detect_enable_disable_conflict(self):
        """Should detect enable/disable conflicts."""
        text1 = "Enable automatic notifications for all users"
        text2 = "Disable automatic notifications by default"
        assert _detect_conflict(text1, text2) is True

    def test_detect_show_hide_conflict(self):
        """Should detect show/hide conflicts."""
        text1 = "Show user email addresses in the profile"
        text2 = "Hide user email addresses from public view"
        assert _detect_conflict(text1, text2) is True

    def test_no_conflict_unrelated(self):
        """Should not detect conflict for unrelated requirements."""
        text1 = "Create user dashboard"
        text2 = "Generate sales report"
        assert _detect_conflict(text1, text2) is False

    def test_no_conflict_complementary(self):
        """Should not detect conflict for complementary requirements."""
        text1 = "Add search functionality to the dashboard"
        text2 = "Add filter functionality to the dashboard"
        assert _detect_conflict(text1, text2) is False


class TestFindDuplicates:
    """Tests for the main find_duplicates function."""

    def test_find_exact_duplicate(self):
        """Should find exact duplicates with high confidence."""
        result = find_duplicates(
            new_issue_key="NEW-1",
            new_title="Implement user login",
            new_description="Users should be able to log in with email and password",
            candidates=[
                {
                    "key": "OLD-1",
                    "title": "Create user login feature",
                    "description": "Allow users to log in using their email and password"
                },
                {
                    "key": "OLD-2",
                    "title": "Generate sales report",
                    "description": "Create monthly sales reports"
                }
            ]
        )
        
        assert len(result["top_matches"]) >= 1
        top_match = result["top_matches"][0]
        assert top_match["issue_key"] == "OLD-1"
        assert top_match["confidence"] >= 0.6

    def test_find_near_duplicate(self):
        """Should find near duplicates with moderate confidence."""
        result = find_duplicates(
            new_issue_key="NEW-1",
            new_title="Add user profile editing",
            new_description="Users should be able to edit their profile information",
            candidates=[
                {
                    "key": "OLD-1",
                    "title": "Update user profile",
                    "description": "Allow users to modify their profile data"
                }
            ]
        )
        
        assert len(result["top_matches"]) >= 1
        assert result["top_matches"][0]["confidence"] >= 0.5

    def test_no_duplicates_found(self):
        """Should return no duplicates for unrelated requirements."""
        result = find_duplicates(
            new_issue_key="NEW-1",
            new_title="Implement payment processing",
            new_description="Process credit card payments for orders",
            candidates=[
                {
                    "key": "OLD-1",
                    "title": "User profile management",
                    "description": "Manage user profiles and settings"
                },
                {
                    "key": "OLD-2",
                    "title": "Email notification system",
                    "description": "Send email notifications to users"
                }
            ],
            threshold=0.5
        )
        
        assert result["duplicates_found"] is False
        assert result["probable_duplicates_count"] == 0

    def test_excludes_self_comparison(self):
        """Should exclude the new issue from comparison."""
        result = find_duplicates(
            new_issue_key="PROJ-123",
            new_title="Test feature",
            new_description="Some description",
            candidates=[
                {
                    "key": "PROJ-123",  # Same key
                    "title": "Test feature",
                    "description": "Some description"
                },
                {
                    "key": "PROJ-456",
                    "title": "Other feature",
                    "description": "Different thing"
                }
            ]
        )
        
        # Should not match itself
        matching_keys = [m["issue_key"] for m in result["top_matches"]]
        assert "PROJ-123" not in matching_keys

    def test_detect_conflicting_requirements(self):
        """Should detect conflicting requirements."""
        result = find_duplicates(
            new_issue_key="NEW-1",
            new_title="Enable automatic email notifications",
            new_description="Automatically send email notifications to all users when events occur",
            candidates=[
                {
                    "key": "OLD-1",
                    "title": "Disable automatic notifications",
                    "description": "Disable automatic email notifications for users by default"
                }
            ],
            threshold=0.3
        )
        
        assert result["conflicts_count"] >= 1 or len(result["top_matches"]) >= 1

    def test_recommendation_for_duplicates(self):
        """Should provide recommendation when duplicates found."""
        result = find_duplicates(
            new_issue_key="NEW-1",
            new_title="Create user authentication",
            new_description="Implement user login and registration with email verification",
            candidates=[
                {
                    "key": "OLD-1",
                    "title": "User authentication system",
                    "description": "Create login and registration for users with email verification"
                }
            ]
        )
        
        assert "recommendation" in result
        assert len(result["recommendation"]) > 0


class TestDuplicatesEndpoint:
    """Tests for the /analyze/duplicates API endpoint."""

    def test_endpoint_basic_request(self):
        """Test basic duplicate check request."""
        response = client.post(
            "/analyze/duplicates",
            json={
                "title": "Implement user dashboard",
                "description": "Create a dashboard for users to view their data",
                "candidates": [
                    {
                        "key": "PROJ-100",
                        "title": "User dashboard feature",
                        "description": "Build dashboard to display user information"
                    },
                    {
                        "key": "PROJ-101",
                        "title": "Admin reporting",
                        "description": "Create admin reports"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "duplicates_found" in data
        assert "top_matches" in data
        assert "recommendation" in data
        assert isinstance(data["top_matches"], list)

    def test_endpoint_with_issue_key(self):
        """Test duplicate check with issue key exclusion."""
        response = client.post(
            "/analyze/duplicates",
            json={
                "issue_key": "PROJ-200",
                "title": "Some feature",
                "description": "Feature description",
                "candidates": [
                    {
                        "key": "PROJ-200",
                        "title": "Some feature",
                        "description": "Feature description"
                    },
                    {
                        "key": "PROJ-201",
                        "title": "Other feature",
                        "description": "Other description"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should not include self-match
        matching_keys = [m["issue_key"] for m in data["top_matches"]]
        assert "PROJ-200" not in matching_keys

    def test_endpoint_custom_threshold(self):
        """Test duplicate check with custom threshold."""
        response = client.post(
            "/analyze/duplicates",
            json={
                "title": "User feature",
                "description": "A feature for users",
                "candidates": [
                    {
                        "key": "PROJ-300",
                        "title": "User functionality",
                        "description": "Functionality for users"
                    }
                ],
                "threshold": 0.8  # Higher threshold
            }
        )
        
        assert response.status_code == 200

    def test_endpoint_finds_probable_duplicate(self):
        """Test that endpoint correctly identifies probable duplicates."""
        response = client.post(
            "/analyze/duplicates",
            json={
                "title": "Implement password reset functionality",
                "description": "Allow users to reset their password via email link",
                "candidates": [
                    {
                        "key": "PROJ-400",
                        "title": "Password reset feature",
                        "description": "Users can reset password through email verification link"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should find this as at least a near-duplicate
        assert len(data["top_matches"]) >= 1
        assert data["top_matches"][0]["confidence"] >= 0.5

    def test_endpoint_response_structure(self):
        """Test that response has correct structure."""
        response = client.post(
            "/analyze/duplicates",
            json={
                "title": "Test requirement",
                "description": "Test description for requirement",
                "candidates": [
                    {
                        "key": "TEST-1",
                        "title": "Another requirement",
                        "description": "Another description"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "duplicates_found" in data
        assert "probable_duplicates_count" in data
        assert "near_duplicates_count" in data
        assert "conflicts_count" in data
        assert "top_matches" in data
        assert "recommendation" in data
        
        assert isinstance(data["duplicates_found"], bool)
        assert isinstance(data["probable_duplicates_count"], int)
        assert isinstance(data["top_matches"], list)

    def test_endpoint_match_structure(self):
        """Test that match objects have correct structure."""
        response = client.post(
            "/analyze/duplicates",
            json={
                "title": "Create export functionality",
                "description": "Export data to CSV and Excel formats",
                "candidates": [
                    {
                        "key": "EXP-1",
                        "title": "Data export feature",
                        "description": "Allow exporting data to CSV and Excel"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if data["top_matches"]:
            match = data["top_matches"][0]
            assert "issue_key" in match
            assert "title" in match
            assert "match_type" in match
            assert "confidence" in match
            assert "reason" in match
            
            assert match["match_type"] in ["duplicate", "near_duplicate", "conflicting", "related"]
            assert 0 <= match["confidence"] <= 1

    def test_endpoint_validation_requires_candidates(self):
        """Test that endpoint requires at least one candidate."""
        response = client.post(
            "/analyze/duplicates",
            json={
                "title": "Test",
                "description": "Test",
                "candidates": []
            }
        )
        
        assert response.status_code == 422  # Validation error

    def test_endpoint_validation_requires_title(self):
        """Test that endpoint requires title."""
        response = client.post(
            "/analyze/duplicates",
            json={
                "description": "Test",
                "candidates": [{"key": "T-1", "title": "Test", "description": ""}]
            }
        )
        
        assert response.status_code == 422  # Validation error

    def test_high_confidence_flagged_as_duplicate(self):
        """Test that high confidence matches are flagged as duplicates."""
        response = client.post(
            "/analyze/duplicates",
            json={
                "title": "User login with email and password authentication",
                "description": "Implement user login functionality allowing users to authenticate with their email address and password credentials",
                "candidates": [
                    {
                        "key": "AUTH-1",
                        "title": "Email and password login for users",
                        "description": "Create login feature for user authentication using email and password"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # This should be detected as a duplicate or near-duplicate
        assert len(data["top_matches"]) >= 1
        top_match = data["top_matches"][0]
        
        # High similarity should result in duplicate detection
        if top_match["confidence"] >= 0.8:
            assert data["duplicates_found"] is True
            assert "DUPLICATE" in data["recommendation"] or "duplicate" in top_match["match_type"]
