import argparse
import json
import sys
from pathlib import Path
from typing import Optional
from rich.console import Console

from .llm_client import LLMClientError, MissingAPIKeyError, analyze_requirement
from .prompt_builder import PromptBuilder
from .schemas import RequirementReadinessReport

console = Console(stderr=True)  # Use stderr for status messages, keep stdout clean for piping


def _render_markdown(report: RequirementReadinessReport, *, input_path: str) -> str:
    lines: list[str] = []
    lines.append("# Requirement Readiness Report")
    lines.append("")
    lines.append(f"**Input:** `{input_path}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(report.summary)
    lines.append("")
    lines.append("## Readiness")
    lines.append("")
    lines.append(f"- **Readiness score:** {report.readiness_score}/100")
    lines.append(f"- **Recommendation:** {report.recommendation.value if report.recommendation else ''}")
    lines.append("")
    lines.append("### Score breakdown")
    lines.append("")
    lines.append(f"- Clarity: {report.score_breakdown.clarity}/100")
    lines.append(
        f"- Acceptance criteria quality: {report.score_breakdown.acceptance_criteria_quality}/100"
    )
    lines.append(f"- Testability: {report.score_breakdown.testability}/100")
    lines.append(f"- Edge case coverage: {report.score_breakdown.edge_case_coverage}/100")
    lines.append(f"- Dependency clarity: {report.score_breakdown.dependency_clarity}/100")
    lines.append(f"- Risk visibility: {report.score_breakdown.risk_visibility}/100")
    lines.append(
        f"- Observability expectations: {report.score_breakdown.observability_expectations}/100"
    )

    lines.append("")
    lines.append("## Rewritten user story")
    lines.append("")
    lines.append(report.rewritten_user_story)

    if report.missing_information:
        lines.append("")
        lines.append("## Missing information")
        lines.append("")
        for item in report.missing_information:
            lines.append(f"- {item}")

    if report.acceptance_criteria:
        lines.append("")
        lines.append("## Acceptance criteria")
        lines.append("")
        for ac in report.acceptance_criteria:
            lines.append(f"- {ac}")

    if report.edge_cases:
        lines.append("")
        lines.append("## Edge cases")
        lines.append("")
        for edge in report.edge_cases:
            lines.append(f"- {edge}")

    def _section(title: str, items: list[str]) -> None:
        if not items:
            return
        lines.append("")
        lines.append(f"## {title}")
        lines.append("")
        for r in items:
            lines.append(f"- {r}")

    _section("Product risks", report.product_risks)
    _section("QA risks", report.qa_risks)
    _section("Technical risks", report.technical_risks)

    if report.suggested_test_scenarios:
        lines.append("")
        lines.append("## Suggested test scenarios")
        lines.append("")
        for s in report.suggested_test_scenarios:
            lines.append(
                f"- **{s.title}** ({s.type.value}, {s.priority.value}): {s.description}"
            )

    _section("Automation candidates", report.automation_candidates)
    _section("Clarification questions", report.clarification_questions)
    _section("Human review notes", report.human_review_notes)

    return "\n".join(lines).rstrip() + "\n"


def _get_demo_response(requirement_text: str) -> str:
    """Generate a realistic demo response without calling the LLM."""
    demo_data = {
        "original_requirement": requirement_text,
        "summary": "This requirement requests the ability to configure QUIC protocol on edge servers but lacks specifics about scope, configuration options, user roles, and success criteria.",
        "rewritten_user_story": "As a platform engineer, I want to enable and configure QUIC protocol settings on edge servers through a configuration interface, so that I can optimize HTTP/3 performance for end users while maintaining control over protocol-specific parameters.",
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
            "Which edge server software/platform (nginx, HAProxy, Cloudflare, custom)?",
            "What QUIC settings should be configurable (connection timeout, max streams, congestion control)?",
            "Who are the target users (DevOps, platform team, customers)?",
            "What is the rollout strategy (per-server, per-region, percentage-based)?",
            "Are there fallback requirements if QUIC negotiation fails?",
            "What are the performance baselines and targets?"
        ],
        "acceptance_criteria": [
            "[ASSUMPTION] User can enable/disable QUIC per edge server",
            "[ASSUMPTION] Configuration changes take effect within 60 seconds",
            "[ASSUMPTION] Invalid configurations are rejected with clear error messages",
            "[NEEDS CLARIFICATION] Define which QUIC parameters are exposed"
        ],
        "edge_cases": [
            "Client does not support QUIC - fallback to HTTP/2 or HTTP/1.1",
            "Configuration applied during high traffic period",
            "Conflicting configurations across server clusters",
            "QUIC disabled but existing connections still active",
            "Certificate rotation while QUIC is enabled"
        ],
        "product_risks": [
            "Scope creep: 'configure' is vague and could expand indefinitely",
            "No defined user persona - unclear who owns this feature",
            "Missing success metrics to validate feature value"
        ],
        "qa_risks": [
            "Cannot write deterministic tests without specific acceptance criteria",
            "Performance testing requires baseline metrics not provided",
            "No clarity on browser/client compatibility matrix"
        ],
        "technical_risks": [
            "QUIC requires UDP - firewall and load balancer changes may be needed",
            "Certificate management complexity with QUIC",
            "Potential impact on existing monitoring/observability stack"
        ],
        "suggested_test_scenarios": [
            {"title": "Enable QUIC on single edge server", "type": "functional", "priority": "high", "description": "Verify QUIC can be enabled and clients negotiate HTTP/3 successfully"},
            {"title": "QUIC fallback to HTTP/2", "type": "functional", "priority": "high", "description": "Verify graceful fallback when client does not support QUIC"},
            {"title": "Configuration validation", "type": "functional", "priority": "medium", "description": "Verify invalid QUIC parameters are rejected with clear errors"},
            {"title": "Load test with QUIC enabled", "type": "non_functional", "priority": "high", "description": "Measure latency and throughput with QUIC vs HTTP/2 baseline"},
            {"title": "QUIC under packet loss", "type": "non_functional", "priority": "medium", "description": "Verify QUIC congestion control under simulated network degradation"}
        ],
        "automation_candidates": [
            "API tests for configuration endpoints",
            "Synthetic monitoring for QUIC negotiation",
            "Automated rollback on error rate threshold"
        ],
        "clarification_questions": [
            "Which edge server platform is this for?",
            "What specific QUIC parameters need to be configurable?",
            "Who is the primary user persona for this configuration?",
            "What is the expected rollout timeline and strategy?",
            "Are there existing QUIC implementations to integrate with or is this greenfield?",
            "What monitoring/alerting is expected when QUIC is enabled?"
        ],
        "human_review_notes": [
            "This requirement is too vague for sprint planning",
            "Recommend a spike to define QUIC configuration scope",
            "Consider splitting into: 1) QUIC enablement, 2) QUIC tuning, 3) QUIC observability"
        ]
    }
    return json.dumps(demo_data, indent=2)


def _render_jira_comment(report: RequirementReadinessReport) -> str:
    """Render report as a Jira-compatible comment (Atlassian wiki markup)."""
    lines: list[str] = []
    
    # Header with color-coded recommendation
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
    
    # Clarification questions (most actionable for Jira)
    if report.clarification_questions:
        lines.append("h4. Clarification Questions")
        for q in report.clarification_questions:
            lines.append(f"* {q}")
        lines.append("")
    
    # Missing information
    if report.missing_information:
        lines.append("h4. Missing Information")
        for item in report.missing_information:
            lines.append(f"* {item}")
        lines.append("")
    
    # Risks summary
    all_risks = report.product_risks + report.qa_risks + report.technical_risks
    if all_risks:
        lines.append("h4. Identified Risks")
        for risk in all_risks[:5]:  # Limit to top 5 for brevity
            lines.append(f"* {risk}")
        if len(all_risks) > 5:
            lines.append(f"_...and {len(all_risks) - 5} more risks_")
        lines.append("")
    
    lines.append("----")
    lines.append("_Generated by AI Requirement Readiness Analyzer_")
    
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Requirement Readiness Analyzer - Analyze product requirements for readiness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a markdown file
  python -m src.main --input requirements.md --output report.md

  # Analyze plain text directly
  python -m src.main --text "As a user, I want to login" --output report.md

  # Read from stdin (for n8n/automation)
  echo "requirement text" | python -m src.main --stdin --format json

  # Output JSON to stdout for piping to other tools
  python -m src.main --input req.md --format json --stdout

  # Generate Jira comment format
  python -m src.main --input req.md --format jira --stdout
"""
    )
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--input",
        help="Path to a file containing the requirement (markdown or plain text)",
    )
    input_group.add_argument(
        "--text",
        help="Requirement text provided directly as a string",
    )
    input_group.add_argument(
        "--stdin",
        action="store_true",
        help="Read requirement text from stdin (useful for pipelines)",
    )
    
    # Output options
    parser.add_argument(
        "--output",
        help="Path to save the output report file (optional if using --stdout)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print output to stdout instead of (or in addition to) file",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json", "jira"],
        default="markdown",
        help="Output format: markdown (default), json (for APIs), jira (Atlassian wiki markup)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress status messages (useful for automation)",
    )
    parser.add_argument(
        "--provider",
        default="openai",
        help="LLM provider (default: openai)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode with sample output (no API key needed)",
    )
    args = parser.parse_args()
    
    # Validate: must have output destination
    if not args.output and not args.stdout:
        parser.error("Must specify --output FILE and/or --stdout")

    # Determine input source
    input_source: str = "stdin" if args.stdin else (args.text[:30] + "..." if args.text and len(args.text) > 30 else args.text or args.input)
    
    if not args.quiet:
        console.print(f"[blue]Input:[/blue] {input_source}")
        if args.output:
            console.print(f"[blue]Output:[/blue] {args.output}")
        console.print(f"[blue]Format:[/blue] {args.format}")
    
    # Read requirement text from the appropriate source
    requirement_text: Optional[str] = None
    
    if args.stdin:
        requirement_text = sys.stdin.read().strip()
        if not requirement_text:
            console.print("[red]Error: no input received from stdin[/red]")
            sys.exit(1)
    elif args.text:
        requirement_text = args.text.strip()
    else:
        input_path = Path(args.input)
        if not input_path.exists():
            console.print(f"[red]Error: input file not found: {input_path}[/red]")
            sys.exit(1)
        try:
            requirement_text = input_path.read_text(encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            console.print(f"[red]Error reading input file: {e}[/red]")
            sys.exit(1)

    if not args.quiet:
        if args.demo:
            console.print("[yellow]Running in DEMO mode (no LLM call)[/yellow]")
        console.print("[blue]Analyzing...[/blue]")
    
    # Demo mode: use sample output
    if args.demo:
        raw_json = _get_demo_response(requirement_text)
    else:
        try:
            prompt = PromptBuilder().build_prompt(requirement_text)
            raw_json = analyze_requirement(prompt, provider=args.provider)
        except MissingAPIKeyError as e:
            console.print(f"[red]{e}[/red]")
            sys.exit(2)
        except LLMClientError as e:
            console.print(f"[red]LLM error: {e}[/red]")
            sys.exit(3)
        except Exception as e:  # noqa: BLE001
            console.print(f"[red]Unexpected error during LLM call: {e}[/red]")
            sys.exit(3)

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        console.print("[red]Model did not return valid JSON.[/red]")
        console.print(f"[red]{e}[/red]")
        sys.exit(4)

    try:
        report = RequirementReadinessReport(**data)
    except Exception as e:  # noqa: BLE001
        console.print("[red]JSON did not match the expected schema.[/red]")
        console.print(f"[red]{e}[/red]")
        sys.exit(4)

    # Generate output in requested format
    if args.format == "json":
        output_content = json.dumps(report.model_dump(), indent=2, ensure_ascii=False)
    elif args.format == "jira":
        output_content = _render_jira_comment(report)
    else:  # markdown
        output_content = _render_markdown(report, input_path=input_source)
    
    # Write to stdout if requested
    if args.stdout:
        print(output_content)
    
    # Write to file if requested
    if args.output:
        try:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output_content + "\n", encoding="utf-8")
            
            # Also save JSON alongside markdown/jira for reference
            if args.format != "json":
                json_path = output_path.with_suffix(".json")
                json_path.write_text(
                    json.dumps(report.model_dump(), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
        except Exception as e:  # noqa: BLE001
            console.print(f"[red]Error writing outputs: {e}[/red]")
            sys.exit(5)
    
    if not args.quiet:
        console.print("\n[green]Analysis complete[/green]")
        console.print(f"Readiness score: {report.readiness_score}/100")
        console.print(
            f"Recommendation: {report.recommendation.value if report.recommendation else ''}"
        )
        if args.output:
            console.print(f"Saved: {args.output}")
            if args.format != "json":
                console.print(f"Saved: {Path(args.output).with_suffix('.json')}")
        if args.stdout and not args.quiet:
            console.print("Output written to stdout")


if __name__ == "__main__":
    main()
