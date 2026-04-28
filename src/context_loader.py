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


# Domain classification keyword rules
# Each domain maps to a set of keywords (lowercase) to match against title, description, and labels
DOMAIN_KEYWORDS: dict[str, set[str]] = {
    "cdn_edge_networking": {
        "cdn", "edge", "cache", "caching", "quic", "http3", "http/3",
        "origin", "routing", "purge", "tls", "ssl", "dns", "traffic",
        "edge location", "edge compute", "load balancer", "load balancing",
        "reverse proxy", "proxy", "bandwidth", "latency", "throughput",
        "geo", "geolocation", "pop", "point of presence", "anycast",
        "ddos", "waf", "firewall", "rate limit", "rate-limit",
        "certificate", "https", "http2", "http/2", "origin shield",
        "cache invalidation", "ttl", "vary header", "content delivery",
    },
    "authentication_security": {
        "login", "auth", "authentication", "authorization", "users",
        "roles", "role", "permissions", "permission", "password", "session",
        "access", "access control", "rbac", "abac", "oauth", "oidc", "saml",
        "sso", "single sign-on", "mfa", "2fa", "two-factor", "multi-factor",
        "jwt", "token", "refresh token", "api key", "secret", "credential",
        "identity", "idp", "identity provider", "ldap", "active directory",
        "account", "signup", "sign-up", "register", "logout", "sign-out",
        "password reset", "forgot password", "lockout", "brute force",
    },
    "control_panel": {
        "control panel", "control page", "operator", "admin", "administrator",
        "device", "panel", "industrial", "controls", "dashboard",
        "admin panel", "admin dashboard", "management console",
        "settings page", "configuration page", "system settings",
        "user management", "tenant", "multi-tenant", "back office",
        "backoffice", "operator console", "control interface",
    },
    "ci_cd_delivery": {
        "ci", "cd", "ci/cd", "cicd", "pipeline", "deploy", "deployment",
        "github actions", "gitlab", "gitlab ci", "jenkins", "circleci",
        "travis", "release", "release automation", "build", "build pipeline",
        "artifact", "docker", "container", "kubernetes", "k8s", "helm",
        "terraform", "ansible", "infrastructure as code", "iac",
        "staging", "production", "prod", "environment", "rollback",
        "blue-green", "canary", "rolling update", "continuous integration",
        "continuous delivery", "continuous deployment", "devops",
    },
}


def classify_domain_context(
    title: str,
    description: str,
    labels: list[str] | None = None
) -> str:
    """
    Classify a requirement into the best-matching domain context.
    
    Uses deterministic keyword/label matching. Returns the domain with
    the most keyword matches. Falls back to 'generic_web' if no matches.
    
    Args:
        title: Requirement title or summary
        description: Requirement description
        labels: Optional list of labels/tags
        
    Returns:
        Domain context name (e.g., 'cdn_edge_networking', 'authentication_security')
    """
    # Combine all text for matching
    text = f"{title} {description}".lower()
    labels_lower = [label.lower() for label in (labels or [])]
    
    # Score each domain by keyword matches
    scores: dict[str, int] = {}
    
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            # Check in text
            if keyword in text:
                score += 1
            # Check in labels (higher weight)
            if any(keyword in label for label in labels_lower):
                score += 2
        scores[domain] = score
    
    # Find domain with highest score
    if scores:
        best_domain = max(scores, key=lambda d: scores[d])
        if scores[best_domain] > 0:
            return best_domain
    
    return DEFAULT_CONTEXT


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
