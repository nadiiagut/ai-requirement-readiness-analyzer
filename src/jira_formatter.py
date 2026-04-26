"""
Jira comment formatter for requirement readiness reports.

Formats reports as Atlassian wiki markup for posting to Jira comments.
"""

from typing import Optional

from .schemas import RequirementReadinessReport


def format_jira_comment(report: RequirementReadinessReport, issue_key: Optional[str] = None) -> str:
    """
    Format a readiness report as a Jira-compatible comment.
    
    Uses Atlassian wiki markup for styling. Output is concise and actionable.
    
    Args:
        report: The analyzed requirement report
        issue_key: Optional Jira issue key for reference
        
    Returns:
        Jira wiki markup string ready to post as a comment
    """
    lines: list[str] = []
    
    rec = report.recommendation.value if report.recommendation else "unknown"
    color_map = {
        "ready": "green",
        "needs_refinement": "yellow",
        "high_risk": "red",
        "not_ready": "red"
    }
    color = color_map.get(rec, "grey")
    
    # Title
    title_suffix = f" - {issue_key}" if issue_key else ""
    lines.append(f"h3. AI Requirement Readiness Analysis{title_suffix}")
    lines.append("")
    
    # Readiness score and recommendation
    lines.append(f"*Readiness Score:* {report.readiness_score}/100")
    lines.append(f"*Recommendation:* {{color:{color}}}{rec.replace('_', ' ').title()}{{color}}")
    lines.append("")
    
    # Main concerns (top risks)
    all_risks = report.product_risks + report.qa_risks + report.technical_risks
    if all_risks:
        lines.append("h4. Main Concerns")
        for risk in all_risks[:3]:
            lines.append(f"* (!) {risk}")
        lines.append("")
    
    # Clarification questions
    if report.clarification_questions:
        lines.append("h4. Clarification Questions")
        for q in report.clarification_questions[:5]:
            lines.append(f"* (?) {q}")
        lines.append("")
    
    # QA next step
    lines.append("h4. QA Next Step")
    if report.readiness_score >= 85:
        lines.append("* (/) Ready for test planning")
    elif report.readiness_score >= 70:
        lines.append("* (i) Address clarification questions before test planning")
    elif report.readiness_score >= 50:
        lines.append("* (x) Significant gaps - schedule refinement session")
    else:
        lines.append("* (x) Not ready - return to product owner for clarification")
    lines.append("")
    
    # Human review note
    lines.append("----")
    if report.human_review_notes:
        lines.append(f"_AI Note: {report.human_review_notes[0]}_")
    else:
        lines.append("_AI-generated analysis. Human review recommended before action._")
    
    return "\n".join(lines)
