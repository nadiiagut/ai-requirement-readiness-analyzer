"""
FastAPI service for AI Requirement Readiness Analyzer.

Provides REST API endpoints for requirement analysis,
designed for integration with n8n, Jira automation, and other tools.
"""

import json
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .llm_client import LLMClientError, MissingAPIKeyError, analyze_requirement
from .prompt_builder import PromptBuilder
from .schemas import RequirementReadinessReport
from .jira_formatter import format_jira_comment
from .confluence_formatter import format_confluence_page


app = FastAPI(
    title="AI Requirement Readiness Analyzer",
    description="Analyze product requirements and get structured readiness reports",
    version="1.0.0",
)


def _assess_input_quality(title: str, description: str) -> dict:
    """
    Assess the quality of requirement input and return quality metrics.
    
    Returns dict with:
        - quality_level: 'insufficient', 'poor', 'minimal', 'adequate'
        - issues: list of specific problems found
        - max_score: maximum achievable readiness score given input quality
    """
    issues = []
    
    title_clean = title.strip() if title else ""
    desc_clean = description.strip() if description else ""
    
    title_words = len(title_clean.split()) if title_clean else 0
    desc_words = len(desc_clean.split()) if desc_clean else 0
    
    # Check for empty/missing description
    if not desc_clean:
        issues.append("No description provided")
    elif desc_words < 5:
        issues.append("Description is too short (less than 5 words)")
    
    # Check for minimal title
    if not title_clean:
        issues.append("No title provided")
    elif title_words == 1:
        issues.append("Title is only one word")
    elif title_words < 3:
        issues.append("Title is too brief (less than 3 words)")
    
    # Check for placeholder/generic content
    generic_titles = {"test", "testing", "todo", "tbd", "placeholder", "temp", "fix", "update", "change"}
    if title_clean.lower() in generic_titles:
        issues.append("Title appears to be a placeholder")
    
    # Determine quality level and max achievable score
    if not desc_clean or not title_clean:
        quality_level = "insufficient"
        max_score = 5
    elif desc_words < 5 or title_words == 1:
        quality_level = "poor"
        max_score = 15
    elif desc_words < 15 or title_words < 3:
        quality_level = "minimal"
        max_score = 30
    else:
        quality_level = "adequate"
        max_score = 100
    
    return {
        "quality_level": quality_level,
        "issues": issues,
        "max_score": max_score,
        "title_words": title_words,
        "desc_words": desc_words,
    }


class AnalyzeRequest(BaseModel):
    """Request body for /analyze endpoint. Accepts Jira-like payload."""
    issue_key: Optional[str] = Field(
        default=None,
        description="Jira issue key (e.g., QA-123)",
        json_schema_extra={"example": "QA-123"}
    )
    title: str = Field(
        description="Requirement title or summary",
        json_schema_extra={"example": "Delayed AC charging"}
    )
    description: str = Field(
        description="Full requirement description",
        json_schema_extra={"example": "User should be able to delay AC charging by 4 hours..."}
    )
    issue_type: Optional[str] = Field(
        default=None,
        description="Jira issue type (e.g., Story, Bug, Task)",
        json_schema_extra={"example": "Story"}
    )
    priority: Optional[str] = Field(
        default=None,
        description="Jira priority (e.g., High, Medium, Low)",
        json_schema_extra={"example": "High"}
    )
    labels: Optional[List[str]] = Field(
        default=None,
        description="Jira labels",
        json_schema_extra={"example": ["ev-charging", "backend"]}
    )


class AnalyzeResponse(BaseModel):
    """Response body for /analyze endpoint."""
    issue_key: Optional[str] = None
    readiness_score: int
    recommendation: str
    report: RequirementReadinessReport


class HealthResponse(BaseModel):
    """Response body for /health endpoint."""
    status: str
    version: str


class JiraCommentResponse(BaseModel):
    """Response body for /analyze/jira-comment endpoint."""
    issue_key: Optional[str] = None
    jira_comment: str


class ConfluencePageResponse(BaseModel):
    """Response body for /analyze/confluence-page endpoint."""
    issue_key: Optional[str] = None
    page_title: str
    page_body: str


def _get_demo_response(title: str, description: str) -> str:
    """
    Generate a demo response based on input quality assessment.
    
    Returns stricter scores for insufficient/poor quality input.
    """
    requirement_text = f"{title}\n\n{description}"
    quality = _assess_input_quality(title, description)
    
    if quality["quality_level"] == "insufficient":
        # No description or no title - this is not a valid requirement
        demo_data = {
            "original_requirement": requirement_text,
            "summary": "This item cannot be analyzed as a requirement. Essential information is missing.",
            "rewritten_user_story": "Cannot generate - insufficient information provided.",
            "readiness_score": 5,
            "recommendation": "not_ready",
            "score_breakdown": {
                "clarity": 5,
                "acceptance_criteria_quality": 0,
                "testability": 0,
                "edge_case_coverage": 0,
                "dependency_clarity": 0,
                "risk_visibility": 0,
                "observability_expectations": 0
            },
            "missing_information": quality["issues"] + [
                "A requirement must have both a meaningful title and description",
                "Cannot assess readiness without basic requirement content"
            ],
            "acceptance_criteria": [],
            "edge_cases": [],
            "product_risks": [
                "This is not a valid requirement - cannot estimate effort or risk",
                "Development cannot proceed without requirement definition"
            ],
            "qa_risks": [
                "Cannot create any test cases without requirement content",
                "No basis for test planning"
            ],
            "technical_risks": [
                "Cannot assess technical feasibility without requirements"
            ],
            "suggested_test_scenarios": [],
            "automation_candidates": [],
            "clarification_questions": [
                "What is this requirement about?",
                "What should the system do?",
                "Who is the user and what is their goal?"
            ],
            "human_review_notes": [
                "BLOCKED: This item has no description and cannot be analyzed",
                "Action required: Add a detailed description before analysis"
            ]
        }
    elif quality["quality_level"] == "poor":
        # One-word title or very short description
        demo_data = {
            "original_requirement": requirement_text,
            "summary": "This requirement is too vague to analyze meaningfully. Only a brief title or minimal description was provided.",
            "rewritten_user_story": "Cannot generate a proper user story from minimal input.",
            "readiness_score": 10,
            "recommendation": "not_ready",
            "score_breakdown": {
                "clarity": 15,
                "acceptance_criteria_quality": 5,
                "testability": 5,
                "edge_case_coverage": 0,
                "dependency_clarity": 10,
                "risk_visibility": 5,
                "observability_expectations": 0
            },
            "missing_information": quality["issues"] + [
                "Detailed description of what the feature should do",
                "User context and goals",
                "Acceptance criteria",
                "Success metrics"
            ],
            "acceptance_criteria": [
                "[CANNOT DETERMINE] No acceptance criteria can be inferred from this input"
            ],
            "edge_cases": [],
            "product_risks": [
                "Requirement is too vague to estimate scope or effort",
                "High risk of misalignment between expectation and delivery",
                "Cannot validate feature value without defined goals"
            ],
            "qa_risks": [
                "Cannot write meaningful test cases",
                "No clear pass/fail criteria",
                "Testing scope undefined"
            ],
            "technical_risks": [
                "Cannot assess implementation complexity",
                "Unknown dependencies and constraints"
            ],
            "suggested_test_scenarios": [],
            "automation_candidates": [],
            "clarification_questions": [
                "What specific functionality is being requested?",
                "What problem does this solve for the user?",
                "What are the expected inputs and outputs?",
                "What are the acceptance criteria?"
            ],
            "human_review_notes": [
                "BLOCKED: Requirement lacks sufficient detail for analysis",
                "The title and description are too brief to assess readiness",
                "Action required: Expand the description with specific details"
            ]
        }
    elif quality["quality_level"] == "minimal":
        # Short but present content
        demo_data = {
            "original_requirement": requirement_text,
            "summary": "This requirement provides limited information. Key details about scope, users, and success criteria are missing.",
            "rewritten_user_story": "As a user, I want [unclear feature] so that [unknown benefit].",
            "readiness_score": 25,
            "recommendation": "not_ready",
            "score_breakdown": {
                "clarity": 30,
                "acceptance_criteria_quality": 15,
                "testability": 20,
                "edge_case_coverage": 10,
                "dependency_clarity": 25,
                "risk_visibility": 20,
                "observability_expectations": 15
            },
            "missing_information": quality["issues"] + [
                "Detailed feature description",
                "User personas and roles",
                "Specific acceptance criteria",
                "Performance expectations",
                "Error handling requirements"
            ],
            "acceptance_criteria": [
                "[NEEDS DEFINITION] Acceptance criteria cannot be determined from this input"
            ],
            "edge_cases": [
                "Edge cases cannot be identified without more detail"
            ],
            "product_risks": [
                "Scope is unclear - high risk of scope creep",
                "User needs not well defined",
                "Success criteria missing"
            ],
            "qa_risks": [
                "Limited basis for test case design",
                "Cannot define test coverage",
                "Pass/fail criteria unclear"
            ],
            "technical_risks": [
                "Implementation approach uncertain",
                "Dependencies unknown"
            ],
            "suggested_test_scenarios": [
                {"title": "Basic functionality", "type": "functional", "priority": "high", "description": "Verify basic feature works - details TBD"}
            ],
            "automation_candidates": [],
            "clarification_questions": [
                "Can you provide more detail about what this feature should do?",
                "Who are the users and what are their goals?",
                "What are the specific acceptance criteria?",
                "What happens in error scenarios?"
            ],
            "human_review_notes": [
                "Requirement needs more detail before development can begin",
                "Consider a refinement session to flesh out requirements"
            ]
        }
    else:
        # Adequate input - standard demo response
        demo_data = {
            "original_requirement": requirement_text,
            "summary": "This requirement provides a foundation but lacks specifics about scope, acceptance criteria, and edge cases. Clarification needed before development.",
            "rewritten_user_story": "As a user, I want to perform the described action, so that the expected outcome can be achieved and validated against defined goals.",
            "readiness_score": 34,
            "recommendation": "not_ready",
            "score_breakdown": {
                "clarity": 40,
                "acceptance_criteria_quality": 30,
                "testability": 35,
                "edge_case_coverage": 25,
                "dependency_clarity": 45,
                "risk_visibility": 35,
                "observability_expectations": 25
            },
            "missing_information": [
                "Specific scope and boundary of this feature",
                "Target users and their roles",
                "Success criteria and acceptance conditions",
                "Dependencies on other systems or features",
                "Performance expectations",
                "Error handling requirements"
            ],
            "acceptance_criteria": [
                "[ASSUMPTION] Feature can be enabled/disabled by authorized users",
                "[ASSUMPTION] Invalid inputs are rejected with clear error messages",
                "[NEEDS CLARIFICATION] Define specific success conditions"
            ],
            "edge_cases": [
                "Invalid input format or out-of-range values",
                "Concurrent access by multiple users",
                "System under high load",
                "Network interruption during processing"
            ],
            "product_risks": [
                "Scope creep due to vague requirements",
                "No defined user persona",
                "Missing success metrics"
            ],
            "qa_risks": [
                "Cannot write deterministic tests without specific acceptance criteria",
                "Performance testing requires baseline metrics"
            ],
            "technical_risks": [
                "Potential integration issues",
                "Unknown dependencies may cause delays"
            ],
            "suggested_test_scenarios": [
                {"title": "Basic functionality test", "type": "functional", "priority": "high", "description": "Verify core feature works with valid inputs"},
                {"title": "Input validation test", "type": "functional", "priority": "high", "description": "Verify invalid inputs are rejected"},
                {"title": "Error recovery test", "type": "negative", "priority": "medium", "description": "Verify graceful handling of failures"}
            ],
            "automation_candidates": [
                "API tests for core endpoints",
                "Regression test suite"
            ],
            "clarification_questions": [
                "What is the exact scope of this feature?",
                "Who are the primary users?",
                "What are the specific acceptance criteria?",
                "What dependencies exist?",
                "What are the performance requirements?"
            ],
            "human_review_notes": [
                "This requirement needs clarification before development",
                "Recommend a refinement session to define scope and acceptance criteria"
            ]
        }
    
    return json.dumps(demo_data, indent=2)


def _analyze_requirement(request: AnalyzeRequest, demo_mode: bool, provider: str) -> RequirementReadinessReport:
    """Core analysis logic shared by all endpoints."""
    requirement_text = f"{request.title}\n\n{request.description}"
    
    if demo_mode:
        raw_json = _get_demo_response(request.title, request.description)
    else:
        try:
            prompt = PromptBuilder().build_prompt(requirement_text)
            raw_json = analyze_requirement(prompt, provider=provider)
        except MissingAPIKeyError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except LLMClientError as e:
            raise HTTPException(status_code=502, detail=f"LLM error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
    
    try:
        data = json.loads(raw_json)
        return RequirementReadinessReport(**data)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Invalid JSON from LLM: {e}")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Schema validation failed: {e}")


def _render_jira_comment(report: RequirementReadinessReport) -> str:
    """Render report as a Jira-compatible comment (Atlassian wiki markup)."""
    lines: list[str] = []
    
    rec = report.recommendation.value if report.recommendation else "unknown"
    color_map = {"ready": "green", "needs_refinement": "orange", "high_risk": "red", "not_ready": "red"}
    color = color_map.get(rec, "grey")
    
    lines.append(f"{{panel:title=AI Requirement Readiness Analysis|borderColor=#{color}}}")
    lines.append(f"*Readiness Score:* {report.readiness_score}/100")
    lines.append(f"*Recommendation:* {{color:{color}}}{rec.replace('_', ' ').title()}{{color}}")
    lines.append("")
    lines.append(f"*Summary:* {report.summary}")
    lines.append("{panel}")
    lines.append("")
    
    if report.clarification_questions:
        lines.append("h4. Clarification Questions")
        for q in report.clarification_questions:
            lines.append(f"* {q}")
        lines.append("")
    
    if report.missing_information:
        lines.append("h4. Missing Information")
        for item in report.missing_information:
            lines.append(f"* {item}")
        lines.append("")
    
    all_risks = report.product_risks + report.qa_risks + report.technical_risks
    if all_risks:
        lines.append("h4. Identified Risks")
        for risk in all_risks[:5]:
            lines.append(f"* {risk}")
        if len(all_risks) > 5:
            lines.append(f"_...and {len(all_risks) - 5} more risks_")
        lines.append("")
    
    lines.append("----")
    lines.append("_Generated by AI Requirement Readiness Analyzer_")
    
    return "\n".join(lines)


def _render_confluence_page(report: RequirementReadinessReport, issue_key: Optional[str] = None) -> tuple[str, str]:
    """Render report as Confluence page content (XHTML storage format)."""
    title_prefix = f"{issue_key}: " if issue_key else ""
    page_title = f"{title_prefix}Requirement Readiness Report"
    
    rec = report.recommendation.value if report.recommendation else "unknown"
    color_map = {"ready": "green", "needs_refinement": "orange", "high_risk": "red", "not_ready": "red"}
    color = color_map.get(rec, "grey")
    
    body_parts = []
    
    # Status panel
    body_parts.append(f"""<ac:structured-macro ac:name="panel">
<ac:parameter ac:name="borderColor">#{color}</ac:parameter>
<ac:parameter ac:name="title">Readiness Summary</ac:parameter>
<ac:rich-text-body>
<p><strong>Readiness Score:</strong> {report.readiness_score}/100</p>
<p><strong>Recommendation:</strong> <ac:structured-macro ac:name="status"><ac:parameter ac:name="colour">{color}</ac:parameter><ac:parameter ac:name="title">{rec.replace('_', ' ').title()}</ac:parameter></ac:structured-macro></p>
<p><strong>Summary:</strong> {report.summary}</p>
</ac:rich-text-body>
</ac:structured-macro>""")
    
    # Rewritten user story
    body_parts.append(f"""<h2>Rewritten User Story</h2>
<p>{report.rewritten_user_story}</p>""")
    
    # Missing information
    if report.missing_information:
        items = "".join(f"<li>{item}</li>" for item in report.missing_information)
        body_parts.append(f"<h2>Missing Information</h2><ul>{items}</ul>")
    
    # Acceptance criteria
    if report.acceptance_criteria:
        items = "".join(f"<li>{ac}</li>" for ac in report.acceptance_criteria)
        body_parts.append(f"<h2>Acceptance Criteria</h2><ul>{items}</ul>")
    
    # Edge cases
    if report.edge_cases:
        items = "".join(f"<li>{ec}</li>" for ec in report.edge_cases)
        body_parts.append(f"<h2>Edge Cases</h2><ul>{items}</ul>")
    
    # Risks
    all_risks = []
    if report.product_risks:
        all_risks.extend([("Product", r) for r in report.product_risks])
    if report.qa_risks:
        all_risks.extend([("QA", r) for r in report.qa_risks])
    if report.technical_risks:
        all_risks.extend([("Technical", r) for r in report.technical_risks])
    
    if all_risks:
        rows = "".join(f"<tr><td>{cat}</td><td>{risk}</td></tr>" for cat, risk in all_risks)
        body_parts.append(f"""<h2>Identified Risks</h2>
<table><thead><tr><th>Category</th><th>Risk</th></tr></thead><tbody>{rows}</tbody></table>""")
    
    # Test scenarios
    if report.suggested_test_scenarios:
        rows = "".join(
            f"<tr><td>{s.title}</td><td>{s.type.value}</td><td>{s.priority.value}</td><td>{s.description}</td></tr>"
            for s in report.suggested_test_scenarios
        )
        body_parts.append(f"""<h2>Suggested Test Scenarios</h2>
<table><thead><tr><th>Title</th><th>Type</th><th>Priority</th><th>Description</th></tr></thead><tbody>{rows}</tbody></table>""")
    
    # Clarification questions
    if report.clarification_questions:
        items = "".join(f"<li>{q}</li>" for q in report.clarification_questions)
        body_parts.append(f"<h2>Clarification Questions</h2><ul>{items}</ul>")
    
    # Footer
    body_parts.append("""<hr/>
<p><em>Generated by AI Requirement Readiness Analyzer</em></p>""")
    
    page_body = "\n".join(body_parts)
    return page_title, page_body


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return HealthResponse(status="healthy", version="1.0.0")


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze(
    request: AnalyzeRequest,
    demo_mode: bool = Query(
        default=False,
        description="Use demo mode (no LLM call, returns sample data)"
    ),
    provider: str = Query(
        default="openai",
        description="LLM provider to use"
    )
):
    """
    Analyze a product requirement and return a structured readiness report.
    
    Accepts Jira-like payload with optional fields: issue_type, priority, labels.
    
    The report includes:
    - Readiness score (0-100)
    - Recommendation (ready, needs_refinement, high_risk, not_ready)
    - Missing information
    - Acceptance criteria
    - Edge cases
    - Product/QA/Technical risks
    - Suggested test scenarios
    - Clarification questions
    """
    report = _analyze_requirement(request, demo_mode, provider)
    
    return AnalyzeResponse(
        issue_key=request.issue_key,
        readiness_score=report.readiness_score,
        recommendation=report.recommendation.value if report.recommendation else "unknown",
        report=report
    )


@app.post("/analyze/jira-comment", response_model=JiraCommentResponse, tags=["Analysis"])
async def analyze_jira_comment(
    request: AnalyzeRequest,
    demo_mode: bool = Query(
        default=False,
        description="Use demo mode (no LLM call, returns sample data)"
    ),
    provider: str = Query(
        default="openai",
        description="LLM provider to use"
    )
):
    """
    Analyze a requirement and return a Jira-compatible comment.
    
    Returns Atlassian wiki markup that can be posted directly as a Jira comment.
    Ideal for n8n/automation workflows that add comments to Jira issues.
    """
    report = _analyze_requirement(request, demo_mode, provider)
    comment = format_jira_comment(report, issue_key=request.issue_key)
    
    return JiraCommentResponse(
        issue_key=request.issue_key,
        jira_comment=comment
    )


@app.post("/analyze/confluence-page", response_model=ConfluencePageResponse, tags=["Analysis"])
async def analyze_confluence_page(
    request: AnalyzeRequest,
    demo_mode: bool = Query(
        default=False,
        description="Use demo mode (no LLM call, returns sample data)"
    ),
    provider: str = Query(
        default="openai",
        description="LLM provider to use"
    )
):
    """
    Analyze a requirement and return Confluence page content.
    
    Returns page_title and page_body in Confluence XHTML storage format.
    Use with Confluence REST API to create documentation pages.
    """
    report = _analyze_requirement(request, demo_mode, provider)
    page = format_confluence_page(report, issue_key=request.issue_key)
    
    return ConfluencePageResponse(
        issue_key=request.issue_key,
        page_title=page["page_title"],
        page_body=page["page_body"]
    )
