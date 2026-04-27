"""
FastAPI service for AI Requirement Readiness Analyzer.

Provides REST API endpoints for requirement analysis,
designed for integration with n8n, Jira automation, and other tools.
"""

import json
from typing import Any, List, Optional, Union

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from .llm_client import LLMClientError, MissingAPIKeyError, analyze_requirement
from .prompt_builder import PromptBuilder
from .schemas import RequirementReadinessReport
from .jira_formatter import format_jira_comment
from .confluence_formatter import format_confluence_page
from .duplicate_detector import find_duplicates
from .jira_adf import extract_text_from_adf


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
    description: Union[str, dict, None] = Field(
        default="",
        description="Full requirement description. Can be plain text or Jira ADF (Atlassian Document Format) JSON.",
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
    domain_context: Optional[str] = Field(
        default=None,
        description="Domain context for analysis (e.g., control_panel, embedded_device, media_streaming). Defaults to generic_web if not specified.",
        json_schema_extra={"example": "control_panel"}
    )

    @field_validator('description', mode='before')
    @classmethod
    def convert_adf_to_text(cls, v: Any) -> str:
        """Convert ADF description to plain text."""
        return extract_text_from_adf(v)


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


class CandidateIssue(BaseModel):
    """A candidate issue for duplicate comparison."""
    key: str = Field(..., description="Issue key (e.g., PROJ-123)")
    title: str = Field(..., description="Issue title/summary")
    description: str = Field(default="", description="Issue description")


class DuplicateMatch(BaseModel):
    """A matched duplicate or related issue."""
    issue_key: str
    title: str
    match_type: str = Field(..., description="Type: duplicate, near_duplicate, conflicting, related")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score 0-1")
    reason: str


class DuplicateCheckRequest(BaseModel):
    """Request body for /analyze/duplicates endpoint."""
    issue_key: Optional[str] = Field(
        default=None,
        description="Key of the new issue (excluded from comparison)"
    )
    title: str = Field(..., description="Title of the requirement to check")
    description: str = Field(default="", description="Description of the requirement")
    candidates: List[CandidateIssue] = Field(
        ...,
        description="List of candidate issues to compare against",
        min_length=1
    )
    threshold: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description="Minimum similarity threshold for matches"
    )


class DuplicateCheckResponse(BaseModel):
    """Response body for /analyze/duplicates endpoint."""
    duplicates_found: bool = Field(..., description="True if probable duplicates detected")
    probable_duplicates_count: int = Field(default=0)
    near_duplicates_count: int = Field(default=0)
    conflicts_count: int = Field(default=0)
    top_matches: List[DuplicateMatch] = Field(default_factory=list)
    recommendation: str


class AcceptanceCriterion(BaseModel):
    """A single acceptance criterion."""
    id: str = Field(..., description="AC identifier (e.g., AC-1)")
    given: str = Field(..., description="Given precondition")
    when: str = Field(..., description="When action")
    then: str = Field(..., description="Then expected outcome")


class TestScenario(BaseModel):
    """A test scenario for QA."""
    title: str = Field(..., description="Test scenario title")
    type: str = Field(..., description="Type: positive, negative, or boundary")


class AcceptanceCriteriaRequest(BaseModel):
    """Request body for /analyze/acceptance-criteria endpoint."""
    issue_key: Optional[str] = Field(default=None, description="Jira issue key")
    title: str = Field(..., description="Requirement title")
    description: Union[str, dict, None] = Field(
        default="",
        description="Requirement description (plain text or ADF)"
    )
    domain_context: Optional[str] = Field(
        default=None,
        description="Domain context (e.g., control_panel, embedded_device)"
    )

    @field_validator('description', mode='before')
    @classmethod
    def convert_adf_to_text(cls, v: Any) -> str:
        """Convert ADF description to plain text."""
        return extract_text_from_adf(v)


class AcceptanceCriteriaResponse(BaseModel):
    """Response body for /analyze/acceptance-criteria endpoint."""
    issue_key: Optional[str] = None
    acceptance_criteria: List[AcceptanceCriterion] = Field(
        ..., 
        description="List of acceptance criteria (max 5)",
        max_length=5
    )
    edge_cases: List[str] = Field(
        ...,
        description="Edge cases: failure modes, permissions, empty states, invalid input, concurrency",
        max_length=5
    )
    test_scenarios: List[TestScenario] = Field(
        ...,
        description="Practical QA test scenarios",
        max_length=5
    )
    automation_candidates: List[str] = Field(
        ...,
        description="Scenarios worth automating in CI/CD",
        max_length=5
    )


def _get_demo_response(title: str, description: str, domain_context: Optional[str] = None) -> str:
    """
    Generate a demo response based on input quality assessment and domain context.
    
    Returns stricter scores for insufficient/poor quality input.
    Context-aware responses for specific domains like control_panel.
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
        # Adequate input - context-aware demo response
        if domain_context == "control_panel":
            demo_data = {
                "original_requirement": requirement_text,
                "summary": "This requirement involves user management for a control panel. Critical security and access control details are missing.",
                "rewritten_user_story": "As a system administrator, I want to manage user roles and permissions so that operators have appropriate access to control panel functions.",
                "readiness_score": 32,
                "recommendation": "not_ready",
                "score_breakdown": {
                    "clarity": 35,
                    "acceptance_criteria_quality": 25,
                    "testability": 30,
                    "edge_case_coverage": 20,
                    "dependency_clarity": 40,
                    "risk_visibility": 35,
                    "observability_expectations": 30
                },
                "missing_information": [
                    "Complete RBAC permissions matrix for each role",
                    "Password policy requirements (complexity, rotation, history)",
                    "Session management rules (timeout, concurrent sessions)",
                    "Audit logging requirements for user actions",
                    "Security boundaries between admin and operator roles",
                    "Multi-factor authentication requirements"
                ],
                "acceptance_criteria": [
                    "[ASSUMPTION] Admin can create, modify, and delete operator accounts",
                    "[ASSUMPTION] Operators cannot modify their own permission level",
                    "[ASSUMPTION] All user management actions are logged with timestamp and actor",
                    "[NEEDS CLARIFICATION] Define exact permissions for each role"
                ],
                "edge_cases": [
                    "Admin attempts to delete their own account",
                    "Last admin account deletion prevention",
                    "Concurrent role modification conflicts",
                    "Session behavior when permissions are revoked",
                    "Password reset during active session"
                ],
                "product_risks": [
                    "Insufficient role granularity may require rework",
                    "Missing audit requirements could violate compliance",
                    "Unclear permission boundaries risk security gaps"
                ],
                "qa_risks": [
                    "Cannot test RBAC without complete permissions matrix",
                    "Security testing requires defined authentication policies",
                    "Audit log verification needs specified format and retention"
                ],
                "technical_risks": [
                    "Session management complexity with multiple concurrent users",
                    "Audit log storage and performance impact",
                    "Secure credential storage implementation"
                ],
                "suggested_test_scenarios": [
                    {"title": "Role-based access verification", "type": "functional", "priority": "high", "description": "Verify each role can only access permitted functions"},
                    {"title": "Privilege escalation prevention", "type": "negative", "priority": "high", "description": "Verify operators cannot gain admin privileges"},
                    {"title": "Audit log completeness", "type": "functional", "priority": "high", "description": "Verify all user actions are logged with required details"},
                    {"title": "Session timeout enforcement", "type": "non_functional", "priority": "medium", "description": "Verify sessions expire after configured timeout"},
                    {"title": "Concurrent session handling", "type": "functional", "priority": "medium", "description": "Verify behavior with multiple active sessions"}
                ],
                "automation_candidates": [
                    "RBAC permission matrix verification tests",
                    "Audit log format and completeness checks",
                    "Session management regression tests"
                ],
                "clarification_questions": [
                    "What specific permissions does each role (admin, operator) have?",
                    "What actions require audit logging?",
                    "What is the password policy (complexity, expiration, history)?",
                    "What are the session timeout and concurrent session limits?",
                    "Is multi-factor authentication required for any role?",
                    "What approval workflow exists for creating new admin accounts?"
                ],
                "human_review_notes": [
                    "Control panel user management requires detailed security specifications",
                    "RBAC matrix must be defined before development",
                    "Consider compliance requirements (SOC2, ISO27001) for audit logging"
                ]
            }
        elif domain_context == "embedded_device":
            demo_data = {
                "original_requirement": requirement_text,
                "summary": "This requirement targets an embedded system. Resource constraints and hardware considerations need clarification.",
                "rewritten_user_story": "As a device operator, I want to configure the system so that it operates within defined hardware constraints.",
                "readiness_score": 30,
                "recommendation": "not_ready",
                "score_breakdown": {
                    "clarity": 35,
                    "acceptance_criteria_quality": 25,
                    "testability": 25,
                    "edge_case_coverage": 20,
                    "dependency_clarity": 35,
                    "risk_visibility": 30,
                    "observability_expectations": 25
                },
                "missing_information": [
                    "Target hardware specifications (CPU, memory, storage)",
                    "Real-time requirements and timing constraints",
                    "Power consumption budget",
                    "Communication protocols and interfaces",
                    "Firmware update mechanism requirements",
                    "Recovery procedures for failure scenarios"
                ],
                "acceptance_criteria": [
                    "[ASSUMPTION] Operation within specified memory limits",
                    "[ASSUMPTION] Graceful degradation on resource exhaustion",
                    "[NEEDS CLARIFICATION] Define hardware platform specifications"
                ],
                "edge_cases": [
                    "Memory exhaustion during operation",
                    "Power loss during critical operation",
                    "Communication timeout with external systems",
                    "Firmware corruption detection and recovery",
                    "Watchdog timer expiration scenarios"
                ],
                "product_risks": [
                    "Unknown hardware constraints may force redesign",
                    "Real-time requirements not specified",
                    "Power budget undefined"
                ],
                "qa_risks": [
                    "Testing requires target hardware availability",
                    "Real-time behavior difficult to simulate",
                    "Edge cases may require specialized test equipment"
                ],
                "technical_risks": [
                    "Memory footprint may exceed available resources",
                    "Timing constraints may not be achievable",
                    "Hardware abstraction layer complexity"
                ],
                "suggested_test_scenarios": [
                    {"title": "Memory usage verification", "type": "non_functional", "priority": "high", "description": "Verify operation within memory constraints"},
                    {"title": "Power loss recovery", "type": "negative", "priority": "high", "description": "Verify system recovers correctly after power loss"},
                    {"title": "Watchdog behavior", "type": "functional", "priority": "high", "description": "Verify watchdog timer triggers recovery correctly"}
                ],
                "automation_candidates": [
                    "Memory usage monitoring tests",
                    "Communication protocol conformance tests"
                ],
                "clarification_questions": [
                    "What is the target hardware platform?",
                    "What are the memory and storage constraints?",
                    "What are the real-time timing requirements?",
                    "What communication interfaces are available?",
                    "What is the power budget?"
                ],
                "human_review_notes": [
                    "Embedded requirements need hardware specifications before analysis",
                    "Consider resource constraints in all design decisions"
                ]
            }
        else:
            # Default generic_web response
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
        raw_json = _get_demo_response(request.title, request.description, request.domain_context)
    else:
        try:
            prompt = PromptBuilder().build_prompt(requirement_text, domain_context=request.domain_context)
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


@app.post("/analyze/duplicates", response_model=DuplicateCheckResponse, tags=["Analysis"])
async def check_duplicates(request: DuplicateCheckRequest):
    """
    Check for duplicate or related requirements in the backlog.
    
    Compares a new requirement against candidate backlog issues using
    semantic intent matching (not just keyword matching).
    
    Detects:
    - **Duplicates**: Same intent, different wording (confidence >= 0.8)
    - **Near-duplicates**: Overlapping scope (confidence >= 0.6)
    - **Conflicting**: Contradictory goals
    - **Related**: Similar topics (confidence >= threshold)
    
    Flag confidence > 0.8 as probable duplicate requiring review.
    """
    candidates_dict = [
        {
            "key": c.key,
            "title": c.title,
            "description": c.description
        }
        for c in request.candidates
    ]
    
    result = find_duplicates(
        new_issue_key=request.issue_key,
        new_title=request.title,
        new_description=request.description,
        candidates=candidates_dict,
        threshold=request.threshold
    )
    
    return DuplicateCheckResponse(
        duplicates_found=result["duplicates_found"],
        probable_duplicates_count=result["probable_duplicates_count"],
        near_duplicates_count=result["near_duplicates_count"],
        conflicts_count=result["conflicts_count"],
        top_matches=[
            DuplicateMatch(**match) for match in result["top_matches"]
        ],
        recommendation=result["recommendation"]
    )


def _generate_acceptance_criteria(
    title: str,
    description: str,
    domain_context: Optional[str] = None
) -> dict:
    """
    Generate acceptance criteria, edge cases, test scenarios, and automation candidates.
    
    Uses domain context to tailor suggestions.
    """
    from .context_loader import load_context
    
    # Load domain context (available for future LLM integration)
    context = load_context(domain_context) if domain_context else None
    
    # Extract key concepts from requirement
    text = f"{title} {description}".lower()
    
    # Initialize outputs
    acceptance_criteria = []
    edge_cases = []
    test_scenarios = []
    automation_candidates = []
    
    # Domain-specific generation
    if domain_context == "control_panel":
        acceptance_criteria = [
            {
                "id": "AC-1",
                "given": "The user is authenticated and has appropriate permissions",
                "when": "The user performs the main action described",
                "then": "The system completes the operation and provides confirmation"
            },
            {
                "id": "AC-2",
                "given": "The system is in a valid state",
                "when": "The user submits the required data",
                "then": "The data is validated and persisted correctly"
            },
            {
                "id": "AC-3",
                "given": "The operation requires confirmation",
                "when": "The user confirms the action",
                "then": "The system executes the operation with proper audit logging"
            }
        ]
        edge_cases = [
            "Session expires during multi-step operation",
            "Concurrent modification by another admin user",
            "Maximum allowed entries reached for resource",
            "User lacks partial permissions for nested operation",
            "Empty state when no data exists yet"
        ]
        test_scenarios = [
            {"title": "Verify operation completes with valid permissions", "type": "positive"},
            {"title": "Verify access denied for insufficient permissions", "type": "negative"},
            {"title": "Verify behavior at maximum resource limit", "type": "boundary"},
            {"title": "Verify concurrent edit conflict detection", "type": "negative"},
            {"title": "Verify audit log entry created on action", "type": "positive"}
        ]
        automation_candidates = [
            "Permission verification for all role types",
            "Input validation with boundary values",
            "Audit log generation verification",
            "Session timeout handling",
            "API response schema validation"
        ]
    elif domain_context == "embedded_device":
        acceptance_criteria = [
            {
                "id": "AC-1",
                "given": "The device is powered on and initialized",
                "when": "The trigger condition is met",
                "then": "The system responds within specified latency requirements"
            },
            {
                "id": "AC-2",
                "given": "The device has stable power supply",
                "when": "The operation is executed",
                "then": "Memory and CPU usage remain within defined limits"
            },
            {
                "id": "AC-3",
                "given": "Communication channel is established",
                "when": "Data is transmitted",
                "then": "Data integrity is verified with checksum validation"
            }
        ]
        edge_cases = [
            "Power fluctuation during write operation",
            "Memory approaching allocation limit",
            "Sensor reading at min/max boundary values",
            "Communication timeout during data transfer",
            "Invalid or corrupted incoming data packet"
        ]
        test_scenarios = [
            {"title": "Verify response time under normal conditions", "type": "positive"},
            {"title": "Verify graceful degradation on low memory", "type": "boundary"},
            {"title": "Verify recovery after communication timeout", "type": "negative"},
            {"title": "Verify data integrity with checksum validation", "type": "positive"},
            {"title": "Verify behavior at sensor boundary values", "type": "boundary"}
        ]
        automation_candidates = [
            "Response latency measurement under load",
            "Memory usage profiling during operations",
            "Communication protocol compliance tests",
            "Data integrity verification with checksums",
            "Boundary value testing for sensor inputs"
        ]
    elif domain_context == "media_streaming":
        acceptance_criteria = [
            {
                "id": "AC-1",
                "given": "User has valid subscription and network connection",
                "when": "User initiates playback",
                "then": "Content starts within 2 seconds with adaptive quality"
            },
            {
                "id": "AC-2",
                "given": "Content is DRM protected",
                "when": "Playback is requested",
                "then": "License is validated before content delivery"
            },
            {
                "id": "AC-3",
                "given": "User is watching content",
                "when": "Network quality degrades",
                "then": "System adapts bitrate without interruption"
            }
        ]
        edge_cases = [
            "Network bandwidth drops below minimum threshold",
            "User switches devices mid-stream",
            "Content license expires during playback",
            "Maximum concurrent streams already active",
            "Geographic restriction applies to content"
        ]
        test_scenarios = [
            {"title": "Verify playback starts within latency SLA", "type": "positive"},
            {"title": "Verify adaptive bitrate on bandwidth change", "type": "boundary"},
            {"title": "Verify DRM license validation blocks expired content", "type": "negative"},
            {"title": "Verify concurrent stream limit enforcement", "type": "negative"},
            {"title": "Verify seamless device handoff", "type": "positive"}
        ]
        automation_candidates = [
            "Playback start time measurement",
            "Adaptive bitrate switching verification",
            "DRM license validation flow",
            "Concurrent stream limit enforcement",
            "Content availability by region"
        ]
    else:
        # Generic web application
        acceptance_criteria = [
            {
                "id": "AC-1",
                "given": "The user is on the relevant page",
                "when": "The user performs the described action",
                "then": "The system responds with expected outcome"
            },
            {
                "id": "AC-2",
                "given": "Required preconditions are met",
                "when": "The user submits the form/request",
                "then": "Data is validated and processed correctly"
            },
            {
                "id": "AC-3",
                "given": "The operation completes successfully",
                "when": "The result is displayed",
                "then": "User receives appropriate confirmation feedback"
            }
        ]
        edge_cases = [
            "User submits empty or whitespace-only input",
            "Double-click on submit button",
            "Page refresh during async operation",
            "User not authenticated when accessing protected resource",
            "Server returns 5xx error during operation"
        ]
        test_scenarios = [
            {"title": "Verify successful operation with valid input", "type": "positive"},
            {"title": "Verify validation error on invalid input", "type": "negative"},
            {"title": "Verify behavior at input length boundaries", "type": "boundary"},
            {"title": "Verify authentication redirect for protected routes", "type": "negative"},
            {"title": "Verify error handling on server failure", "type": "negative"}
        ]
        automation_candidates = [
            "Form validation with valid and invalid inputs",
            "Authentication flow verification",
            "API response status code validation",
            "Input boundary value testing",
            "Error message display verification"
        ]
    
    # Add context-specific items based on keywords
    if "login" in text or "authentication" in text or "password" in text:
        acceptance_criteria.append({
            "id": f"AC-{len(acceptance_criteria) + 1}",
            "given": "User enters valid credentials",
            "when": "User submits login form",
            "then": "User is authenticated and redirected to dashboard"
        })
        edge_cases.append("User enters incorrect password multiple times")
        test_scenarios.append({"title": "Verify account lockout after failed attempts", "type": "negative"})
        automation_candidates.append("Login flow with valid/invalid credentials")
    
    if "search" in text or "filter" in text:
        edge_cases.append("Search query returns zero results")
        test_scenarios.append({"title": "Verify empty state display for no results", "type": "boundary"})
        automation_candidates.append("Search result pagination and filtering")
    
    if "upload" in text or "file" in text or "import" in text:
        edge_cases.append("File exceeds maximum allowed size")
        edge_cases.append("Unsupported file format submitted")
        test_scenarios.append({"title": "Verify file size limit enforcement", "type": "boundary"})
        automation_candidates.append("File upload with various formats and sizes")
    
    # Limit to max 5 each
    return {
        "acceptance_criteria": acceptance_criteria[:5],
        "edge_cases": edge_cases[:5],
        "test_scenarios": test_scenarios[:5],
        "automation_candidates": automation_candidates[:5]
    }


@app.post("/analyze/acceptance-criteria", response_model=AcceptanceCriteriaResponse, tags=["Analysis"])
async def generate_acceptance_criteria(request: AcceptanceCriteriaRequest):
    """
    Generate acceptance criteria, edge cases, test scenarios, and automation candidates.
    
    Uses domain context to provide relevant suggestions:
    - **control_panel**: Permission checks, audit logging, concurrent access
    - **embedded_device**: Resource constraints, power management, communication
    - **media_streaming**: DRM, buffering, adaptive bitrate
    - **generic_web** (default): Standard web app patterns
    
    Returns structured JSON with:
    - Up to 5 acceptance criteria (Given/When/Then format)
    - Up to 5 edge cases (failure modes, permissions, empty states, invalid input, concurrency)
    - Up to 5 test scenarios (positive, negative, boundary)
    - Up to 5 automation candidates (CI/CD worthy scenarios)
    """
    result = _generate_acceptance_criteria(
        title=request.title,
        description=request.description,
        domain_context=request.domain_context
    )
    
    return AcceptanceCriteriaResponse(
        issue_key=request.issue_key,
        acceptance_criteria=[
            AcceptanceCriterion(**ac) for ac in result["acceptance_criteria"]
        ],
        edge_cases=result["edge_cases"],
        test_scenarios=[
            TestScenario(**ts) for ts in result["test_scenarios"]
        ],
        automation_candidates=result["automation_candidates"]
    )
