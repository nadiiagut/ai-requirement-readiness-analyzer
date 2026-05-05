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
from .context_loader import classify_domain_context


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
    risk_level: str = Field(..., description="Risk level: Low, Medium, High, Critical")
    qa_complexity: str = Field(..., description="QA complexity: Low, Medium, High")
    clarification_count: int = Field(..., description="Number of clarification questions")
    automation_candidate: bool = Field(..., description="True if requirement is suitable for automation")
    selected_domain_context: str = Field(..., description="Domain context used for analysis (auto-classified or explicit)")
    report: RequirementReadinessReport


class HealthResponse(BaseModel):
    """Response body for /health endpoint."""
    status: str
    version: str


class JiraCommentResponse(BaseModel):
    """Response body for /analyze/jira-comment endpoint."""
    issue_key: Optional[str] = None
    jira_comment: str


class JiraCommentFormatRequest(BaseModel):
    """Request body for /format/jira-comment endpoint. Accepts combined analysis + AC data."""
    issue_key: Optional[str] = Field(default=None, description="Jira issue key")
    readiness_score: int = Field(..., ge=0, le=100, description="Readiness score 0-100")
    recommendation: str = Field(..., description="Recommendation: ready, needs_review, needs_refinement, not_ready")
    summary: Optional[str] = Field(default=None, description="Requirement summary")
    main_concerns: Optional[List[str]] = Field(default=None, description="Main concerns/risks")
    clarification_questions: Optional[List[str]] = Field(default=None, description="Clarification questions")
    acceptance_criteria: Optional[List[dict]] = Field(
        default=None,
        description="Acceptance criteria with id, given, when, then fields"
    )
    edge_cases: Optional[List[str]] = Field(default=None, description="Edge cases")
    test_scenarios: Optional[List[dict]] = Field(default=None, description="Test scenarios")
    automation_candidates: Optional[List[str]] = Field(default=None, description="Automation candidates")


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
    labels: Optional[List[str]] = Field(
        default=None,
        description="Jira labels (used for domain auto-classification)"
    )
    domain_context: Optional[str] = Field(
        default=None,
        description="Domain context (e.g., control_panel, embedded_device). If not provided, auto-classified from title/description/labels."
    )

    @field_validator('description', mode='before')
    @classmethod
    def convert_adf_to_text(cls, v: Any) -> str:
        """Convert ADF description to plain text."""
        return extract_text_from_adf(v)


class AcceptanceCriteriaResponse(BaseModel):
    """Response body for /analyze/acceptance-criteria endpoint."""
    issue_key: Optional[str] = None
    selected_domain_context: str = Field(..., description="Domain context used for analysis (auto-classified or explicit)")
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


class SprintIssue(BaseModel):
    """A single issue in a sprint for analysis."""
    issue_key: str = Field(..., description="Jira issue key (e.g., NG-1)")
    title: str = Field(..., description="Issue title/summary")
    description: Union[str, dict, None] = Field(
        default="",
        description="Issue description (plain text or ADF)"
    )
    status: Optional[str] = Field(default=None, description="Issue status (e.g., To Do, In Progress)")
    priority: Optional[str] = Field(default=None, description="Issue priority (e.g., High, Medium, Low)")
    labels: List[str] = Field(default_factory=list, description="Issue labels")
    assignee: Optional[str] = Field(default=None, description="Assignee name")
    issue_url: Optional[str] = Field(default=None, description="URL to the issue (for linking)")

    @field_validator('description', mode='before')
    @classmethod
    def convert_adf_to_text(cls, v: Any) -> str:
        """Convert ADF description to plain text."""
        return extract_text_from_adf(v)


class SprintAnalysisRequest(BaseModel):
    """Request body for /analyze/sprint endpoint."""
    sprint_name: str = Field(..., description="Sprint name")
    sprint_id: Optional[int] = Field(default=None, description="Sprint ID")
    domain_context: Optional[str] = Field(
        default=None,
        description="Domain context (e.g., control_panel, embedded_device)"
    )
    issues: List[SprintIssue] = Field(
        ...,
        description="List of issues in the sprint",
        min_length=1
    )


class SprintScopeEntry(BaseModel):
    """An issue entry for the Sprint Scope table."""
    issue_key: str = Field(..., description="Issue key")
    title: str = Field(..., description="Issue title")
    assignee: Optional[str] = Field(default=None, description="Assignee name")
    status: Optional[str] = Field(default=None, description="Issue status")
    risk: str = Field(..., description="Risk level: Low, Medium, High")
    reason: str = Field(..., description="Short stakeholder-friendly risk explanation")
    notes: str = Field(..., description="Acceptance criteria / notes")
    issue_url: Optional[str] = Field(default=None, description="URL to the issue")


class RiskyEntry(BaseModel):
    """A risky issue entry in the sprint (deprecated, use SprintScopeEntry)."""
    issue_key: str = Field(..., description="Issue key")
    title: str = Field(..., description="Issue title")
    reason: str = Field(..., description="Why this is risky")
    risk: str = Field(..., description="Risk level: Low, Medium, High")


class DecisionEntry(BaseModel):
    """An item requiring a stakeholder or PM decision."""
    issue_key: str = Field(..., description="Issue key")
    issue_url: str = Field(..., description="Full URL to the issue")
    title: str = Field(..., description="Issue title")
    decision_needed: str = Field(..., description="Short decision description")
    why_it_matters: str = Field(..., description="Stakeholder-friendly explanation")


class SprintAnalysisResponse(BaseModel):
    """Response body for /analyze/sprint endpoint."""
    sprint_name: str = Field(..., description="Sprint name")
    sprint_id: Optional[int] = Field(default=None, description="Sprint ID used in Jira macro for live board")
    context_distribution: dict[str, int] = Field(
        ..., 
        description="Distribution of domain contexts across sprint issues (context_name -> issue_count)"
    )
    sprint_health_score: int = Field(..., ge=0, le=100, description="Overall sprint health 0-100")
    delivery_confidence: str = Field(..., description="Delivery confidence: Low, Medium, High")
    total_issues: int = Field(..., description="Total number of issues in sprint")
    high_risk_count: int = Field(default=0, description="Number of high risk items")
    clarification_count: int = Field(default=0, description="Total items needing clarification")
    ready_count: int = Field(..., description="Issues ready for development")
    needs_review_count: int = Field(..., description="Issues needing review")
    needs_refinement_count: int = Field(..., description="Issues needing refinement")
    not_ready_count: int = Field(default=0, description="Issues not ready")
    sprint_scope: List[SprintScopeEntry] = Field(default_factory=list, description="All issues in sprint with analysis")
    risky_entries: List[RiskyEntry] = Field(default_factory=list, description="Issues with elevated risk (deprecated)")
    top_risks: List[str] = Field(default_factory=list, description="Top sprint-level risks")
    qa_focus_areas: List[str] = Field(default_factory=list, description="Areas QA should focus on")
    blocked_candidates: List[str] = Field(default_factory=list, description="Issues that may block others")
    recommended_actions: List[str] = Field(default_factory=list, description="Recommended actions for sprint success")
    decisions_needed: List[DecisionEntry] = Field(default_factory=list, description="Items requiring stakeholder or PM decisions")
    executive_summary: str = Field(..., description="Executive summary of sprint readiness")
    confluence_page_title: str = Field(..., description="Confluence page title for sprint dashboard")
    confluence_page_body_storage: str = Field(..., description="Confluence storage-format HTML body")


class ConfluenceSprintPageRequest(BaseModel):
    """Request body for /format/confluence-sprint-page endpoint."""
    sprint_analysis: SprintAnalysisResponse = Field(
        ...,
        description="Sprint analysis output from /analyze/sprint"
    )


class ConfluenceSprintPageResponse(BaseModel):
    """Response body for /format/confluence-sprint-page endpoint."""
    page_title: str = Field(..., description="Confluence page title")
    page_body_storage: str = Field(..., description="Confluence storage-format HTML body")


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


def _compute_risk_level(report: RequirementReadinessReport) -> str:
    """
    Compute risk level based on identified risks (separate from readiness score).
    
    Risk is assessed by counting and weighing product, QA, and technical risks.
    """
    product_risks = len(report.product_risks)
    qa_risks = len(report.qa_risks)
    technical_risks = len(report.technical_risks)
    
    # Weight technical risks higher as they often have broader impact
    weighted_risk_count = product_risks + qa_risks + (technical_risks * 1.5)
    
    # Also factor in missing information as it increases uncertainty
    missing_info_count = len(report.missing_information)
    weighted_risk_count += missing_info_count * 0.5
    
    if weighted_risk_count >= 8:
        return "Critical"
    elif weighted_risk_count >= 5:
        return "High"
    elif weighted_risk_count >= 2:
        return "Medium"
    return "Low"


def _compute_qa_complexity(report: RequirementReadinessReport) -> str:
    """
    Compute QA complexity based on flows, roles, edge cases, and dependencies.
    
    Higher complexity means more test effort required.
    """
    complexity_score = 0
    
    # Edge cases add complexity
    edge_case_count = len(report.edge_cases)
    complexity_score += edge_case_count * 2
    
    # Test scenarios indicate flow complexity
    scenario_count = len(report.suggested_test_scenarios)
    complexity_score += scenario_count * 1.5
    
    # Acceptance criteria indicate required verifications
    ac_count = len(report.acceptance_criteria)
    complexity_score += ac_count
    
    # Missing information adds uncertainty complexity
    missing_count = len(report.missing_information)
    complexity_score += missing_count
    
    # Clarification questions suggest unclear requirements
    question_count = len(report.clarification_questions)
    complexity_score += question_count * 0.5
    
    if complexity_score >= 15:
        return "High"
    elif complexity_score >= 8:
        return "Medium"
    return "Low"


def _compute_automation_candidate(report: RequirementReadinessReport) -> bool:
    """
    Determine if requirement is suitable for test automation.
    
    True if scenarios are repetitive, testable, and have clear expected outcomes.
    """
    # Check if there are automation candidates explicitly identified
    if report.automation_candidates and len(report.automation_candidates) > 0:
        return True
    
    # Check testability score from breakdown
    testability = report.score_breakdown.testability if report.score_breakdown else 0
    
    # High testability suggests automation potential
    if testability >= 70:
        # Also need clear acceptance criteria for automation
        if len(report.acceptance_criteria) >= 2:
            return True
    
    # Check if test scenarios exist and are well-defined
    if len(report.suggested_test_scenarios) >= 3:
        # Multiple scenarios suggest repeatable test patterns
        return True
    
    return False


def _classify_issue_by_labels(labels: List[str]) -> Optional[str]:
    """
    Classify issue readiness based on labels.
    
    Returns: 'ready', 'needs_review', 'needs_refinement', or None if no relevant label.
    """
    labels_lower = [l.lower().replace("_", "-").replace(" ", "-") for l in labels]
    
    if any(l in ["ready-for-sprint", "ready", "sprint-ready", "dev-ready"] for l in labels_lower):
        return "ready"
    if any(l in ["needs-review", "review", "needs-qa-review"] for l in labels_lower):
        return "needs_review"
    if any(l in ["needs-refinement", "refinement", "needs-grooming", "backlog"] for l in labels_lower):
        return "needs_refinement"
    return None


def _analyze_sprint_issue(
    issue: "SprintIssue",
    domain_context: Optional[str],
    demo_mode: bool,
    provider: str
) -> dict:
    """
    Analyze a single sprint issue and return classification data.
    
    Returns dict with: readiness, risk_level, risks, qa_areas, is_risky, reason
    """
    # First check labels for explicit classification
    label_readiness = _classify_issue_by_labels(issue.labels)
    
    # Analyze the requirement
    request = AnalyzeRequest(
        issue_key=issue.issue_key,
        title=issue.title,
        description=issue.description,
        domain_context=domain_context,
    )
    
    try:
        report = _analyze_requirement(request, demo_mode, provider)
        
        # Determine readiness (labels take precedence if present)
        if label_readiness:
            readiness = label_readiness
        else:
            readiness = report.recommendation.value if report.recommendation else "needs_refinement"
        
        # Compute risk level
        risk_level = _compute_risk_level(report)
        
        # Collect risks
        all_risks = report.product_risks + report.qa_risks + report.technical_risks
        
        # Collect QA focus areas
        qa_areas = []
        if report.edge_cases:
            qa_areas.extend(report.edge_cases[:2])
        if report.qa_risks:
            qa_areas.extend(report.qa_risks[:2])
        
        # Determine if this is a risky entry
        is_risky = False
        reason = ""
        
        # needs-refinement in active sprint is risky
        if readiness == "needs_refinement":
            is_risky = True
            reason = "Needs refinement but already in sprint"
        elif readiness == "not_ready":
            is_risky = True
            reason = "Not ready for development"
        elif risk_level in ["High", "Critical"]:
            is_risky = True
            reason = f"{risk_level} risk: {all_risks[0] if all_risks else 'Multiple concerns identified'}"
        elif report.readiness_score < 50:
            is_risky = True
            reason = f"Low readiness score ({report.readiness_score}/100)"
        
        # Check for blocking indicators
        is_blocker = False
        blocker_keywords = ["blocks", "blocking", "prerequisite", "depends on", "dependency"]
        desc_lower = (issue.description or "").lower()
        title_lower = issue.title.lower()
        if any(kw in desc_lower or kw in title_lower for kw in blocker_keywords):
            is_blocker = True
        
        return {
            "readiness": readiness,
            "readiness_score": report.readiness_score,
            "risk_level": risk_level,
            "risks": all_risks[:3],
            "qa_areas": qa_areas[:3],
            "is_risky": is_risky,
            "reason": reason,
            "is_blocker": is_blocker,
            "clarification_count": len(report.clarification_questions),
        }
    except Exception:
        # If analysis fails, mark as needing refinement
        return {
            "readiness": label_readiness or "needs_refinement",
            "readiness_score": 0,
            "risk_level": "Medium",
            "risks": ["Unable to analyze requirement"],
            "qa_areas": [],
            "is_risky": True,
            "reason": "Analysis failed - requires manual review",
            "is_blocker": False,
            "clarification_count": 0,
        }


def _compute_sprint_health_from_labels(issue_labels_list: list[list[str]]) -> int:
    """
    Compute sprint health score (1-100) based on issue labels.
    
    Label weights:
    - ready-for-sprint / ready / sprint-ready / dev-ready: 90
    - needs-review: 70
    - needs-refinement / backlog: 45
    - no relevant label: 65
    
    Returns average score clamped to 1-100.
    If no issues, returns 0.
    """
    if not issue_labels_list:
        return 0
    
    scores = []
    for labels in issue_labels_list:
        labels_lower = [l.lower() for l in labels]
        
        # Check for ready labels
        if any(l in labels_lower for l in ["ready-for-sprint", "ready", "sprint-ready", "dev-ready"]):
            scores.append(90)
        # Check for needs-review
        elif any(l in labels_lower for l in ["needs-review", "review"]):
            scores.append(70)
        # Check for needs-refinement
        elif any(l in labels_lower for l in ["needs-refinement", "backlog", "refinement"]):
            scores.append(45)
        # No relevant label
        else:
            scores.append(65)
    
    avg_score = sum(scores) / len(scores)
    return max(1, min(100, int(avg_score)))


def _compute_delivery_confidence(sprint_health: int, risky_ratio: float) -> str:
    """Compute delivery confidence based on sprint health and risky ratio."""
    if sprint_health >= 75 and risky_ratio < 0.2:
        return "High"
    elif sprint_health >= 50 and risky_ratio < 0.4:
        return "Medium"
    return "Low"


def _generate_stakeholder_reason(readiness: str, risk_level: str, risks: list, clarification_count: int) -> str:
    """Generate a short stakeholder-friendly reason for the risk assessment."""
    if readiness == "needs_refinement":
        return "Missing acceptance criteria"
    elif readiness == "not_ready":
        return "Not ready for development"
    elif risk_level == "High":
        if risks:
            first_risk = risks[0].lower()
            if "permission" in first_risk or "role" in first_risk or "auth" in first_risk:
                return "Role permissions not defined"
            elif "acceptance" in first_risk or "criteria" in first_risk:
                return "Missing acceptance criteria"
            elif "behavior" in first_risk or "success" in first_risk or "failure" in first_risk:
                return "No clear success/failure behavior"
        return "High risk identified"
    elif clarification_count > 0:
        return "Clarification questions pending"
    return "No QA risk detected"


def _generate_scope_notes(readiness: str, risk_level: str, clarification_count: int) -> str:
    """Generate short acceptance criteria / notes for the Sprint Scope table."""
    if readiness == "needs_refinement":
        return "AC missing — requires refinement"
    elif readiness == "not_ready":
        return "Not ready — move to backlog or refine"
    elif risk_level == "High":
        return "Verify role permissions and audit behavior"
    elif clarification_count > 0:
        return f"Address {clarification_count} clarification question(s)"
    elif readiness == "needs_review":
        return "Ready for review before development"
    return "Ready for QA test planning"


_THEME_KEYWORDS: list[tuple[str, list[str]]] = [
    ("access control", ["access", "permission", "role", "rbac", "acl"]),
    ("user management", ["user", "account", "profile", "register", "onboard"]),
    ("authentication", ["auth", "login", "sso", "2fa", "password", "session"]),
    ("dashboard and reporting", ["dashboard", "report", "analytics", "metric", "chart"]),
    ("billing and payments", ["billing", "payment", "invoice", "subscription", "charge"]),
    ("notifications", ["notification", "email", "alert", "webhook", "alert"]),
    ("API and integrations", ["api", "integration", "webhook", "sync", "import", "export"]),
    ("configuration and admin", ["config", "setting", "setup", "admin", "control panel", "operational"]),
]

_OUTCOME_MAP: dict[str, str] = {
    "access control": "strengthen user access management",
    "user management": "improve user lifecycle and onboarding",
    "authentication": "improve login security and session reliability",
    "dashboard and reporting": "increase stakeholder visibility and data-driven decisions",
    "billing and payments": "improve payment reliability and financial workflows",
    "notifications": "improve alerting and communication reliability",
    "API and integrations": "expand platform connectivity and integration coverage",
    "configuration and admin": "increase operational control and flexibility",
}


def _infer_sprint_themes(issue_titles: list) -> list:
    """Infer up to 3 product/feature themes from issue titles."""
    text = " ".join(issue_titles).lower()
    found = []
    for theme, keywords in _THEME_KEYWORDS:
        if any(kw in text for kw in keywords):
            found.append(theme)
        if len(found) == 3:
            break
    return found


def _generate_executive_summary(
    sprint_name: str,
    delivery_confidence: str,
    total_issues: int,
    issues: Optional[list] = None,
) -> str:
    """
    Generate a stakeholder-facing executive summary focused on delivery.

    Summarises what is being delivered, impacted systems, and business outcome.
    Risk is intentionally excluded — it belongs in Delivery Risk Review.
    """
    if total_issues == 0:
        return f"{sprint_name} has no issues to analyze."

    issues = issues or []

    # Build combined texts (title + description) for richer theme detection
    titles: list[str] = []
    combined_texts: list[str] = []
    for issue in issues:
        if hasattr(issue, 'title'):
            title = issue.title
            desc = str(issue.description or "")
        else:
            title = issue.get('title', '')
            desc = str(issue.get('description', '') or "")
        titles.append(title)
        combined_texts.append(f"{title} {desc}")

    # Infer themes from full issue text (titles + descriptions)
    themes = _infer_sprint_themes(combined_texts)

    # Delivery statement
    if len(titles) == 1:
        delivery = f"This sprint delivers: {titles[0]}."
    elif len(titles) <= 3:
        delivery = "This sprint delivers: " + "; ".join(titles) + "."
    elif themes:
        delivery = f"This sprint delivers {total_issues} items focused on " + " and ".join(themes) + "."
    else:
        delivery = f"This sprint delivers {total_issues} items."

    # Business outcome derived from detected themes
    outcomes = [_OUTCOME_MAP[t] for t in themes if t in _OUTCOME_MAP]
    outcome = ("Intended outcome: " + " and ".join(outcomes[:2]) + ".") if outcomes else ""

    # Delivery confidence (readiness signal — not a risk statement)
    confidence = f"Delivery confidence: {delivery_confidence.lower()}."

    return " ".join(p for p in [delivery, outcome, confidence] if p)


_JIRA_BASE_URL = "https://nadingut.atlassian.net/browse"


def _build_decisions_needed(sprint_scope: list, issues: list) -> list:
    """
    Build DecisionEntry objects for issues requiring stakeholder decisions.

    Triggers: risk == High, needs-refinement notes, unclear/missing requirements,
              status Blocked, or reason mentions missing/undefined.
    """
    decisions = []
    for entry in sprint_scope:
        if hasattr(entry, 'issue_key'):
            issue_key = entry.issue_key
            title = entry.title
            risk = entry.risk
            reason = entry.reason
            notes = entry.notes
            status = (entry.status or "").strip()
            issue_url = entry.issue_url
        else:
            issue_key = entry.get('issue_key', '')
            title = entry.get('title', '')
            risk = entry.get('risk', 'Low')
            reason = entry.get('reason', '')
            notes = entry.get('notes', '')
            status = (entry.get('status') or '').strip()
            issue_url = entry.get('issue_url')

        reason_lower = reason.lower()
        notes_lower = notes.lower()
        is_decision = (
            risk == "High"
            or "missing acceptance criteria" in reason_lower
            or "not defined" in reason_lower
            or "ac missing" in notes_lower
            or "requires refinement" in notes_lower
            or status.lower() in ("blocked", "flagged")
        )
        if not is_decision:
            continue

        # Decision description
        if "missing acceptance criteria" in reason_lower or "ac missing" in notes_lower:
            decision = "Approve scope or define acceptance criteria"
            why = "This item cannot be built without clear acceptance criteria."
        elif "not defined" in reason_lower or "permissions" in reason_lower:
            decision = "Define role and permission boundaries"
            why = "Without defined permissions, implementation may not match expectations."
        elif "not ready" in notes_lower or "backlog" in notes_lower:
            decision = "Decide if this story should proceed or be deferred"
            why = "Unresolved scope creates delivery risk for this sprint."
        elif status.lower() in ("blocked", "flagged"):
            decision = "Unblock or reassign this item"
            why = "A blocked item may delay dependent stories."
        else:
            decision = "Review and confirm approach before development"
            why = "High-risk item may require stakeholder alignment."

        full_url = issue_url or f"{_JIRA_BASE_URL}/{issue_key}"
        decisions.append(DecisionEntry(
            issue_key=issue_key,
            issue_url=full_url,
            title=title,
            decision_needed=decision,
            why_it_matters=why,
        ))
    return decisions

_DEFAULT_STAKEHOLDERS = [
    ("Product / Delivery Owner", "@Nadin Gut", "Sprint scope and stakeholder visibility"),
    ("QA / Quality Owner", "@Nadin Gut", "Requirement readiness and test coverage review"),
]


def _issue_link(issue_key: str, issue_url: Optional[str]) -> str:
    """Return an HTML anchor for the issue, generating the URL if not provided."""
    url = issue_url or f"{_JIRA_BASE_URL}/{issue_key}"
    return f'<a href="{url}">{issue_key}</a>'


def _render_confluence_sprint_body(
    sprint_name: str,
    executive_summary: str,
    sprint_health_score: int,
    delivery_confidence: str,
    total_issues: int,
    high_risk_count: int,
    clarification_count: int,
    sprint_scope: list,
    qa_focus_areas: list,
    decisions_needed: list,
) -> tuple[str, str]:
    """
    Render sprint analysis as stakeholder-facing Confluence storage-format HTML.

    Returns (page_title, page_body_storage).
    Uses safe HTML tags (h1, h2, p, table, tr, th, td, ul, li, strong, a) plus
    ac:structured-macro for the live Jira sprint board integration.
    No markdown, no escaped newlines, no leading "=".

    Sections:
    1. H1: {Sprint Name} Dashboard
    2. Executive Summary
    3. Stakeholders
    4. Sprint Snapshot  (metrics table + status breakdown)
    5. Sprint Scope  (Issue, Title, Status, Risk, Reason, Acceptance Criteria / Notes)
    6. QA Focus Areas
    7. Decision Needed  (Issue, Decision Needed)
    """
    parts = []

    # Clean sprint name - remove any leading "=" that might exist
    clean_sprint_name = sprint_name.lstrip("=").strip()

    # 1. Title
    parts.append(f"<h1>{clean_sprint_name} Dashboard</h1>")

    # 2. Executive Summary
    parts.append("<h2>Executive Summary</h2>")
    parts.append(f"<p>{executive_summary}</p>")

    # 3. Stakeholders
    parts.append("<h2>Stakeholders</h2>")
    parts.append("<table>")
    parts.append("<tr><th>Role</th><th>Name</th><th>Responsibility</th></tr>")
    for role, name, responsibility in _DEFAULT_STAKEHOLDERS:
        parts.append(f"<tr><td>{role}</td><td>{name}</td><td>{responsibility}</td></tr>")
    parts.append("</table>")

    # 4. Sprint Snapshot (metrics + status breakdown)
    parts.append("<h2>Sprint Snapshot</h2>")
    parts.append("<table>")
    parts.append("<tr><th>Metric</th><th>Value</th></tr>")
    parts.append(f"<tr><td>Sprint Health Score</td><td>{sprint_health_score}/100</td></tr>")
    parts.append(f"<tr><td>Delivery Confidence</td><td>{delivery_confidence}</td></tr>")
    parts.append(f"<tr><td>Total Issues</td><td>{total_issues}</td></tr>")
    parts.append(f"<tr><td>High Risk Items</td><td>{high_risk_count}</td></tr>")
    parts.append(f"<tr><td>Items Needing Clarification</td><td>{clarification_count}</td></tr>")
    parts.append("</table>")
    status_counts: dict[str, int] = {}
    for entry in sprint_scope:
        raw_status = (entry.status if hasattr(entry, 'status') else entry.get('status')) or "Unknown"
        status_counts[raw_status] = status_counts.get(raw_status, 0) + 1
    # Standardise well-known statuses; collect remainder as-is
    snapshot_rows: list[tuple[str, int]] = []
    for label in ("To Do", "In Progress", "Done"):
        count = status_counts.pop(label, 0)
        snapshot_rows.append((label, count))
    blocked_count = status_counts.pop("Blocked", 0) + status_counts.pop("Flagged", 0)
    for other_status, cnt in status_counts.items():
        if other_status != "Unknown":
            blocked_count += cnt
    snapshot_rows.append(("Blocked / Flagged", blocked_count))
    parts.append("<table>")
    parts.append("<tr><th>Status</th><th>Count</th></tr>")
    for label, count in snapshot_rows:
        parts.append(f"<tr><td>{label}</td><td>{count}</td></tr>")
    parts.append("</table>")

    # 5. Sprint Scope
    parts.append("<h2>Sprint Scope</h2>")
    if sprint_scope:
        parts.append("<table>")
        parts.append("<tr><th>Issue</th><th>Title</th><th>Status</th><th>Risk</th><th>Reason</th><th>Acceptance Criteria / Notes</th></tr>")
        for entry in sprint_scope:
            if hasattr(entry, 'issue_key'):
                issue_key = entry.issue_key
                title = entry.title
                status = entry.status or "—"
                risk = entry.risk
                reason = entry.reason
                notes = entry.notes
                issue_url = entry.issue_url
            else:
                issue_key = entry.get('issue_key', '')
                title = entry.get('title', '')
                status = entry.get('status') or "—"
                risk = entry.get('risk', 'Medium')
                reason = entry.get('reason', '')
                notes = entry.get('notes', '')
                issue_url = entry.get('issue_url')
            issue_cell = _issue_link(issue_key, issue_url)
            parts.append(f"<tr><td>{issue_cell}</td><td>{title}</td><td>{status}</td><td>{risk}</td><td>{reason}</td><td>{notes}</td></tr>")
        parts.append("</table>")
    else:
        parts.append("<p>No issues in sprint scope.</p>")

    # 6. QA Focus Areas
    parts.append("<h2>QA Focus Areas</h2>")
    parts.append("<ul>")
    parts.append("<li>Maintain 97% pass rate on new feature tests and regression suite.</li>")
    for area in qa_focus_areas:
        parts.append(f"<li>{area}</li>")
    parts.append("</ul>")

    # 7. Decision Needed
    parts.append("<h2>Decision Needed</h2>")
    if decisions_needed:
        parts.append("<table>")
        parts.append("<tr><th>Issue</th><th>Decision Needed</th></tr>")
        for d in decisions_needed:
            if hasattr(d, 'issue_key'):
                issue_key = d.issue_key
                issue_url = d.issue_url
                decision = d.decision_needed
            else:
                issue_key = d.get('issue_key', '')
                issue_url = d.get('issue_url', '')
                decision = d.get('decision_needed', '')
            issue_cell = _issue_link(issue_key, issue_url)
            parts.append(f"<tr><td>{issue_cell}</td><td>{decision}</td></tr>")
        parts.append("</table>")
    else:
        parts.append("<p>No stakeholder decisions currently detected.</p>")

    page_body = "".join(parts)
    page_title = f"{clean_sprint_name} Dashboard"
    return (page_title, page_body)


def _render_confluence_sprint_page(analysis: "SprintAnalysisResponse") -> dict:
    """
    Render sprint analysis as Confluence storage-format HTML.
    Wrapper for _render_confluence_sprint_body that accepts SprintAnalysisResponse.
    """
    page_title, page_body = _render_confluence_sprint_body(
        sprint_name=analysis.sprint_name,
        executive_summary=analysis.executive_summary,
        sprint_health_score=analysis.sprint_health_score,
        delivery_confidence=analysis.delivery_confidence,
        total_issues=analysis.total_issues,
        high_risk_count=analysis.high_risk_count,
        clarification_count=analysis.clarification_count,
        sprint_scope=analysis.sprint_scope,
        qa_focus_areas=analysis.qa_focus_areas,
        decisions_needed=analysis.decisions_needed,
    )
    return {
        "page_title": page_title,
        "page_body_storage": page_body
    }


def _render_jira_comment(report: RequirementReadinessReport) -> str:
    """Render report as a Jira-compatible comment (plain text, no wiki markup)."""
    # Use the jira_formatter module for consistent plain-text output
    return format_jira_comment(report)


def _render_confluence_page(report: RequirementReadinessReport, issue_key: Optional[str] = None) -> tuple[str, str]:
    """Render report as Confluence page content (XHTML storage format)."""
    title_prefix = f"{issue_key}: " if issue_key else ""
    page_title = f"{title_prefix}Requirement Readiness Report"
    
    rec = report.recommendation.value if report.recommendation else "unknown"
    color_map = {"ready": "green", "needs_review": "yellow", "needs_refinement": "orange", "not_ready": "red"}
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
    
    Domain context is auto-classified based on keywords in title, description, and labels.
    Explicit domain_context in request overrides auto-classification.
    
    The report includes:
    - Readiness score (0-100)
    - Recommendation (ready, needs_refinement, high_risk, not_ready)
    - Missing information
    - Acceptance criteria
    - Edge cases
    - Product/QA/Technical risks
    - Suggested test scenarios
    - Clarification questions
    - Selected domain context
    """
    # Auto-classify domain context if not explicitly provided
    if request.domain_context:
        selected_context = request.domain_context
    else:
        selected_context = classify_domain_context(
            title=request.title,
            description=request.description or "",
            labels=request.labels
        )
    
    # Update request with selected context for analysis
    request.domain_context = selected_context
    
    report = _analyze_requirement(request, demo_mode, provider)
    
    return AnalyzeResponse(
        issue_key=request.issue_key,
        readiness_score=report.readiness_score,
        recommendation=report.recommendation.value if report.recommendation else "unknown",
        risk_level=_compute_risk_level(report),
        qa_complexity=_compute_qa_complexity(report),
        clarification_count=len(report.clarification_questions),
        automation_candidate=_compute_automation_candidate(report),
        selected_domain_context=selected_context,
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
    
    Domain context is auto-classified based on keywords in title, description, and labels.
    Explicit domain_context in request overrides auto-classification.
    
    Returns plain text (no wiki markup) that can be posted directly as a Jira comment.
    Ideal for automation workflows that add comments to Jira issues.
    """
    # Auto-classify domain context if not explicitly provided
    if request.domain_context:
        selected_context = request.domain_context
    else:
        selected_context = classify_domain_context(
            title=request.title,
            description=request.description or "",
            labels=request.labels
        )
    
    # Update request with selected context for analysis
    request.domain_context = selected_context
    
    report = _analyze_requirement(request, demo_mode, provider)
    comment = format_jira_comment(
        report,
        issue_key=request.issue_key,
        selected_domain_context=selected_context
    )
    
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


@app.post("/analyze/sprint", response_model=SprintAnalysisResponse, tags=["Analysis"])
async def analyze_sprint(
    request: SprintAnalysisRequest,
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
    Analyze all issues in a sprint and return sprint-level health metrics.
    
    Each issue is classified into its own domain context based on title, description, and labels.
    If explicit domain_context is provided in the request, all issues use that context.
    Otherwise, each issue is analyzed with its individually classified context.
    
    Provides:
    - Context distribution (domain_context -> issue_count)
    - Sprint health score (0-100)
    - Delivery confidence (Low/Medium/High)
    - Issue readiness breakdown
    - Risky entries with reasons
    - Top risks and QA focus areas
    - Recommended actions
    - Executive summary
    
    Uses labels (needs-refinement, needs-review, ready-for-sprint) when present.
    Treats needs-refinement in active sprint as a sprint risk.
    """
    total_issues = len(request.issues)
    
    # Track context distribution
    context_distribution: dict[str, int] = {}
    
    # Analyze each issue with its own classified context (unless explicit context provided)
    issue_results = []
    for issue in request.issues:
        # Determine context for this issue
        if request.domain_context:
            # Explicit context overrides auto-classification for all issues
            issue_context = request.domain_context
        else:
            # Auto-classify each issue individually
            issue_context = classify_domain_context(
                title=issue.title,
                description=issue.description or "",
                labels=issue.labels
            )
        
        # Track distribution
        context_distribution[issue_context] = context_distribution.get(issue_context, 0) + 1
        
        # Analyze with the issue's context
        result = _analyze_sprint_issue(issue, issue_context, demo_mode, provider)
        result["issue_key"] = issue.issue_key
        result["title"] = issue.title
        result["priority"] = issue.priority
        result["domain_context"] = issue_context
        issue_results.append(result)
    
    # Count by readiness
    ready_count = sum(1 for r in issue_results if r["readiness"] == "ready")
    needs_review_count = sum(1 for r in issue_results if r["readiness"] == "needs_review")
    needs_refinement_count = sum(1 for r in issue_results if r["readiness"] == "needs_refinement")
    not_ready_count = sum(1 for r in issue_results if r["readiness"] == "not_ready")
    
    # Compute sprint health using label-based formula
    issue_labels_list = [issue.labels for issue in request.issues]
    sprint_health = _compute_sprint_health_from_labels(issue_labels_list)
    
    # Build sprint scope entries for ALL issues
    sprint_scope = []
    for i, r in enumerate(issue_results):
        issue = request.issues[i]
        risk_level = r["risk_level"]
        # Normalize risk to Low/Medium/High
        if risk_level in ["Critical", "High"]:
            normalized_risk = "High"
        elif risk_level == "Medium":
            normalized_risk = "Medium"
        else:
            normalized_risk = "Low"
        
        reason = _generate_stakeholder_reason(
            r["readiness"], risk_level, r["risks"], r["clarification_count"]
        )
        notes = _generate_scope_notes(
            r["readiness"], risk_level, r["clarification_count"]
        )
        
        sprint_scope.append(SprintScopeEntry(
            issue_key=issue.issue_key,
            title=issue.title,
            assignee=issue.assignee,
            status=issue.status,
            risk=normalized_risk,
            reason=reason,
            notes=notes,
            issue_url=issue.issue_url
        ))
    
    # Count high risk items
    high_risk_count = sum(1 for entry in sprint_scope if entry.risk == "High")
    
    # Total clarification count
    total_clarifications = sum(r["clarification_count"] for r in issue_results)
    
    # Collect risky entries (deprecated, kept for backward compatibility)
    risky_entries = [
        RiskyEntry(
            issue_key=r["issue_key"],
            title=r["title"],
            reason=r["reason"] if r["reason"] else "Elevated risk",
            risk=r["risk_level"]
        )
        for r in issue_results if r["is_risky"]
    ]
    risky_count = len(risky_entries)
    
    # Compute delivery confidence
    risky_ratio = risky_count / total_issues if total_issues > 0 else 0
    delivery_confidence = _compute_delivery_confidence(sprint_health, risky_ratio)
    
    # Collect top risks (deduplicated)
    all_risks = []
    for r in issue_results:
        all_risks.extend(r["risks"])
    # Deduplicate while preserving order
    seen_risks = set()
    top_risks = []
    for risk in all_risks:
        if risk not in seen_risks:
            seen_risks.add(risk)
            top_risks.append(risk)
            if len(top_risks) >= 5:
                break
    
    # Collect QA focus areas (deduplicated)
    all_qa_areas = []
    for r in issue_results:
        all_qa_areas.extend(r["qa_areas"])
    seen_qa = set()
    qa_focus_areas = []
    for area in all_qa_areas:
        if area not in seen_qa:
            seen_qa.add(area)
            qa_focus_areas.append(area)
            if len(qa_focus_areas) >= 5:
                break
    
    # Identify blocked candidates
    blocked_candidates = [
        f"{r['issue_key']}: {r['title']}"
        for r in issue_results if r["is_blocker"]
    ][:3]
    
    # Generate recommended actions
    recommended_actions = []
    if needs_refinement_count > 0:
        recommended_actions.append(
            f"Schedule refinement session for {needs_refinement_count} issue(s) before sprint starts"
        )
    if not_ready_count > 0:
        recommended_actions.append(
            f"Consider moving {not_ready_count} not-ready issue(s) to backlog"
        )
    high_priority_risky = [r for r in issue_results if r["is_risky"] and r.get("priority") in ["High", "Highest", "Critical"]]
    if high_priority_risky:
        recommended_actions.append(
            f"Review {len(high_priority_risky)} high-priority risky item(s) with Product Owner"
        )
    total_clarifications = sum(r["clarification_count"] for r in issue_results)
    if total_clarifications > 5:
        recommended_actions.append(
            f"Address {total_clarifications} clarification questions across sprint issues"
        )
    if not recommended_actions:
        if delivery_confidence == "High":
            recommended_actions.append("Sprint is well-prepared. Proceed with confidence.")
        else:
            recommended_actions.append("Monitor risky items during sprint execution.")
    
    # Generate executive summary (delivery-focused: what, systems, outcome)
    executive_summary = _generate_executive_summary(
        sprint_name=request.sprint_name,
        delivery_confidence=delivery_confidence,
        total_issues=total_issues,
        issues=request.issues,
    )

    # Build decisions needed for stakeholder section
    decisions_needed = _build_decisions_needed(sprint_scope, request.issues)

    # Generate Confluence page (included inline to avoid separate API call)
    confluence_page_title, confluence_page_body_storage = _render_confluence_sprint_body(
        sprint_name=request.sprint_name,
        executive_summary=executive_summary,
        sprint_health_score=sprint_health,
        delivery_confidence=delivery_confidence,
        total_issues=total_issues,
        high_risk_count=high_risk_count,
        clarification_count=total_clarifications,
        sprint_scope=sprint_scope,
        qa_focus_areas=qa_focus_areas,
        decisions_needed=decisions_needed,
    )

    return SprintAnalysisResponse(
        sprint_name=request.sprint_name,
        sprint_id=request.sprint_id,
        context_distribution=context_distribution,
        sprint_health_score=sprint_health,
        delivery_confidence=delivery_confidence,
        total_issues=total_issues,
        high_risk_count=high_risk_count,
        clarification_count=total_clarifications,
        ready_count=ready_count,
        needs_review_count=needs_review_count,
        needs_refinement_count=needs_refinement_count,
        not_ready_count=not_ready_count,
        sprint_scope=sprint_scope,
        risky_entries=risky_entries,
        top_risks=top_risks,
        qa_focus_areas=qa_focus_areas,
        blocked_candidates=blocked_candidates,
        recommended_actions=recommended_actions,
        decisions_needed=decisions_needed,
        executive_summary=executive_summary,
        confluence_page_title=confluence_page_title,
        confluence_page_body_storage=confluence_page_body_storage
    )


@app.post("/format/confluence-sprint-page", response_model=ConfluenceSprintPageResponse, tags=["Formatting"])
async def format_confluence_sprint_page(request: ConfluenceSprintPageRequest):
    """
    Format sprint analysis as a Confluence page in storage format.
    
    Takes the output from /analyze/sprint and generates a Confluence-compatible
    HTML page with all sprint quality metrics.
    
    Sections included:
    1. Sprint Quality Dashboard title
    2. Executive Summary
    3. Sprint Health Score
    4. Delivery Confidence
    5. Readiness Distribution
    6. Risky Sprint Entries
    7. Top Risks
    8. QA Focus Areas
    9. Recommended Actions
    10. Story Breakdown
    
    Uses only safe HTML tags (h1, h2, h3, p, ul, li, table, tr, th, td, strong).
    No markdown, no escaped newlines.
    """
    result = _render_confluence_sprint_page(request.sprint_analysis)
    
    return ConfluenceSprintPageResponse(
        page_title=result["page_title"],
        page_body_storage=result["page_body_storage"]
    )


@app.post("/format/jira-comment", response_model=JiraCommentResponse, tags=["Formatting"])
async def format_jira_comment_endpoint(request: JiraCommentFormatRequest):
    """
    Format combined analysis + acceptance criteria data as a Jira comment.
    
    Accepts pre-computed analysis data and returns a plain-text Jira comment.
    Use this when you have separate analysis and AC generation results to combine.
    
    Returns plain text with real line breaks (no wiki markup).
    """
    from .jira_formatter import _sanitize_issue_key, _format_recommendation
    
    lines: list[str] = []
    
    # Sanitize issue key
    clean_issue_key = _sanitize_issue_key(request.issue_key)
    
    # Title
    title_suffix = f" — {clean_issue_key}" if clean_issue_key else ""
    lines.append(f"AI Requirement Readiness Analysis{title_suffix}")
    lines.append("")
    
    # Readiness score and recommendation
    lines.append(f"Readiness Score: {request.readiness_score}/100")
    lines.append(f"Recommendation: {_format_recommendation(request.recommendation)}")
    lines.append("")
    
    # Main concerns
    if request.main_concerns:
        lines.append("Main Concerns:")
        for concern in request.main_concerns[:3]:
            lines.append(f"• {concern}")
        lines.append("")
    
    # Clarification questions
    if request.clarification_questions:
        lines.append("Clarification Questions:")
        for i, q in enumerate(request.clarification_questions[:5], 1):
            lines.append(f"{i}. {q}")
        lines.append("")
    
    # Acceptance criteria
    if request.acceptance_criteria:
        lines.append("Suggested Acceptance Criteria:")
        for ac in request.acceptance_criteria[:5]:
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
    if request.readiness_score >= 80:
        lines.append("Ready for test planning.")
    elif request.readiness_score >= 60:
        lines.append("Address clarification questions before test planning.")
    elif request.readiness_score >= 40:
        lines.append("Significant gaps — schedule refinement session.")
    else:
        lines.append("Not ready — return to Product Owner for clarification.")
    lines.append("")
    
    # AI note
    lines.append("AI Note:")
    lines.append("AI-assisted review. Human PM/QA validation required.")
    
    return JiraCommentResponse(
        issue_key=clean_issue_key,
        jira_comment="\n".join(lines)
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
    
    Domain context is auto-classified based on keywords in title, description, and labels.
    Explicit domain_context in request overrides auto-classification.
    
    Uses domain context to provide relevant suggestions:
    - **cdn_edge_networking**: Cache, routing, TLS, origin protection
    - **authentication_security**: Login, permissions, session management
    - **control_panel**: Permission checks, audit logging, concurrent access
    - **ci_cd_delivery**: Pipeline, deployment, release automation
    - **embedded_device**: Resource constraints, power management, communication
    - **media_streaming**: DRM, buffering, adaptive bitrate
    - **generic_web** (default): Standard web app patterns
    
    Returns structured JSON with:
    - Up to 5 acceptance criteria (Given/When/Then format)
    - Up to 5 edge cases (failure modes, permissions, empty states, invalid input, concurrency)
    - Up to 5 test scenarios (positive, negative, boundary)
    - Up to 5 automation candidates (CI/CD worthy scenarios)
    - Selected domain context
    """
    # Auto-classify domain context if not explicitly provided
    if request.domain_context:
        selected_context = request.domain_context
    else:
        selected_context = classify_domain_context(
            title=request.title,
            description=request.description or "",
            labels=request.labels
        )
    
    result = _generate_acceptance_criteria(
        title=request.title,
        description=request.description,
        domain_context=selected_context
    )
    
    return AcceptanceCriteriaResponse(
        issue_key=request.issue_key,
        selected_domain_context=selected_context,
        acceptance_criteria=[
            AcceptanceCriterion(**ac) for ac in result["acceptance_criteria"]
        ],
        edge_cases=result["edge_cases"],
        test_scenarios=[
            TestScenario(**ts) for ts in result["test_scenarios"]
        ],
        automation_candidates=result["automation_candidates"]
    )
