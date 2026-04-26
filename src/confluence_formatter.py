"""
Confluence page formatter for requirement readiness reports.

Formats reports as Confluence-compatible content for documentation pages.
"""

from typing import Optional

from .schemas import RequirementReadinessReport


def format_confluence_page(
    report: RequirementReadinessReport,
    issue_key: Optional[str] = None,
    title: Optional[str] = None
) -> dict:
    """
    Format a readiness report as Confluence page content.
    
    Returns a dictionary with page_title and page_body suitable for
    Confluence REST API page creation.
    
    Args:
        report: The analyzed requirement report
        issue_key: Optional Jira issue key for title prefix
        title: Optional custom title (overrides default)
        
    Returns:
        Dictionary with 'page_title' and 'page_body' keys
    """
    # Generate page title
    if title:
        page_title = title
    elif issue_key:
        page_title = f"{issue_key}: Requirement Readiness Report"
    else:
        page_title = "Requirement Readiness Report"
    
    rec = report.recommendation.value if report.recommendation else "unknown"
    
    body_parts: list[str] = []
    
    # Executive summary
    body_parts.append("## Executive Summary")
    body_parts.append("")
    body_parts.append(report.summary)
    body_parts.append("")
    
    # Readiness score
    body_parts.append("## Readiness Score")
    body_parts.append("")
    body_parts.append(f"**Score:** {report.readiness_score}/100")
    body_parts.append(f"**Recommendation:** {rec.replace('_', ' ').title()}")
    body_parts.append("")
    
    # Score breakdown
    body_parts.append("## Score Breakdown")
    body_parts.append("")
    body_parts.append("| Dimension | Score |")
    body_parts.append("|-----------|-------|")
    body_parts.append(f"| Clarity | {report.score_breakdown.clarity}/100 |")
    body_parts.append(f"| Acceptance Criteria Quality | {report.score_breakdown.acceptance_criteria_quality}/100 |")
    body_parts.append(f"| Testability | {report.score_breakdown.testability}/100 |")
    body_parts.append(f"| Edge Case Coverage | {report.score_breakdown.edge_case_coverage}/100 |")
    body_parts.append(f"| Dependency Clarity | {report.score_breakdown.dependency_clarity}/100 |")
    body_parts.append(f"| Risk Visibility | {report.score_breakdown.risk_visibility}/100 |")
    body_parts.append(f"| Observability Expectations | {report.score_breakdown.observability_expectations}/100 |")
    body_parts.append("")
    
    # Rewritten user story
    body_parts.append("## Rewritten User Story")
    body_parts.append("")
    body_parts.append(f"> {report.rewritten_user_story}")
    body_parts.append("")
    
    # Missing information
    if report.missing_information:
        body_parts.append("## Missing Information")
        body_parts.append("")
        for item in report.missing_information:
            body_parts.append(f"- {item}")
        body_parts.append("")
    
    # Acceptance criteria
    if report.acceptance_criteria:
        body_parts.append("## Acceptance Criteria")
        body_parts.append("")
        for ac in report.acceptance_criteria:
            body_parts.append(f"- {ac}")
        body_parts.append("")
    
    # Edge cases
    if report.edge_cases:
        body_parts.append("## Edge Cases")
        body_parts.append("")
        for ec in report.edge_cases:
            body_parts.append(f"- {ec}")
        body_parts.append("")
    
    # Risks
    all_risks_exist = report.product_risks or report.qa_risks or report.technical_risks
    if all_risks_exist:
        body_parts.append("## Risks")
        body_parts.append("")
        body_parts.append("| Category | Risk |")
        body_parts.append("|----------|------|")
        for risk in report.product_risks:
            body_parts.append(f"| Product | {risk} |")
        for risk in report.qa_risks:
            body_parts.append(f"| QA | {risk} |")
        for risk in report.technical_risks:
            body_parts.append(f"| Technical | {risk} |")
        body_parts.append("")
    
    # Suggested test scenarios
    if report.suggested_test_scenarios:
        body_parts.append("## Suggested Test Scenarios")
        body_parts.append("")
        body_parts.append("| Title | Type | Priority | Description |")
        body_parts.append("|-------|------|----------|-------------|")
        for s in report.suggested_test_scenarios:
            body_parts.append(f"| {s.title} | {s.type.value} | {s.priority.value} | {s.description} |")
        body_parts.append("")
    
    # Automation candidates
    if report.automation_candidates:
        body_parts.append("## Automation Candidates")
        body_parts.append("")
        for ac in report.automation_candidates:
            body_parts.append(f"- {ac}")
        body_parts.append("")
    
    # Clarification questions
    if report.clarification_questions:
        body_parts.append("## Clarification Questions")
        body_parts.append("")
        for q in report.clarification_questions:
            body_parts.append(f"- {q}")
        body_parts.append("")
    
    # Human review notes
    if report.human_review_notes:
        body_parts.append("## Human Review Notes")
        body_parts.append("")
        for note in report.human_review_notes:
            body_parts.append(f"- {note}")
        body_parts.append("")
    
    # Footer
    body_parts.append("---")
    body_parts.append("")
    body_parts.append("*Generated by AI Requirement Readiness Analyzer*")
    
    page_body = "\n".join(body_parts)
    
    return {
        "page_title": page_title,
        "page_body": page_body
    }
