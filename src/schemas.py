from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from enum import Enum


class ReadinessScore(str, Enum):
    READY = "ready"
    MOSTLY_READY = "mostly_ready"
    PARTIALLY_READY = "partially_ready"
    NOT_READY = "not_ready"


class Issue(BaseModel):
    category: str = Field(description="Category of the issue (e.g., clarity, completeness, testability)")
    severity: str = Field(description="Severity level (low, medium, high, critical)")
    description: str = Field(description="Description of the issue")
    suggestion: str = Field(description="Suggested fix or improvement")


class Strength(BaseModel):
    category: str = Field(description="Category of the strength")
    description: str = Field(description="Description of what makes this requirement strong")


class RequirementAnalysis(BaseModel):
    requirement_summary: str = Field(description="Brief summary of the requirement")
    readiness_score: ReadinessScore = Field(description="Overall readiness assessment")
    confidence_score: float = Field(description="Confidence in the analysis (0.0-1.0)")
    strengths: List[Strength] = Field(description="What makes this requirement well-written")
    issues: List[Issue] = Field(description="Issues that need to be addressed")
    acceptance_criteria_assessment: str = Field(description="Assessment of acceptance criteria quality")
    testability_assessment: str = Field(description="Assessment of how testable the requirement is")
    next_steps: List[str] = Field(description="Recommended next steps for the PM/team")
    estimated_implementation_complexity: str = Field(description="Estimated complexity (low, medium, high)")


class RequirementReadinessRecommendation(str, Enum):
    READY = "ready"
    NEEDS_REFINEMENT = "needs_refinement"
    HIGH_RISK = "high_risk"
    NOT_READY = "not_ready"


class TestScenarioType(str, Enum):
    FUNCTIONAL = "functional"
    NEGATIVE = "negative"
    REGRESSION = "regression"
    NON_FUNCTIONAL = "non_functional"
    INTEGRATION = "integration"


class TestScenarioPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SuggestedTestScenario(BaseModel):
    title: str
    type: TestScenarioType
    priority: TestScenarioPriority
    description: str


class ScoreBreakdown(BaseModel):
    clarity: int = Field(ge=0, le=100)
    acceptance_criteria_quality: int = Field(ge=0, le=100)
    testability: int = Field(ge=0, le=100)
    edge_case_coverage: int = Field(ge=0, le=100)
    dependency_clarity: int = Field(ge=0, le=100)
    risk_visibility: int = Field(ge=0, le=100)
    observability_expectations: int = Field(ge=0, le=100)

    def average(self) -> float:
        values = [
            self.clarity,
            self.acceptance_criteria_quality,
            self.testability,
            self.edge_case_coverage,
            self.dependency_clarity,
            self.risk_visibility,
            self.observability_expectations,
        ]
        return sum(values) / len(values)

    def weighted_score(self) -> int:
        weights = {
            "clarity": 20,
            "acceptance_criteria_quality": 20,
            "testability": 20,
            "edge_case_coverage": 15,
            "dependency_clarity": 10,
            "risk_visibility": 10,
            "observability_expectations": 5,
        }
        weighted = (
            self.clarity * weights["clarity"]
            + self.acceptance_criteria_quality * weights["acceptance_criteria_quality"]
            + self.testability * weights["testability"]
            + self.edge_case_coverage * weights["edge_case_coverage"]
            + self.dependency_clarity * weights["dependency_clarity"]
            + self.risk_visibility * weights["risk_visibility"]
            + self.observability_expectations * weights["observability_expectations"]
        )
        return int(round(weighted / 100))


class RequirementReadinessReport(BaseModel):
    original_requirement: str
    summary: str
    rewritten_user_story: str
    readiness_score: int = Field(ge=0, le=100)
    recommendation: Optional[RequirementReadinessRecommendation] = None
    score_breakdown: ScoreBreakdown
    missing_information: List[str]
    acceptance_criteria: List[str]
    edge_cases: List[str]
    product_risks: List[str]
    qa_risks: List[str]
    technical_risks: List[str]
    suggested_test_scenarios: List[SuggestedTestScenario]
    automation_candidates: List[str]
    clarification_questions: List[str]
    human_review_notes: List[str]

    @staticmethod
    def derive_recommendation(score: int) -> RequirementReadinessRecommendation:
        if score >= 85:
            return RequirementReadinessRecommendation.READY
        if score >= 70:
            return RequirementReadinessRecommendation.NEEDS_REFINEMENT
        if score >= 50:
            return RequirementReadinessRecommendation.HIGH_RISK
        return RequirementReadinessRecommendation.NOT_READY

    @model_validator(mode="after")
    def validate_breakdown_and_recommendation(self) -> "RequirementReadinessReport":
        approx_score = self.score_breakdown.weighted_score()
        if abs(approx_score - self.readiness_score) > 15:
            raise ValueError(
                "score_breakdown weighted score should approximately match readiness_score "
                f"(breakdown_weighted={approx_score}, readiness_score={self.readiness_score})"
            )

        if self.recommendation is None:
            self.recommendation = self.derive_recommendation(self.readiness_score)
        return self
