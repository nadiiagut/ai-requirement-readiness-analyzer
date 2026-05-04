# AI Requirement Readiness Analyzer

An AI-powered requirement quality analysis engine for software delivery teams. Supports both **issue-level requirement readiness analysis** and **sprint-level stakeholder dashboard generation**.

Analyze individual user stories to detect gaps and generate acceptance criteria, or analyze entire sprints and produce a stakeholder-facing Confluence page with delivery confidence, progress tracking, and decision items.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-281%20passed-brightgreen.svg)](#testing)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)

---

## The Problem

Poor requirement quality is one of the most expensive problems in software delivery.

| Problem | Business Impact |
|---------|-----------------|
| **Vague requirements** | Developers block on clarifications, rework increases |
| **Missing acceptance criteria** | QA cannot validate, release risk grows |
| **Undiscovered edge cases** | Production bugs, incident costs |
| **No testability analysis** | Automation opportunities missed |
| **Late-stage scope changes** | Sprint failures, deadline slippage |

Studies show that **fixing a defect in production costs 100x more** than catching it during requirements. Teams waste significant time interpreting ambiguous tickets instead of building.

**This tool catches quality issues at the source** — before they propagate into development, testing, and production.

---

## Features

### Issue-Level Analysis

| Capability | Description |
|------------|-------------|
| **Readiness Scoring** | 0-100 score across 7 quality dimensions with weighted breakdown |
| **Gap Analysis** | Identifies missing information, ambiguities, and unclear scope |
| **Acceptance Criteria Generation** | BDD-style Given/When/Then criteria based on requirement intent |
| **Edge Case Detection** | Failure modes, boundary conditions, concurrency issues |
| **Test Scenario Generation** | Positive, negative, and boundary test cases for QA |
| **Automation Candidates** | Identifies scenarios suitable for CI/CD automation |
| **QA Risk Analysis** | Testability concerns, coverage gaps, validation risks |
| **Domain-Aware Analysis** | Optional domain context for specialized industries |

### Sprint-Level Analysis

Stakeholder-facing sprint readiness dashboard with Confluence page generation.

| Capability | Description |
|------------|-------------|
| **Sprint Health Score** | 0-100 label-based score (ready-for-sprint=90, needs-review=70, needs-refinement=45) |
| **Delivery Confidence** | High/Medium/Low confidence rating for sprint completion |
| **Stakeholder Summary** | Theme-aware executive summary for product owners and PMs |
| **Sprint Scope Table** | All issues with risk, reason, and AC notes; issue key rendered as Jira link |
| **Progress Snapshot** | Live status breakdown — To Do / In Progress / Done / Blocked |
| **Decision Needed** | Surfaces only the items where PM or stakeholder action is required |
| **QA / Delivery Focus** | Prioritized areas for QA and delivery team attention |
| **Confluence Dashboard** | Storage-format HTML page ready to push via Confluence REST API |

---

## Use Cases

| Role | Use Case |
|------|----------|
| **Product Managers** | Validate story quality before sprint planning |
| **QA Engineers** | Generate test scenarios and edge cases automatically |
| **Delivery Managers** | Reduce churn from poorly defined requirements |
| **Engineering Managers** | Improve backlog quality metrics |
| **Scrum Masters** | Enhance refinement sessions with structured feedback |
| **Release Managers** | Assess readiness risk before release commits |
| **Agile Coaches** | Sprint-level health dashboards for retrospectives |

### AI-Assisted Backlog Governance

Integrate into your workflow to enforce quality gates:
- Block tickets below readiness threshold from entering sprint
- Auto-generate acceptance criteria for stories missing them
- Flag duplicate or conflicting requirements
- Track requirement quality trends over time

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Requirement Analyzer                   │
├─────────────────────────────────────────────────────────────┤
│  REST API (FastAPI)                                         │
│  ├── /analyze                 Full readiness report         │
│  ├── /analyze/acceptance-criteria   AC + test scenarios     │
│  ├── /analyze/sprint          Sprint-level analysis         │
│  ├── /analyze/duplicates      Duplicate detection           │
│  ├── /analyze/jira-comment    Formatted output              │
│  └── /format/confluence-sprint-page  Sprint dashboard       │
├─────────────────────────────────────────────────────────────┤
│  Core Engine                                                │
│  ├── Pydantic Schemas         Validated input/output        │
│  ├── Prompt Builder           Domain-aware prompt injection │
│  ├── LLM Client               Provider abstraction layer    │
│  └── Formatters               Jira, Confluence, Markdown    │
├─────────────────────────────────────────────────────────────┤
│  LLM Providers                                              │
│  ├── OpenAI (GPT-4o, GPT-4o-mini)                          │
│  ├── Demo Mode (no API key required)                        │
│  └── Extensible for Claude, Groq, Ollama                   │
└─────────────────────────────────────────────────────────────┘
```

**Technology Stack:**
- **FastAPI** — High-performance async REST API
- **Pydantic** — Schema validation and serialization
- **LLM Abstraction** — Swappable providers (OpenAI, demo mode, future: Claude/Groq/Ollama)
- **Domain Contexts** — YAML-based domain knowledge injection

---

## Installation

### Prerequisites
- Python 3.10+
- OpenAI API key (optional — demo mode available)

### Setup

```bash
# Clone repository
git clone https://github.com/your-org/ai-requirement-readiness-analyzer.git
cd ai-requirement-readiness-analyzer

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (optional)
cp .env.example .env
# Edit .env to add OPENAI_API_KEY
```

### Start the API Server

```bash
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

API documentation available at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## API Reference

### POST /analyze

Full requirement readiness analysis with scoring and recommendations.

**Request:**
```json
{
  "issue_key": "PROJ-123",
  "title": "User password reset via email",
  "description": "Users should be able to reset their password by receiving a link via email",
  "issue_type": "Story",
  "priority": "High",
  "labels": ["authentication", "security"],
  "domain_context": "authentication"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `title` | Yes | Requirement title or summary |
| `description` | Yes | Full requirement description (supports Jira ADF format) |
| `issue_key` | No | Ticket identifier for traceability |
| `issue_type` | No | Story, Bug, Task, Epic |
| `priority` | No | Ticket priority |
| `labels` | No | Classification labels |
| `domain_context` | No | Domain hint for specialized analysis |

**Response:**
```json
{
  "issue_key": "PROJ-123",
  "readiness_score": 62,
  "recommendation": "high_risk",
  "summary": "The requirement describes password reset functionality but lacks security specifications...",
  "score_breakdown": {
    "clarity": 70,
    "acceptance_criteria_quality": 45,
    "testability": 60,
    "edge_case_coverage": 50,
    "dependency_clarity": 65,
    "risk_visibility": 70,
    "observability_expectations": 55
  },
  "clarification_questions": [
    "What is the expiration time for reset links?",
    "How many reset attempts are allowed per hour?",
    "Should reset invalidate existing sessions?"
  ],
  "qa_risks": [
    "No rate limiting specified — brute force risk",
    "Email delivery failures not addressed",
    "Token security requirements undefined"
  ]
}
```

### POST /analyze/acceptance-criteria

Generate acceptance criteria, edge cases, test scenarios, and automation candidates.

**Request:**
```json
{
  "issue_key": "PROJ-123",
  "title": "User password reset via email",
  "description": "Users should be able to reset their password by receiving a link via email",
  "domain_context": "authentication"
}
```

**Response:**
```json
{
  "issue_key": "PROJ-123",
  "acceptance_criteria": [
    {
      "id": "AC-1",
      "given": "A registered user with a valid email address",
      "when": "The user requests a password reset",
      "then": "A reset link is sent to their registered email within 30 seconds"
    },
    {
      "id": "AC-2",
      "given": "A user clicks a valid reset link",
      "when": "The user submits a new password meeting complexity requirements",
      "then": "The password is updated and the user is redirected to login"
    }
  ],
  "edge_cases": [
    "Reset link clicked after expiration",
    "User requests multiple reset links in short period",
    "Email address not found in system",
    "Password does not meet complexity requirements",
    "Network timeout during password update"
  ],
  "test_scenarios": [
    {"title": "Verify reset email sent for valid user", "type": "positive"},
    {"title": "Verify error for unregistered email", "type": "negative"},
    {"title": "Verify link expiration after 24 hours", "type": "boundary"},
    {"title": "Verify rate limiting after 5 requests", "type": "negative"},
    {"title": "Verify password complexity validation", "type": "boundary"}
  ],
  "automation_candidates": [
    "Reset email delivery verification",
    "Link expiration enforcement",
    "Rate limiting validation",
    "Password complexity rules",
    "Session invalidation after reset"
  ]
}
```

### POST /analyze/sprint

Analyze all issues in a sprint and return sprint-level health metrics.

Sprint analysis can be triggered by **Jira, GitLab, GitHub Projects, Azure DevOps, or any workflow automation tool** that can make HTTP requests. The endpoint accepts a list of issues and returns aggregated readiness and risk metrics.

**Request:**
```json
{
  "sprint_name": "Sprint 23",
  "sprint_id": 23,
  "domain_context": "control_panel",
  "issues": [
    {
      "issue_key": "NG-101",
      "title": "Add user role management",
      "description": "As an admin, I want to assign roles to users so that I can control access permissions.",
      "status": "To Do",
      "priority": "High",
      "labels": ["ready-for-sprint"]
    },
    {
      "issue_key": "NG-102",
      "title": "Implement audit logging",
      "description": "Log all admin actions for compliance",
      "status": "To Do",
      "priority": "Medium",
      "labels": ["needs-review"]
    },
    {
      "issue_key": "NG-103",
      "title": "Dashboard improvements",
      "description": "",
      "status": "To Do",
      "priority": "Low",
      "labels": ["needs-refinement"]
    }
  ]
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `sprint_name` | Yes | Sprint identifier |
| `sprint_id` | No | Numeric sprint ID |
| `domain_context` | No | Domain hint for specialized analysis |
| `issues` | Yes | Array of issues (min 1) |
| `issues[].issue_key` | Yes | Issue identifier |
| `issues[].title` | Yes | Issue title/summary |
| `issues[].description` | No | Issue description (supports ADF) |
| `issues[].status` | No | Issue status |
| `issues[].priority` | No | Issue priority |
| `issues[].labels` | No | Labels (detects: ready-for-sprint, needs-review, needs-refinement) |

**Response:**
```json
{
  "sprint_name": "Sprint 23",
  "sprint_health_score": 68,
  "delivery_confidence": "Medium",
  "total_issues": 3,
  "high_risk_count": 1,
  "clarification_count": 2,
  "ready_count": 1,
  "needs_review_count": 1,
  "needs_refinement_count": 1,
  "sprint_scope": [
    {
      "issue_key": "NG-101",
      "title": "Add user role management",
      "assignee": "dev@example.com",
      "status": "To Do",
      "risk": "Low",
      "reason": "No QA risk detected",
      "notes": "Ready for QA test planning",
      "issue_url": "https://nadingut.atlassian.net/browse/NG-101"
    },
    {
      "issue_key": "NG-103",
      "title": "Dashboard improvements",
      "assignee": null,
      "status": "To Do",
      "risk": "High",
      "reason": "Missing acceptance criteria",
      "notes": "AC missing — requires refinement",
      "issue_url": null
    }
  ],
  "decisions_needed": [
    {
      "issue_key": "NG-103",
      "issue_url": "https://nadingut.atlassian.net/browse/NG-103",
      "title": "Dashboard improvements",
      "decision_needed": "Approve scope or define acceptance criteria",
      "why_it_matters": "This item cannot be built without clear acceptance criteria."
    }
  ],
  "executive_summary": "This sprint focuses on access control and configuration and admin. Delivery confidence is medium due to unresolved acceptance criteria on 1 story. Health: 68/100.",
  "confluence_page_title": "Sprint 23 Dashboard",
  "confluence_page_body_storage": "<h1>Sprint 23 Dashboard</h1>..."
}
```

**Label Detection:**

The endpoint classifies issues by label and assigns a weighted health score:

| Label | Score | Meaning |
|-------|-------|---------|
| `ready-for-sprint`, `sprint-ready`, `dev-ready` | 90 | Ready for development |
| `needs-review`, `review`, `needs-qa-review` | 70 | Minor review needed |
| `needs-refinement`, `refinement`, `needs-grooming` | 45 | Significant gaps present |
| _(no label)_ | 65 | Unclassified |

Health score = average across all issues, clamped 1–100. Returns 0 only when no issues are present.

### POST /format/confluence-sprint-page

Generate a Confluence storage-format page from an existing `/analyze/sprint` response.

Pass the full `SprintAnalysisResponse` object inside a `sprint_analysis` wrapper. The page title and body are re-rendered from the stored data.

**Response:**
```json
{
  "page_title": "Sprint 23 Dashboard",
  "page_body_storage": "<h1>Sprint 23 Dashboard</h1><h2>Executive Summary</h2>..."
}
```

The `page_body_storage` is stakeholder-facing Confluence storage-format HTML with these sections:

| # | Section | Content |
|---|---------|---------|
| 1 | **H1 title** | `{Sprint Name} Dashboard` |
| 2 | **Executive Summary** | Delivery theme, confidence, and risk note |
| 3 | **Stakeholders** | Role / Name / Responsibility table |
| 4 | **Sprint Metrics** | Health score, confidence, totals, risk counts |
| 5 | **Progress Snapshot** | To Do / In Progress / Done / Blocked counts |
| 6 | **Sprint Scope** | All issues with risk, reason, AC notes; issue keys as Jira links |
| 7 | **QA / Delivery Focus Areas** | Prioritized QA focus list |
| 8 | **Decision Needed** | Items requiring PM/stakeholder action, or "No decisions detected" |

Uses only safe HTML tags: `h1`, `h2`, `p`, `ul`, `li`, `table`, `tr`, `th`, `td`, `strong`, `a`.
No markdown, no escaped `\n`, no leading `=` in title.

### POST /analyze/jira-comment

Generate plain-text comment formatted for Jira.

**Request:**
```json
{
  "issue_key": "PROJ-123",
  "title": "User password reset via email",
  "description": "Users should be able to reset their password..."
}
```

**Response:**
```json
{
  "issue_key": "PROJ-123",
  "jira_comment": "AI Requirement Readiness Analysis — PROJ-123\n\nReadiness Score: 62/100\nRecommendation: Needs Review\n\n..."
}
```

### POST /analyze/confluence-page

Generate Confluence storage format for documentation pages.

### POST /analyze/duplicates

Detect duplicate or conflicting requirements in backlog.

### Query Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `demo_mode` | `false` | Use deterministic demo output (no LLM API call) |
| `provider` | `openai` | LLM provider selection |

---

## CLI Usage

### Available Commands

```bash
# Analyze a requirement from file
python -m src.main --input requirement.json --output report.md

# Analyze from text
python -m src.main --text "As a user, I want to reset my password" --format json

# Pipeline mode (stdin/stdout)
cat requirement.json | python -m src.main --stdin --format json --stdout --quiet

# Demo mode (no API key required)
python -m src.main --text "Add search functionality" --demo --output report.md
```

### CLI Flags

| Flag | Description |
|------|-------------|
| `--input FILE` | Read requirement from file |
| `--text "..."` | Pass requirement as string |
| `--stdin` | Read from stdin |
| `--output FILE` | Write report to file |
| `--stdout` | Print to stdout |
| `--format` | `markdown`, `json`, or `jira` |
| `--quiet` | Suppress status messages |
| `--demo` | Use demo mode (no API) |
| `--provider` | LLM provider |

---

## Integration Examples

### Jira Automation

```yaml
# Jira Automation Rule
trigger: Issue Created
condition: Issue Type = Story

action: Send Web Request
  URL: https://your-server/analyze/jira-comment
  Method: POST
  Body: |
    {
      "issue_key": "{{issue.key}}",
      "title": "{{issue.summary}}",
      "description": "{{issue.description}}"
    }

action: Add Comment
  Body: {{webResponse.body.jira_comment}}
```

### GitHub Actions

```yaml
name: Requirement Quality Check

on:
  pull_request:
    paths:
      - 'docs/requirements/**'

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install analyzer
        run: pip install -r requirements.txt
      
      - name: Analyze requirements
        run: |
          for file in docs/requirements/*.md; do
            python -m src.main --input "$file" --format json --stdout > "${file%.md}.json"
            SCORE=$(jq '.readiness_score' "${file%.md}.json")
            if [ "$SCORE" -lt 70 ]; then
              echo "::warning file=$file::Readiness score $SCORE/100 - needs refinement"
            fi
          done
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### GitLab CI

```yaml
requirement-analysis:
  stage: validate
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - |
      python -m src.main \
        --input $CI_PROJECT_DIR/requirements/feature.md \
        --format json \
        --stdout > analysis.json
    - |
      SCORE=$(jq '.readiness_score' analysis.json)
      if [ "$SCORE" -lt 70 ]; then
        echo "Requirement readiness below threshold: $SCORE/100"
        exit 1
      fi
  artifacts:
    paths:
      - analysis.json
```

### Confluence Integration

```python
import requests

# Analyze requirement
analysis = requests.post(
    "http://localhost:8000/analyze/confluence-page",
    json={"title": "Feature X", "description": "..."}
).json()

# Create Confluence page
requests.post(
    f"{CONFLUENCE_URL}/rest/api/content",
    auth=(USER, TOKEN),
    json={
        "type": "page",
        "title": analysis["page_title"],
        "space": {"key": "PROJ"},
        "body": {
            "storage": {
                "value": analysis["page_body"],
                "representation": "storage"
            }
        }
    }
)
```

### Webhook / Custom Automation

```bash
# Generic webhook integration
curl -X POST "https://your-server/analyze" \
  -H "Content-Type: application/json" \
  -d @requirement.json \
  | jq '.readiness_score, .recommendation'
```

---

## Domain Context

Domain context improves analysis quality by injecting industry-specific knowledge into the LLM prompt.

### Available Domains

| Domain | Focus Areas |
|--------|-------------|
| `fintech` | Compliance, transaction integrity, audit trails, PCI-DSS |
| `control_panel` | Permissions, multi-tenancy, audit logging, RBAC |
| `media_streaming` | DRM, adaptive bitrate, latency, concurrent streams |
| `embedded_device` | Resource constraints, power management, firmware |
| `iot` | Connectivity, telemetry, device provisioning |
| `authentication` | Security, session management, token handling |

### Usage

```json
{
  "title": "Payment retry logic",
  "description": "Implement automatic retry for failed payments",
  "domain_context": "fintech"
}
```

With `fintech` context, the analyzer will:
- Flag missing idempotency requirements
- Check for audit trail specifications
- Identify compliance-related edge cases
- Suggest financial regulation considerations

### Custom Domain Contexts

Add custom domains by creating YAML files in `src/contexts/`:

```yaml
# src/contexts/healthcare.yaml
description: Healthcare and medical software domain
focus_areas:
  - HIPAA compliance
  - Patient data privacy
  - Audit trail requirements
  - Emergency access procedures
risk_categories:
  - Data breach exposure
  - Compliance violations
  - Patient safety
```

---

## Demo

### Sample Input

```json
{
  "issue_key": "SHOP-456",
  "title": "Add product to cart",
  "description": "User can add products to shopping cart"
}
```

### Sample Output

```json
{
  "issue_key": "SHOP-456",
  "readiness_score": 42,
  "recommendation": "not_ready",
  "summary": "The requirement lacks specificity around cart behavior, quantity limits, and inventory validation.",
  "score_breakdown": {
    "clarity": 50,
    "acceptance_criteria_quality": 30,
    "testability": 45,
    "edge_case_coverage": 25,
    "dependency_clarity": 40,
    "risk_visibility": 35,
    "observability_expectations": 30
  },
  "clarification_questions": [
    "What happens when product is out of stock?",
    "Is there a maximum quantity limit per item?",
    "Should cart persist across sessions?",
    "How are pricing changes handled for items in cart?"
  ],
  "qa_risks": [
    "No inventory validation behavior specified",
    "Cart persistence undefined",
    "Price consistency not addressed",
    "Concurrent cart modifications not considered"
  ]
}
```

### Acceptance Criteria Output

```json
{
  "acceptance_criteria": [
    {
      "id": "AC-1",
      "given": "A product is in stock",
      "when": "User clicks Add to Cart",
      "then": "Product appears in cart with quantity 1"
    },
    {
      "id": "AC-2",
      "given": "Product already in cart",
      "when": "User adds same product again",
      "then": "Quantity increments by 1"
    }
  ],
  "edge_cases": [
    "Product goes out of stock after adding to cart",
    "User adds more than available inventory",
    "Price changes while product in cart",
    "Session expires with items in cart",
    "Concurrent cart updates from multiple tabs"
  ],
  "test_scenarios": [
    {"title": "Verify product added successfully", "type": "positive"},
    {"title": "Verify out-of-stock product blocked", "type": "negative"},
    {"title": "Verify quantity at maximum limit", "type": "boundary"}
  ],
  "automation_candidates": [
    "Add to cart API validation",
    "Inventory check integration",
    "Cart persistence across sessions",
    "Price consistency verification"
  ]
}
```

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run specific test file
python -m pytest tests/test_acceptance_criteria.py -v
```

**Test Coverage:**
- Schema validation
- Scoring model
- Recommendation thresholds
- API endpoints (issue-level and sprint-level)
- Domain context loading
- Acceptance criteria generation
- Duplicate detection
- Sprint analysis and health scoring
- Confluence page formatting

---

## Scoring Model

Requirements are scored 0-100 across seven dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Clarity** | 20% | Unambiguous language, clear scope |
| **Acceptance Criteria** | 20% | Testable success conditions defined |
| **Testability** | 20% | Can QA write tests from this? |
| **Edge Case Coverage** | 15% | Error paths and boundaries addressed |
| **Dependency Clarity** | 10% | Blockers and integrations identified |
| **Risk Visibility** | 10% | Risks explicitly surfaced |
| **Observability** | 5% | Logging, metrics, alerting defined |

### Recommendation Thresholds

| Score | Recommendation | Action |
|-------|----------------|--------|
| 80-100 | ✅ **Ready** | Proceed to development |
| 60-79 | 🟡 **Needs Review** | Minor clarifications needed |
| 40-59 | 🟠 **Needs Refinement** | Significant gaps to address |
| 0-39 | 🔴 **Not Ready** | Major rework required |

---

## Roadmap

### Completed
- [x] Sprint-level risk summary and label-based health scoring
- [x] Stakeholder-facing Confluence sprint dashboard
- [x] Sprint Scope table with Jira issue links (auto-generated when no URL provided)
- [x] Progress Snapshot (To Do / In Progress / Done / Blocked)
- [x] Decision Needed section for PM/stakeholder actions
- [x] Stakeholders table with delivery and QA owner rows
- [x] Theme-aware executive summary (infers product area from issue titles)
- [x] Duplicate requirement detection

### Planned
- [ ] Configurable stakeholders per sprint (not hardcoded)
- [ ] Confluence REST API push (auto-create/update page)
- [ ] Release note generation from requirements
- [ ] Traceability matrix generation
- [ ] Anthropic Claude provider
- [ ] Ollama local LLM support
- [ ] Web UI dashboard

---

## Configuration

### Environment Variables

```bash
# .env
OPENAI_API_KEY=sk-proj-your-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.1
```

### LLM Provider Options

| Provider | Model | Speed | Cost |
|----------|-------|-------|------|
| OpenAI | `gpt-4o-mini` | Fast | $0.15/1M tokens |
| OpenAI | `gpt-4o` | Medium | $2.50/1M tokens |
| Demo | — | Instant | Free |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Run tests: `python -m pytest tests/ -v`
4. Submit a pull request

---

## License

MIT License — see [LICENSE](LICENSE) for details.
