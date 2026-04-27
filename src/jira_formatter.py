"""
Jira comment formatter for requirement readiness reports.

Formats reports as plain text for Jira Cloud compatibility.
"""

from typing import Optional

from .schemas import RequirementReadinessReport


def _format_recommendation(rec: str) -> str:
    """Convert recommendation enum value to readable uppercase text."""
    mapping = {
        "ready": "READY",
        "needs_refinement": "NEEDS REFINEMENT",
        "high_risk": "HIGH RISK",
        "not_ready": "NOT READY",
    }
    return mapping.get(rec, rec.upper().replace("_", " "))


def format_jira_comment(report: RequirementReadinessReport, issue_key: Optional[str] = None) -> str:
    """
    Format a readiness report as a Jira Cloud-compatible comment.
    
    Uses plain text formatting that displays correctly in Jira Cloud.
    Avoids legacy wiki markup that doesn't render properly.
    
    Args:
        report: The analyzed requirement report
        issue_key: Optional Jira issue key for reference
        
    Returns:
        Plain text string ready to post as a Jira comment
    """
    lines: list[str] = []
    
    rec = report.recommendation.value if report.recommendation else "unknown"
    rec_display = _format_recommendation(rec)
    
    # Title
    title_suffix = f" — {issue_key}" if issue_key else ""
    lines.append(f"AI Requirement Readiness Analysis{title_suffix}")
    lines.append("")
    
    # Readiness score and recommendation
    lines.append(f"Readiness Score: {report.readiness_score}/100")
    lines.append(f"Recommendation: {rec_display}")
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
    
    # QA next step
    lines.append("QA Next Step:")
    if report.readiness_score >= 85:
        lines.append("Ready for test planning.")
    elif report.readiness_score >= 70:
        lines.append("Address clarification questions before test planning.")
    elif report.readiness_score >= 50:
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
