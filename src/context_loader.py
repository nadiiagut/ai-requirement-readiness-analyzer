"""
Domain context loader for requirement analysis.

Loads YAML context files that influence LLM analysis based on product domain.
"""

import os
from pathlib import Path
from typing import Optional

import yaml


CONTEXTS_DIR = Path(__file__).parent / "contexts"
DEFAULT_CONTEXT = "generic_web"


class DomainContext:
    """Represents a loaded domain context."""
    
    def __init__(self, name: str, data: dict):
        self.name = name
        self.description = data.get("description", "")
        self.focus_areas = data.get("focus_areas", [])
        self.risk_categories = data.get("risk_categories", [])
        self.typical_concerns = data.get("typical_concerns", [])
        self.avoid_assumptions = data.get("avoid_assumptions", [])
        self.clarification_priorities = data.get("clarification_priorities", [])
    
    def to_prompt_section(self) -> str:
        """Format context as a prompt section for the LLM."""
        lines = [
            f"## Domain Context: {self.name}",
            f"{self.description}",
            "",
        ]
        
        if self.focus_areas:
            lines.append("### Focus Areas")
            lines.append("Prioritize analysis of these aspects:")
            for item in self.focus_areas:
                lines.append(f"- {item}")
            lines.append("")
        
        if self.risk_categories:
            lines.append("### Domain-Specific Risks")
            lines.append("Look for risks in these categories:")
            for item in self.risk_categories:
                lines.append(f"- {item}")
            lines.append("")
        
        if self.typical_concerns:
            lines.append("### Typical Concerns")
            lines.append("Consider these domain-specific concerns:")
            for item in self.typical_concerns:
                lines.append(f"- {item}")
            lines.append("")
        
        if self.avoid_assumptions:
            lines.append("### Avoid These Assumptions")
            lines.append("Do NOT assume or suggest:")
            for item in self.avoid_assumptions:
                lines.append(f"- {item}")
            lines.append("")
        
        if self.clarification_priorities:
            lines.append("### Clarification Priorities")
            lines.append("Prioritize clarification questions about:")
            for item in self.clarification_priorities:
                lines.append(f"- {item}")
            lines.append("")
        
        return "\n".join(lines)


def list_available_contexts() -> list[str]:
    """Return list of available context names."""
    contexts = []
    if CONTEXTS_DIR.exists():
        for f in CONTEXTS_DIR.glob("*.yaml"):
            contexts.append(f.stem)
    return sorted(contexts)


def load_context(context_name: Optional[str] = None) -> DomainContext:
    """
    Load a domain context by name.
    
    Args:
        context_name: Name of context to load (without .yaml extension).
                     If None or not found, defaults to generic_web.
    
    Returns:
        DomainContext object with loaded data.
    """
    name = context_name or DEFAULT_CONTEXT
    context_file = CONTEXTS_DIR / f"{name}.yaml"
    
    # Fall back to default if context doesn't exist
    if not context_file.exists():
        context_file = CONTEXTS_DIR / f"{DEFAULT_CONTEXT}.yaml"
        name = DEFAULT_CONTEXT
    
    # If even default doesn't exist, return empty context
    if not context_file.exists():
        return DomainContext(name, {})
    
    with open(context_file, "r") as f:
        data = yaml.safe_load(f) or {}
    
    return DomainContext(name, data)
