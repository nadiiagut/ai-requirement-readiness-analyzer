from pydantic import BaseModel, Field, model_validator
from typing import ClassVar, Dict, List, Optional
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
    NEEDS_REVIEW = "needs_review"
    NEEDS_REFINEMENT = "needs_refinement"
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
    clarity: int = Field(default=0)
    acceptance_criteria_quality: int = Field(default=0)
    testability: int = Field(default=0)
    edge_case_coverage: int = Field(default=0)
    dependency_clarity: int = Field(default=0)
    risk_visibility: int = Field(default=0)
    observability_expectations: int = Field(default=0)

    # Weights for each dimension (max contribution to total score)
    WEIGHTS: ClassVar[Dict[str, int]] = {
        "clarity": 20,
        "acceptance_criteria_quality": 20,
        "testability": 20,
        "edge_case_coverage": 15,
        "dependency_clarity": 10,
        "risk_visibility": 10,
        "observability_expectations": 5,
    }

    @model_validator(mode="after")
    def clamp_scores(self) -> "ScoreBreakdown":
        """Clamp all score values to 0-100 range."""
        self.clarity = max(0, min(100, self.clarity))
        self.acceptance_criteria_quality = max(0, min(100, self.acceptance_criteria_quality))
        self.testability = max(0, min(100, self.testability))
        self.edge_case_coverage = max(0, min(100, self.edge_case_coverage))
        self.dependency_clarity = max(0, min(100, self.dependency_clarity))
        self.risk_visibility = max(0, min(100, self.risk_visibility))
        self.observability_expectations = max(0, min(100, self.observability_expectations))
        return self

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
        """
        Calculate weighted score based on dimension weights.
        Each dimension contributes (value/100) * weight to the total.
        Total max = 100.
        """
        weighted = (
            (self.clarity / 100) * self.WEIGHTS["clarity"]
            + (self.acceptance_criteria_quality / 100) * self.WEIGHTS["acceptance_criteria_quality"]
            + (self.testability / 100) * self.WEIGHTS["testability"]
            + (self.edge_case_coverage / 100) * self.WEIGHTS["edge_case_coverage"]
            + (self.dependency_clarity / 100) * self.WEIGHTS["dependency_clarity"]
            + (self.risk_visibility / 100) * self.WEIGHTS["risk_visibility"]
            + (self.observability_expectations / 100) * self.WEIGHTS["observability_expectations"]
        )
        return int(round(weighted))


class RequirementReadinessReport(BaseModel):
    original_requirement: str
    summary: str
    rewritten_user_story: str
    readiness_score: int = Field(default=0)
    recommendation: Optional[RequirementReadinessRecommendation] = None
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    missing_information: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    edge_cases: List[str] = Field(default_factory=list)
    product_risks: List[str] = Field(default_factory=list)
    qa_risks: List[str] = Field(default_factory=list)
    technical_risks: List[str] = Field(default_factory=list)
    suggested_test_scenarios: List[SuggestedTestScenario] = Field(default_factory=list)
    automation_candidates: List[str] = Field(default_factory=list)
    clarification_questions: List[str] = Field(default_factory=list)
    human_review_notes: List[str] = Field(default_factory=list)

    @staticmethod
    def derive_recommendation(score: int) -> RequirementReadinessRecommendation:
        if score >= 80:
            return RequirementReadinessRecommendation.READY
        if score >= 60:
            return RequirementReadinessRecommendation.NEEDS_REVIEW
        if score >= 40:
            return RequirementReadinessRecommendation.NEEDS_REFINEMENT
        return RequirementReadinessRecommendation.NOT_READY

    @model_validator(mode="after")
    def calculate_score_and_recommendation(self) -> "RequirementReadinessReport":
        """
        Auto-calculate readiness_score from score_breakdown.
        Add warning if model-provided score differs significantly.
        Derive recommendation from final calculated score.
        """
        calculated_score = self.score_breakdown.weighted_score()
        model_score = self.readiness_score

        # Clamp model score to valid range before comparison
        model_score_clamped = max(0, min(100, model_score))

        # Check if adjustment is needed
        if model_score != model_score_clamped or abs(calculated_score - model_score_clamped) > 5:
            warning = (
                f"Score adjusted: model provided {model_score}, "
                f"calculated from breakdown is {calculated_score}. "
                f"Using calculated score."
            )
            if warning not in self.human_review_notes:
                self.human_review_notes = list(self.human_review_notes) + [warning]

        # Always use calculated score from breakdown
        self.readiness_score = calculated_score

        # Derive recommendation from final score
        self.recommendation = self.derive_recommendation(self.readiness_score)

        return self
