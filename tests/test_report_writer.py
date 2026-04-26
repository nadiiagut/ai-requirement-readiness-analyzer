from src.report_writer import ReportWriter
from src.schemas import RequirementReadinessReport


def test_markdown_report_generation_contains_required_sections(sample_report_payload: dict):
    report = RequirementReadinessReport(**sample_report_payload)
    writer = ReportWriter()

    md = writer.generate_markdown_report(report, input_path="examples/sample.md")

    # Top-level header
    assert "# Requirement Readiness Report" in md

    # Required sections
    required_headers = [
        "## Executive Summary",
        "## Readiness Score",
        "## Recommendation",
        "## Rewritten User Story",
        "## Score Breakdown",
        "## Missing Information",
        "## Acceptance Criteria",
        "## Edge Cases",
        "## Risks",
        "### Product Risks",
        "### QA Risks",
        "### Technical Risks",
        "## Suggested Test Scenarios",
        "## Automation Candidates",
        "## Clarification Questions",
        "## Human Review Notes",
    ]
    for header in required_headers:
        assert header in md

    # Confluence-friendly tables exist
    assert "| Dimension | Score | Weight |" in md
    assert "| Title | Type | Priority | Description |" in md

    # A couple of content checks
    assert report.summary in md
    assert report.rewritten_user_story in md
    assert str(report.readiness_score) in md
