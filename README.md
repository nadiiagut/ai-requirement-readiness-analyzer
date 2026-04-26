# AI Requirement Readiness Analyzer

> **Stop wasting time on unclear requirements.** Analyze any product requirement in seconds and get actionable feedback before it hits development.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-11%20passed-brightgreen.svg)](#tests)

A CLI tool that uses LLMs to analyze product requirements and generate structured readiness reports. Get instant feedback on ambiguity, missing acceptance criteria, edge cases, risks, and test scenarios.

**Human-in-the-loop by design** — this tool accelerates review, it doesn't replace human judgment.

### This project demonstrates:
- AI-assisted product requirement analysis
- QA risk detection before implementation
- Structured test planning
- Human-in-the-loop AI governance
- Automation-ready output for Jira/n8n/CI workflows

---

## The Problem

**[Atlassian's 2025 State of Teams](https://www.atlassian.com/state-of-teams-2025) found that teams and leaders waste 25% of their time just searching for answers.**

In product delivery, vague requirements are a major source of this waste:

| Issue | Impact |
|-------|--------|
| Unclear requirements | Developers ask questions, wait for answers, rework |
| Missing acceptance criteria | QA can't write tests, release risk increases |
| Undiscovered edge cases | Bugs in production, incident response |
| Hidden dependencies | Blocked sprints, missed deadlines |

**This tool catches these issues early** — before they become expensive problems in development or production.

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/your-username/ai-requirement-readiness-analyzer.git
cd ai-requirement-readiness-analyzer
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Add your API key
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# 3. Analyze a requirement
python -m src.main --text "Add ability to configure QUIC on edge server" --output outputs/report.md
```

---

## Real Example

### Input
A vague one-liner requirement:

```
Add ability to configure QUIC on edge server
```

### Command
```bash
python -m src.main --text "Add ability to configure QUIC on edge server" --output outputs/quic.md
```

### Output

**Readiness Score: 45/100 — NEEDS REFINEMENT**

The tool identified critical gaps:

| Section | Finding |
|---------|---------|
| **Missing Information** | Which edge server platform? What QUIC parameters? Who are the users? |
| **Acceptance Criteria** | None provided — tool generated assumptions marked `[ASSUMPTION]` |
| **Edge Cases** | Fallback when client doesn't support QUIC, concurrent config changes |
| **Risks** | Scope creep, UDP firewall changes, certificate complexity |
| **Test Scenarios** | 5 suggested tests with priority levels |
| **Clarification Questions** | 6 questions to ask before development |

<details>
<summary>📄 View full generated report</summary>

```markdown
# Requirement Readiness Report

**Input:** Add ability to configure QUIC on edge server

## Summary
The requirement is to implement a configuration capability for QUIC on an edge 
server, enabling improved performance and reduced latency for users. This feature 
is aimed at network administrators who manage edge server settings.

## Readiness
- **Readiness score:** 45/100
- **Recommendation:** needs_refinement

### Score breakdown
- Clarity: 50/100
- Acceptance criteria quality: 30/100
- Testability: 40/100
- Edge case coverage: 30/100
- Dependency clarity: 20/100
- Risk visibility: 50/100
- Observability expectations: 20/100

## Rewritten user story
As a network administrator, I want the ability to configure QUIC on the edge 
server, so that protocol behavior can be configured and evaluated against defined performance goals.

## Missing information
- Specific configuration options for QUIC
- Expected performance metrics or benchmarks
- User roles and permissions for configuration access
- Integration points with existing systems or services

## Acceptance criteria
- The system must allow configuration of QUIC settings via a user interface.
- The configuration changes must be saved and persist across server restarts.
- The system must validate QUIC configuration inputs and provide error messages.
- Performance must improve by at least 20% in latency metrics after QUIC config.

## Edge cases
- Configuration fails due to invalid input format.
- Server does not support QUIC due to outdated software.
- Network interruptions during configuration changes.
- Concurrent configuration attempts by multiple administrators.

## Product risks
- Potential performance degradation if QUIC is misconfigured.
- Incompatibility with existing protocols or services.
- User confusion due to lack of documentation or training.

## QA risks
- Insufficient test coverage for edge cases.
- Difficulty in replicating network conditions for testing QUIC performance.
- Lack of clear rollback procedures if configuration fails.

## Technical risks
- Dependency on third-party libraries for QUIC support.
- Potential security vulnerabilities introduced by new configuration options.
- Backward compatibility issues with existing edge server configurations.

## Suggested test scenarios
- **Validate QUIC configuration input** (functional, high)
- **Check persistence of QUIC settings** (functional, high)
- **Measure performance improvement with QUIC** (non_functional, medium)
- **Simulate concurrent configuration changes** (negative, medium)

## Clarification questions
- What specific QUIC configuration options need to be exposed to the user?
- What are the expected performance metrics for QUIC?
- Who will have permissions to configure QUIC on the edge server?
- Are there existing systems that need to integrate with this capability?

## Human review notes
- The requirement lacks detail on specific configuration options.
- Acceptance criteria need to be more measurable and specific.
- There is a significant risk of misconfiguration impacting performance.
```
</details>

---

## Who Is This For?

### Roles

| Role | Use Case |
|------|----------|
| **Product Managers** | Validate requirements before sprint planning |
| **QA Engineers/Managers** | Get test scenarios and edge cases automatically |
| **Engineering Leads** | Identify technical risks and missing dependencies |
| **Scrum Masters** | Improve refinement sessions with structured feedback |
| **Technical Writers** | Ensure acceptance criteria are clear and testable |
| **DevOps/SRE** | Check for observability and operational requirements |

### Integration Tools

| Tool | Integration |
|------|-------------|
| **n8n** | Execute Command node with `--stdin --format json --stdout` |
| **Jira** | Auto-comment on ticket creation with `--format jira` |
| **GitHub Actions** | PR checks for requirement docs |
| **Slack/Teams** | Webhook with JSON output |
| **Confluence** | Paste markdown reports directly |
| **Make (Integromat)** | HTTP module with JSON output |
| **Zapier** | Code step with CLI execution |

---

## LLM Setup

### Option 1: OpenAI (Recommended)

1. Get an API key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create `.env` file:

```bash
cp .env.example .env
```

3. Add your key:

```bash
# .env
OPENAI_API_KEY=sk-proj-your-key-here
OPENAI_MODEL=gpt-4o-mini          # Fast and cheap
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.1
```

**Model options:**
| Model | Speed | Cost | Quality |
|-------|-------|------|---------|
| `gpt-4o-mini` | Fast | $0.15/1M tokens | Good |
| `gpt-4o` | Medium | $2.50/1M tokens | Better |
| `gpt-4-turbo` | Medium | $10/1M tokens | Best |

### Option 2: Demo Mode (No API needed)

Test the tool without any API key:

```bash
python -m src.main --text "Your requirement here" --output report.md --demo
```

### Option 3: Other Providers (Roadmap)

Coming soon:
- Anthropic Claude
- Groq (free tier)
- Ollama (local)

---

## Usage

### Basic Commands

```bash
# From a file
python -m src.main --input requirements.md --output report.md

# From text directly
python -m src.main --text "As a user, I want to reset my password" --output report.md

# From stdin (for automation)
echo "requirement text" | python -m src.main --stdin --format json --stdout --quiet
```

### Output Formats

| Format | Flag | Use Case |
|--------|------|----------|
| Markdown | `--format markdown` | Confluence, docs, PRs |
| JSON | `--format json` | APIs, automation, n8n |
| Jira | `--format jira` | Jira comments (wiki markup) |

### All CLI Flags

| Flag | Description |
|------|-------------|
| `--input FILE` | Read requirement from file |
| `--text "..."` | Pass requirement as string |
| `--stdin` | Read from stdin (pipelines) |
| `--output FILE` | Save report to file |
| `--stdout` | Print to stdout |
| `--format` | `markdown`, `json`, or `jira` |
| `--quiet` | Suppress status messages |
| `--demo` | Use sample output (no API) |
| `--provider` | LLM provider (default: `openai`) |

---

## REST API

The analyzer is also available as a FastAPI service for integration with n8n, Jira, and other automation tools.

### Start the API Server

```bash
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/analyze` | Full structured report |
| POST | `/analyze/jira-comment` | Jira-formatted comment |
| POST | `/analyze/confluence-page` | Confluence page content |

### Request Payload (all POST endpoints)

All analysis endpoints accept Jira-like payload:

```json
{
  "issue_key": "QA-123",
  "title": "Delayed AC charging",
  "description": "User should be able to delay AC charging by 4 hours",
  "issue_type": "Story",
  "priority": "High",
  "labels": ["ev-charging", "backend"]
}
```

Only `title` and `description` are required. Other fields are optional.

### POST /analyze

Returns full structured report for programmatic processing.

```bash
curl -X POST "http://localhost:8000/analyze?demo_mode=true" \
  -H "Content-Type: application/json" \
  -d '{"issue_key": "QA-123", "title": "Delayed AC charging", "description": "User should be able to delay AC charging by 4 hours"}'
```

### POST /analyze/jira-comment

Returns Atlassian wiki markup ready to post as a Jira comment.

```bash
curl -X POST "http://localhost:8000/analyze/jira-comment?demo_mode=true" \
  -H "Content-Type: application/json" \
  -d '{"issue_key": "QA-123", "title": "Delayed AC charging", "description": "..."}'
```

**Response:**
```json
{
  "issue_key": "QA-123",
  "readiness_score": 34,
  "recommendation": "not_ready",
  "comment": "{panel:title=AI Requirement Readiness Analysis|borderColor=#red}..."
}
```

### POST /analyze/confluence-page

Returns page title and XHTML body for Confluence REST API.

```bash
curl -X POST "http://localhost:8000/analyze/confluence-page?demo_mode=true" \
  -H "Content-Type: application/json" \
  -d '{"issue_key": "QA-123", "title": "Delayed AC charging", "description": "..."}'
```

**Response:**
```json
{
  "issue_key": "QA-123",
  "page_title": "QA-123: Requirement Readiness Report",
  "page_body": "<ac:structured-macro ac:name=\"panel\">..."
}
```

### Query Parameters (all endpoints)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `demo_mode` | `false` | Use sample output (no LLM call) |
| `provider` | `openai` | LLM provider |

### Interactive API Docs

FastAPI auto-generates interactive docs:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Automation Examples

### n8n Workflow (API)

```
[Jira Trigger: Issue Created]
  → [HTTP Request: POST to /analyze with issue_key, title, description]
  → [Jira: Add Comment with readiness score and recommendations]
  → [Confluence: Create page with full report]
```

### n8n Workflow (CLI)

```
[Jira Trigger: Issue Created]
  → [HTTP: Get issue description]
  → [Execute Command: python -m src.main --stdin --format jira --stdout --quiet]
  → [Jira: Add Comment with output]
```

### GitHub Action

```yaml
- name: Check requirement readiness
  run: |
    python -m src.main \
      --input docs/requirements/feature.md \
      --format json \
      --stdout > readiness.json
    
    SCORE=$(jq '.readiness_score' readiness.json)
    if [ "$SCORE" -lt 70 ]; then
      echo "::warning::Requirement readiness score is $SCORE/100"
    fi
```

### Shell Script

```bash
#!/bin/bash
# Analyze all .md files in a directory
for file in requirements/*.md; do
  python -m src.main --input "$file" --output "reports/$(basename $file)"
done
```

---

## Scoring Model

Scores are 0–100 per dimension, combined using these weights:

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| Clarity | 20% | Is the requirement unambiguous? |
| Acceptance Criteria | 20% | Are success conditions defined? |
| Testability | 20% | Can QA write tests from this? |
| Edge Case Coverage | 15% | Are exceptions handled? |
| Dependency Clarity | 10% | Are blockers identified? |
| Risk Visibility | 10% | Are risks surfaced? |
| Observability | 5% | Are logging/metrics defined? |

### Recommendation Thresholds

| Score | Recommendation |
|-------|---------------|
| 85-100 | ✅ `ready` — Good to develop |
| 70-84 | 🟡 `needs_refinement` — Minor gaps |
| 50-69 | 🟠 `high_risk` — Significant issues |
| 0-49 | 🔴 `not_ready` — Major rework needed |

---

## Tests

```bash
python -m pytest tests/ -v
```

Tests cover:
- Schema validation
- Recommendation thresholds
- Prompt builder
- Report generation

---

## Architecture

```
src/
├── main.py           # CLI entry point
├── llm_client.py     # LLM provider abstraction
├── prompt_builder.py # Prompt template injection
├── schemas.py        # Pydantic models + validation
└── report_writer.py  # Markdown/Jira rendering

prompts/
└── requirement_analysis_prompt.md  # The analysis prompt

outputs/              # Generated reports
examples/             # Sample requirements
tests/                # Unit tests
```

---

## Responsible AI

This tool is designed as **AI-assisted review**, not automated approval:

- The model is instructed to **not invent facts**
- Assumptions are marked explicitly as `[ASSUMPTION]`
- Output includes **clarification questions** for humans to answer
- **Human review notes** guide next steps

**Recommended workflow:**
1. Run analyzer on draft requirement
2. Review clarification questions with stakeholders
3. Update requirement
4. Re-run to track improvement

---

## Roadmap

- [ ] Anthropic Claude provider
- [ ] Groq provider (free tier)
- [ ] Ollama support (local LLMs)
- [ ] Diff mode (compare requirement revisions)
- [ ] Web UI wrapper
- [ ] VS Code extension
- [ ] Webhook endpoint for direct HTTP integration

---

## Contributing

Contributions welcome! Please:

1. Fork the repo
2. Create a feature branch
3. Run tests: `python -m pytest tests/ -v`
4. Submit a PR

---

## License

MIT License — see [LICENSE](LICENSE) for details.
