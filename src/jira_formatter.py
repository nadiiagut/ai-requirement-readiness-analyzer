"""
Jira comment formatter for requirement readiness reports.

Formats reports as plain text for Jira Cloud compatibility.
"""

from typing import List, Optional

from .schemas import RequirementReadinessReport


def _format_recommendation(rec: str) -> str:
    """Convert recommendation enum value to readable uppercase text."""
    mapping = {
        "ready": "READY",
        "needs_review": "NEEDS REVIEW",
        "needs_refinement": "NEEDS REFINEMENT",
        "not_ready": "NOT READY",
    }
    return mapping.get(rec, rec.upper().replace("_", " "))


def _sanitize_issue_key(issue_key: Optional[str]) -> Optional[str]:
    """Remove any accidental prefixes from issue key."""
    if not issue_key:
        return None
    # Strip whitespace and remove leading '=' if present
    sanitized = issue_key.strip().lstrip("=").strip()
    return sanitized if sanitized else None


def format_jira_comment(
    report: RequirementReadinessReport,
    issue_key: Optional[str] = None,
    acceptance_criteria: Optional[List[dict]] = None,
    edge_cases: Optional[List[str]] = None,
    test_scenarios: Optional[List[dict]] = None,
    automation_candidates: Optional[List[str]] = None,
    selected_domain_context: Optional[str] = None,
) -> str:
    """
    Format a readiness report as a Jira Cloud-compatible comment.
    
    Uses plain text formatting that displays correctly in Jira Cloud.
    Avoids legacy wiki markup that doesn't render properly.
    
    Args:
        report: The analyzed requirement report
        issue_key: Optional Jira issue key for reference
        acceptance_criteria: Optional list of AC dicts with given/when/then
        edge_cases: Optional list of edge case strings
        test_scenarios: Optional list of test scenario dicts
        automation_candidates: Optional list of automation candidate strings
        selected_domain_context: Optional domain context used for analysis
        
    Returns:
        Plain text string ready to post as a Jira comment
    """
    lines: list[str] = []
    
    rec = report.recommendation.value if report.recommendation else "unknown"
    rec_display = _format_recommendation(rec)
    
    # Sanitize issue key
    clean_issue_key = _sanitize_issue_key(issue_key)
    
    # Title
    title_suffix = f" — {clean_issue_key}" if clean_issue_key else ""
    lines.append(f"AI Requirement Readiness Analysis{title_suffix}")
    lines.append("")
    
    # Readiness score, recommendation, and domain context
    lines.append(f"Readiness Score: {report.readiness_score}/100")
    lines.append(f"Recommendation: {rec_display}")
    if selected_domain_context:
        lines.append(f"Domain Context: {selected_domain_context}")
    lines.append("")
    
    # Main concerns (top risks)
    all_risks = report.product_risks + report.qa_risks + report.technical_risks
    if all_risks:
        lines.append("Main Concerns:")
        for risk in all_risks[:3]:
            lines.append(f"• {risk}")
        lines.append("")
    
    # Clarification questions
    if report.clarification_questions:
        lines.append("Clarification Questions:")
        for i, q in enumerate(report.clarification_questions[:5], 1):
            lines.append(f"{i}. {q}")
        lines.append("")
    
    # Suggested acceptance criteria
    ac_list = acceptance_criteria or []
    # Also check report's acceptance_criteria if no explicit list provided
    if not ac_list and report.acceptance_criteria:
        # Convert string ACs to simple format
        for i, ac in enumerate(report.acceptance_criteria[:5], 1):
            lines.append(f"AC-{i}: {ac}" if not ac.startswith("AC-") else ac)
        if report.acceptance_criteria:
            lines.insert(len(lines) - len(report.acceptance_criteria[:5]), "Suggested Acceptance Criteria:")
            lines.append("")
    elif ac_list:
        lines.append("Suggested Acceptance Criteria:")
        for ac in ac_list[:5]:
            ac_id = ac.get("id", "AC")
            given = ac.get("given", "")
            when = ac.get("when", "")
            then = ac.get("then", "")
            lines.append(f"{ac_id}:")
            lines.append(f"  Given: {given}")
            lines.append(f"  When: {when}")
            lines.append(f"  Then: {then}")
        lines.append("")
    
    # QA next step
    lines.append("QA Next Step:")
    if report.readiness_score >= 80:
        lines.append("Ready for test planning.")
    elif report.readiness_score >= 60:
        lines.append("Address clarification questions before test planning.")
    elif report.readiness_score >= 40:
        lines.append("Significant gaps — schedule refinement session.")
    else:
        lines.append("Not ready — return to Product Owner for clarification.")
    lines.append("")
    
    # AI note
    lines.append("AI Note:")
    if report.human_review_notes:
        # Filter out score adjustment notes for cleaner output
        notes = [n for n in report.human_review_notes if not n.startswith("Score adjusted:")]
        if notes:
            lines.append(notes[0])
        else:
            lines.append("AI-assisted review. Human PM/QA validation required.")
    else:
        lines.append("AI-assisted review. Human PM/QA validation required.")
    
    return "\n".join(lines)
