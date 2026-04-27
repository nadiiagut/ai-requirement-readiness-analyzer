"""Tests for domain context injection feature."""

import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.context_loader import load_context, list_available_contexts, DomainContext
from src.prompt_builder import PromptBuilder


client = TestClient(app)


class TestContextLoader:
    """Tests for context_loader module."""

    def test_list_available_contexts(self):
        """Test that available contexts are listed."""
        contexts = list_available_contexts()
        assert "generic_web" in contexts
        assert "control_panel" in contexts
        assert "embedded_device" in contexts
        assert "media_streaming" in contexts

    def test_load_generic_web_context(self):
        """Test loading generic_web context."""
        ctx = load_context("generic_web")
        assert ctx.name == "generic_web"
        assert len(ctx.focus_areas) > 0
        assert len(ctx.risk_categories) > 0

    def test_load_control_panel_context(self):
        """Test loading control_panel context."""
        ctx = load_context("control_panel")
        assert ctx.name == "control_panel"
        assert any("RBAC" in area for area in ctx.focus_areas)
        assert any("audit" in area.lower() for area in ctx.focus_areas)

    def test_load_embedded_device_context(self):
        """Test loading embedded_device context."""
        ctx = load_context("embedded_device")
        assert ctx.name == "embedded_device"
        assert any("memory" in area.lower() for area in ctx.focus_areas)
        assert any("real-time" in area.lower() for area in ctx.focus_areas)

    def test_load_nonexistent_context_falls_back_to_default(self):
        """Test that nonexistent context falls back to generic_web."""
        ctx = load_context("nonexistent_context")
        assert ctx.name == "generic_web"

    def test_load_none_context_uses_default(self):
        """Test that None context loads generic_web."""
        ctx = load_context(None)
        assert ctx.name == "generic_web"

    def test_context_to_prompt_section(self):
        """Test that context generates valid prompt section."""
        ctx = load_context("control_panel")
        prompt_section = ctx.to_prompt_section()
        
        assert "Domain Context: control_panel" in prompt_section
        assert "Focus Areas" in prompt_section
        assert "RBAC" in prompt_section
        assert "Avoid These Assumptions" in prompt_section


class TestPromptBuilderWithContext:
    """Tests for PromptBuilder domain context injection."""

    def test_prompt_includes_context_section(self):
        """Test that prompt includes context when specified."""
        builder = PromptBuilder()
        prompt = builder.build_prompt(
            "Create user management feature",
            domain_context="control_panel"
        )
        
        assert "Domain Context: control_panel" in prompt
        assert "RBAC" in prompt

    def test_prompt_without_context_uses_default(self):
        """Test that prompt without context uses generic_web."""
        builder = PromptBuilder()
        prompt = builder.build_prompt("Create user management feature")
        
        assert "Domain Context: generic_web" in prompt

    def test_different_contexts_produce_different_prompts(self):
        """Test that different contexts produce different prompts."""
        builder = PromptBuilder()
        requirement = "Handle data processing"
        
        prompt_generic = builder.build_prompt(requirement, domain_context="generic_web")
        prompt_embedded = builder.build_prompt(requirement, domain_context="embedded_device")
        
        # They should be different
        assert prompt_generic != prompt_embedded
        # Embedded should have memory/resource concerns
        assert "memory" in prompt_embedded.lower() or "resource" in prompt_embedded.lower()


class TestAPIWithDomainContext:
    """Tests for API endpoints with domain context."""

    def test_analyze_with_control_panel_context(self):
        """Test analyze endpoint with control_panel context."""
        response = client.post(
            "/analyze?demo_mode=true",
            json={
                "title": "User management for control panel",
                "description": "Create a comprehensive user management system for the control panel. The system should support admin and operator roles with different permission levels. Users need to be able to log in and perform actions based on their assigned roles.",
                "domain_context": "control_panel"
            }
        )
        assert response.status_code == 200
        data = response.json()
        report = data["report"]
        
        # Should have RBAC/security focused content
        all_text = str(report).lower()
        assert any(term in all_text for term in ["rbac", "permission", "role", "audit", "session"])

    def test_analyze_with_generic_context(self):
        """Test analyze endpoint with generic_web context."""
        response = client.post(
            "/analyze?demo_mode=true",
            json={
                "title": "User management for control panel",
                "description": "Create a comprehensive user management system for the control panel. The system should support admin and operator roles with different permission levels. Users need to be able to log in and perform actions based on their assigned roles.",
                "domain_context": "generic_web"
            }
        )
        assert response.status_code == 200
        data = response.json()
        report = data["report"]
        
        # Should have generic web content
        all_text = str(report).lower()
        assert any(term in all_text for term in ["scope", "user", "acceptance"])

    def test_same_requirement_different_context_different_output(self):
        """Test that same requirement with different context produces different analysis."""
        requirement = {
            "title": "User management for control panel",
            "description": "Create a comprehensive user management system for the control panel. The system should support admin and operator roles with different permission levels. Users need to be able to log in and perform actions based on their assigned roles."
        }
        
        # Without context (defaults to generic_web)
        response_generic = client.post(
            "/analyze?demo_mode=true",
            json={**requirement, "domain_context": "generic_web"}
        )
        
        # With control_panel context
        response_control = client.post(
            "/analyze?demo_mode=true",
            json={**requirement, "domain_context": "control_panel"}
        )
        
        assert response_generic.status_code == 200
        assert response_control.status_code == 200
        
        generic_report = response_generic.json()["report"]
        control_report = response_control.json()["report"]
        
        # The reports should be different
        assert generic_report["summary"] != control_report["summary"]
        
        # Control panel should mention security-specific concerns
        control_questions = " ".join(control_report["clarification_questions"]).lower()
        assert any(term in control_questions for term in ["permission", "role", "audit", "session", "password"])
        
        # Control panel should have security-focused missing info
        control_missing = " ".join(control_report["missing_information"]).lower()
        assert any(term in control_missing for term in ["rbac", "permission", "audit", "session", "password"])

    def test_embedded_context_focuses_on_hardware(self):
        """Test that embedded_device context focuses on hardware concerns."""
        response = client.post(
            "/analyze?demo_mode=true",
            json={
                "title": "Implement sensor data collection",
                "description": "Collect temperature sensor data from the hardware sensors and store the readings for later retrieval and analysis. The system should periodically poll sensors and aggregate data efficiently.",
                "domain_context": "embedded_device"
            }
        )
        assert response.status_code == 200
        report = response.json()["report"]
        
        all_text = str(report).lower()
        # Should have embedded/hardware concerns
        assert any(term in all_text for term in ["memory", "hardware", "power", "firmware", "resource"])

    def test_jira_comment_with_context(self):
        """Test jira-comment endpoint respects domain context."""
        response = client.post(
            "/analyze/jira-comment?demo_mode=true",
            json={
                "issue_key": "CTRL-123",
                "title": "User role management",
                "description": "Implement user roles for system access control. The feature should allow administrators to define roles, assign permissions, and manage user access to different parts of the control panel.",
                "domain_context": "control_panel"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Jira comment should reflect control panel concerns
        comment = data["jira_comment"].lower()
        assert any(term in comment for term in ["rbac", "permission", "role", "audit", "session"])

    def test_context_field_is_optional(self):
        """Test that domain_context field is optional."""
        response = client.post(
            "/analyze?demo_mode=true",
            json={
                "title": "Some feature",
                "description": "Implement something useful for the users."
            }
        )
        assert response.status_code == 200
        # Should work without domain_context field

    def test_invalid_context_falls_back_gracefully(self):
        """Test that invalid context name falls back to default."""
        response = client.post(
            "/analyze?demo_mode=true",
            json={
                "title": "Some feature",
                "description": "Implement something useful for the users.",
                "domain_context": "invalid_nonexistent_context"
            }
        )
        assert response.status_code == 200
        # Should work with fallback to generic_web
