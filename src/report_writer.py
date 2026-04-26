from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .schemas import RequirementReadinessReport


class ReportWriter:
    def _list_section(self, title: str, items: list[str]) -> str:
        if not items:
            return f"## {title}\n\n- None\n"

        lines = [f"## {title}", ""]
        for item in items:
            lines.append(f"- {item}")
        lines.append("")
        return "\n".join(lines)

    def generate_markdown_report(self, report: RequirementReadinessReport, *, input_path: str) -> str:
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        md: list[str] = []
        md.append("# Requirement Readiness Report")
        md.append("")
        md.append(f"**Generated:** {generated_at}  ")
        md.append(f"**Input:** `{input_path}`")
        md.append("")

        md.append("## Executive Summary")
        md.append("")
        md.append(report.summary)
        md.append("")

        md.append("## Readiness Score")
        md.append("")
        md.append(f"**{report.readiness_score}/100**")
        md.append("")

        md.append("## Recommendation")
        md.append("")
        md.append(f"**{report.recommendation.value if report.recommendation else ''}**")
        md.append("")

        md.append("## Rewritten User Story")
        md.append("")
        md.append(report.rewritten_user_story)
        md.append("")

        md.append("## Score Breakdown")
        md.append("")
        md.append("| Dimension | Score | Weight |")
        md.append("|---|---:|---:|")
        md.append(f"| Clarity | {report.score_breakdown.clarity}/100 | 20% |")
        md.append(
            f"| Acceptance criteria quality | {report.score_breakdown.acceptance_criteria_quality}/100 | 20% |"
        )
        md.append(f"| Testability | {report.score_breakdown.testability}/100 | 20% |")
        md.append(
            f"| Edge case coverage | {report.score_breakdown.edge_case_coverage}/100 | 15% |"
        )
        md.append(
            f"| Dependency clarity | {report.score_breakdown.dependency_clarity}/100 | 10% |"
        )
        md.append(f"| Risk visibility | {report.score_breakdown.risk_visibility}/100 | 10% |")
        md.append(
            f"| Observability expectations | {report.score_breakdown.observability_expectations}/100 | 5% |"
        )
        md.append("")

        md.append(self._list_section("Missing Information", report.missing_information).rstrip())
        md.append("")
        md.append(self._list_section("Acceptance Criteria", report.acceptance_criteria).rstrip())
        md.append("")
        md.append(self._list_section("Edge Cases", report.edge_cases).rstrip())
        md.append("")

        md.append("## Risks")
        md.append("")
        md.append("### Product Risks")
        md.append("")
        if report.product_risks:
            for r in report.product_risks:
                md.append(f"- {r}")
        else:
            md.append("- None")
        md.append("")
        md.append("### QA Risks")
        md.append("")
        if report.qa_risks:
            for r in report.qa_risks:
                md.append(f"- {r}")
        else:
            md.append("- None")
        md.append("")
        md.append("### Technical Risks")
        md.append("")
        if report.technical_risks:
            for r in report.technical_risks:
                md.append(f"- {r}")
        else:
            md.append("- None")
        md.append("")

        md.append("## Suggested Test Scenarios")
        md.append("")
        if report.suggested_test_scenarios:
            md.append("| Title | Type | Priority | Description |")
            md.append("|---|---|---|---|")
            for s in report.suggested_test_scenarios:
                title = s.title.replace("\n", " ").strip()
                desc = s.description.replace("\n", " ").strip()
                md.append(f"| {title} | {s.type.value} | {s.priority.value} | {desc} |")
        else:
            md.append("- None")
        md.append("")

        md.append(self._list_section("Automation Candidates", report.automation_candidates).rstrip())
        md.append("")
        md.append(self._list_section("Clarification Questions", report.clarification_questions).rstrip())
        md.append("")
        md.append(self._list_section("Human Review Notes", report.human_review_notes).rstrip())
        md.append("")

        return "\n".join(md).rstrip() + "\n"

    def save_report(
        self,
        report: RequirementReadinessReport,
        *,
        input_path: str,
        output_markdown_path: str,
    ) -> tuple[str, str]:
        md_path = Path(output_markdown_path)
        json_path = md_path.with_suffix(".json")

        md_path.parent.mkdir(parents=True, exist_ok=True)

        md_content = self.generate_markdown_report(report, input_path=input_path)
        md_path.write_text(md_content, encoding="utf-8")
        json_path.write_text(
            json.dumps(report.model_dump(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        return str(md_path), str(json_path)
