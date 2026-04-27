"""Tests for acceptance criteria generation endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.api import app


client = TestClient(app)


class TestAcceptanceCriteriaEndpoint:
    """Tests for /analyze/acceptance-criteria endpoint."""

    def test_basic_request(self):
        """Test basic acceptance criteria generation."""
        response = client.post(
            "/analyze/acceptance-criteria",
            json={
                "title": "User Login Feature",
                "description": "Users should be able to log in with email and password"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "acceptance_criteria" in data
        assert "edge_cases" in data
        assert "negative_scenarios" in data
        assert len(data["acceptance_criteria"]) <= 5
        assert len(data["edge_cases"]) <= 5
        assert len(data["negative_scenarios"]) <= 5

    def test_response_structure(self):
        """Test that response has correct structure."""
        response = client.post(
            "/analyze/acceptance-criteria",
            json={
                "title": "Test Feature",
                "description": "Test description"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check top-level fields
        assert "issue_key" in data
        assert "title" in data
        assert "acceptance_criteria" in data
        assert "edge_cases" in data
        assert "negative_scenarios" in data
        assert "domain_context_applied" in data

    def test_acceptance_criterion_structure(self):
        """Test that acceptance criteria have Given/When/Then structure."""
        response = client.post(
            "/analyze/acceptance-criteria",
            json={
                "title": "Create User Account",
                "description": "Allow users to create new accounts"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for ac in data["acceptance_criteria"]:
            assert "id" in ac
            assert "given" in ac
            assert "when" in ac
            assert "then" in ac
            assert ac["id"].startswith("AC-")

    def test_edge_case_structure(self):
        """Test that edge cases have correct structure."""
        response = client.post(
            "/analyze/acceptance-criteria",
            json={
                "title": "File Upload",
                "description": "Upload files to the system"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for ec in data["edge_cases"]:
            assert "id" in ec
            assert "scenario" in ec
            assert "expected_behavior" in ec
            assert ec["id"].startswith("EC-")

    def test_negative_scenario_structure(self):
        """Test that negative scenarios have correct structure."""
        response = client.post(
            "/analyze/acceptance-criteria",
            json={
                "title": "Payment Processing",
                "description": "Process credit card payments"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for ns in data["negative_scenarios"]:
            assert "id" in ns
            assert "scenario" in ns
            assert "expected_behavior" in ns
            assert ns["id"].startswith("NS-")

    def test_with_issue_key(self):
        """Test that issue key is included in response."""
        response = client.post(
            "/analyze/acceptance-criteria",
            json={
                "issue_key": "PROJ-123",
                "title": "Some Feature",
                "description": "Feature description"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["issue_key"] == "PROJ-123"

    def test_control_panel_domain_context(self):
        """Test control panel domain context generates relevant AC."""
        response = client.post(
            "/analyze/acceptance-criteria",
            json={
                "title": "User Management",
                "description": "Admin manages user accounts",
                "domain_context": "control_panel"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["domain_context_applied"] == "control_panel"
        
        # Control panel should mention permissions, audit, etc.
        all_text = str(data).lower()
        assert "permission" in all_text or "authenticated" in all_text

    def test_embedded_device_domain_context(self):
        """Test embedded device domain context generates relevant AC."""
        response = client.post(
            "/analyze/acceptance-criteria",
            json={
                "title": "Sensor Data Processing",
                "description": "Process data from temperature sensor",
                "domain_context": "embedded_device"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["domain_context_applied"] == "embedded_device"
        
        # Embedded should mention device, power, memory, etc.
        all_text = str(data).lower()
        assert "device" in all_text or "power" in all_text or "memory" in all_text

    def test_media_streaming_domain_context(self):
        """Test media streaming domain context generates relevant AC."""
        response = client.post(
            "/analyze/acceptance-criteria",
            json={
                "title": "Video Playback",
                "description": "Stream video content to users",
                "domain_context": "media_streaming"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["domain_context_applied"] == "media_streaming"
        
        # Media streaming should mention playback, DRM, buffering, etc.
        all_text = str(data).lower()
        assert "playback" in all_text or "drm" in all_text or "stream" in all_text

    def test_default_domain_context(self):
        """Test that generic_web is used when no domain specified."""
        response = client.post(
            "/analyze/acceptance-criteria",
            json={
                "title": "Generic Feature",
                "description": "Some generic feature"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["domain_context_applied"] == "generic_web"

    def test_login_keyword_adds_auth_ac(self):
        """Test that login keyword adds authentication-related AC."""
        response = client.post(
            "/analyze/acceptance-criteria",
            json={
                "title": "User Login",
                "description": "Implement login with password"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have auth-related content
        all_text = str(data).lower()
        assert "credential" in all_text or "authenticated" in all_text or "login" in all_text

    def test_upload_keyword_adds_file_ec(self):
        """Test that upload keyword adds file-related edge cases."""
        response = client.post(
            "/analyze/acceptance-criteria",
            json={
                "title": "Document Upload",
                "description": "Upload documents to the system"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have file-related edge cases
        all_text = str(data).lower()
        assert "file" in all_text or "size" in all_text or "format" in all_text

    def test_search_keyword_adds_empty_results_ec(self):
        """Test that search keyword adds no-results edge case."""
        response = client.post(
            "/analyze/acceptance-criteria",
            json={
                "title": "Product Search",
                "description": "Search and filter products"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have search-related edge cases
        all_text = str(data).lower()
        assert "search" in all_text or "results" in all_text or "no results" in all_text

    def test_max_five_items_each(self):
        """Test that response never exceeds 5 items in each category."""
        response = client.post(
            "/analyze/acceptance-criteria",
            json={
                "title": "Complex Feature with login, search, upload, filter",
                "description": "A feature that involves authentication, searching, uploading files, and filtering results"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["acceptance_criteria"]) <= 5
        assert len(data["edge_cases"]) <= 5
        assert len(data["negative_scenarios"]) <= 5

    def test_adf_description_supported(self):
        """Test that ADF description format is supported."""
        adf_description = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Users should be able to upload profile pictures"}
                    ]
                }
            ]
        }
        
        response = client.post(
            "/analyze/acceptance-criteria",
            json={
                "title": "Profile Picture Upload",
                "description": adf_description
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should process ADF and generate results
        assert len(data["acceptance_criteria"]) >= 1

    def test_missing_title_returns_422(self):
        """Test that missing title returns validation error."""
        response = client.post(
            "/analyze/acceptance-criteria",
            json={
                "description": "Some description"
            }
        )
        
        assert response.status_code == 422

    def test_empty_description_still_works(self):
        """Test that empty description still generates results."""
        response = client.post(
            "/analyze/acceptance-criteria",
            json={
                "title": "Some Feature"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["acceptance_criteria"]) >= 1
