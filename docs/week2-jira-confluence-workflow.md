# Week 2: Jira & Confluence Workflow Integration

This guide covers two demo modes for the AI Requirement Readiness Analyzer:

| Mode | Use Case | Requirements |
|------|----------|--------------|
| **Mode A** | Quick demo without accounts | FastAPI + n8n + curl |
| **Mode B** | Full Atlassian integration | Jira + Confluence trial + n8n |

---

## Mode A: No-Jira Demo

Run the complete workflow locally without Jira or Confluence accounts. Perfect for:
- Portfolio demonstrations
- Technical interviews
- Local development testing

### Prerequisites

- Python 3.11+
- n8n (Docker or npm)
- curl or Postman

### Step 1: Start the API Server

```bash
cd ai-requirement-readiness-analyzer

# Install dependencies (if not done)
pip install -r requirements.txt

# Start FastAPI server
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Started reloader process
```

> 📸 **Screenshot opportunity:** Terminal showing server startup

### Step 2: Start n8n

**Option A: Docker (recommended)**
```bash
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

**Option B: npm**
```bash
npx n8n
```

Open http://localhost:5678 in your browser.

> 📸 **Screenshot opportunity:** n8n welcome screen

### Step 3: Import the Demo Workflow

1. In n8n, click **Add Workflow** → **Import from File**
2. Select `n8n/webhook-demo-workflow.json`
3. Click **Import**

You should see a workflow with 7 nodes:

```
Webhook Trigger → Normalize Payload → [3 API calls] → Merge Results → Respond
```

> 📸 **Screenshot opportunity:** Imported workflow canvas

### Step 4: Activate the Workflow

1. Toggle the **Active** switch in the top-right corner
2. Note the webhook URL displayed (e.g., `http://localhost:5678/webhook/analyze-requirement`)

> 📸 **Screenshot opportunity:** Active workflow with webhook URL visible

### Step 5: Send a Test Request

**Using curl:**
```bash
curl -X POST "http://localhost:5678/webhook/analyze-requirement" \
  -H "Content-Type: application/json" \
  -d '{
    "issue_key": "EV-142",
    "title": "Delayed AC charging",
    "description": "User should be able to delay AC charging by 4 hours. Charging should usually resume after power interruption, but sometimes user may need to reconnect the cable.",
    "issue_type": "Story",
    "priority": "High",
    "labels": ["ev-charging", "mobile-app"]
  }'
```

**Using Postman:**
1. Create new POST request
2. URL: `http://localhost:5678/webhook/analyze-requirement`
3. Body → raw → JSON
4. Paste the payload above
5. Click **Send**

> 📸 **Screenshot opportunity:** Postman with request and response

### Step 6: Review the Response

**Expected response structure:**
```json
{
  "issue_key": "EV-142",
  "readiness_score": 34,
  "recommendation": "not_ready",
  "summary": "This requirement lacks specifics about scope...",
  "jira_comment": "h3. AI Requirement Readiness Analysis - EV-142\n\n*Readiness Score:* 34/100...",
  "confluence_page_title": "EV-142: Requirement Readiness Report",
  "confluence_page_body": "## Executive Summary\n\nThis requirement lacks specifics..."
}
```

**Key fields to highlight:**
- `readiness_score`: 34/100 indicates low readiness
- `recommendation`: "not_ready" suggests refinement needed
- `jira_comment`: Ready to paste into Jira
- `confluence_page_body`: Full markdown report

> 📸 **Screenshot opportunity:** JSON response with key fields highlighted

### Step 7: View Formatted Outputs

**Jira Comment Preview:**

The `jira_comment` field contains Atlassian wiki markup:

```
h3. AI Requirement Readiness Analysis - EV-142

*Readiness Score:* 34/100
*Recommendation:* {color:red}Not Ready{color}

h4. Main Concerns
* (!) Scope creep due to vague requirements
* (!) No defined user persona
* (!) Missing success metrics

h4. Clarification Questions
* (?) What is the exact delay duration range?
* (?) What triggers "power interruption"?
* (?) When does "reconnect the cable" apply?

h4. QA Next Step
* (x) Not ready - return to product owner

----
_AI Note: Recommend splitting into smaller stories_
```

**Confluence Page Preview:**

The `confluence_page_body` contains markdown suitable for Confluence:

```markdown
## Executive Summary

This requirement lacks specifics about scope, configuration options...

## Readiness Score

**Score:** 34/100
**Recommendation:** Not Ready

## Score Breakdown

| Dimension | Score |
|-----------|-------|
| Clarity | 40/100 |
| Acceptance Criteria Quality | 30/100 |
...
```

> 📸 **Screenshot opportunity:** Side-by-side Jira comment markup and rendered preview

---

## Mode B: Real Jira/Confluence Trial Demo

Full integration with Atlassian products. Demonstrates production-ready workflow.

### Prerequisites

- Atlassian account (free trial available)
- n8n with Jira and Confluence credentials configured
- API server running

### Step 1: Create Atlassian Trial Account

1. Go to [atlassian.com/try](https://www.atlassian.com/try)
2. Click **Try it free** under Jira Software
3. Create account or sign in with Google
4. Choose **Jira Software** and **Confluence** (both included in trial)
5. Name your site (e.g., `your-name-demo`)

**Trial includes:**
- 7-day free trial
- Full Jira Software features
- Full Confluence features
- No credit card required

> 📸 **Screenshot opportunity:** Atlassian trial signup page

### Step 2: Create Jira Project

1. In Jira, click **Projects** → **Create project**
2. Select **Scrum** or **Kanban** template
3. Configure:
   - **Name:** QA Requirements
   - **Key:** QA
4. Click **Create**

> 📸 **Screenshot opportunity:** New Jira project dashboard

### Step 3: Create Confluence Space

1. In Confluence, click **Spaces** → **Create space**
2. Select **Blank space**
3. Configure:
   - **Space name:** QA Documentation
   - **Space key:** QA
4. Click **Create**

> 📸 **Screenshot opportunity:** New Confluence space home

### Step 4: Create Sample Jira Issue

1. In Jira project QA, click **Create**
2. Fill in:
   - **Issue type:** Story
   - **Summary:** Delayed AC charging
   - **Description:**
     ```
     User should be able to delay AC charging by 4 hours.
     Charging should usually resume after power interruption,
     but sometimes user may need to reconnect the cable.
     ```
   - **Priority:** High
   - **Labels:** ev-charging, mobile-app
3. Click **Create**
4. Note the issue key (e.g., `QA-1`)

> 📸 **Screenshot opportunity:** Created Jira issue detail view

### Step 5: Generate Atlassian API Token

1. Go to [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token**
3. Label: `n8n-integration`
4. Click **Create**
5. **Copy the token immediately** (you won't see it again)

> 📸 **Screenshot opportunity:** API token creation (token blurred)

### Step 6: Configure n8n Jira Credential

1. In n8n, go to **Settings** → **Credentials**
2. Click **Add Credential** → Search **Jira Software**
3. Configure:
   - **Email:** Your Atlassian email
   - **API Token:** Paste token from Step 5
   - **Domain:** `your-site.atlassian.net`
4. Click **Save**
5. Test connection with **Test** button

> 📸 **Screenshot opportunity:** n8n Jira credential configuration

### Step 7: Configure n8n Confluence Credential

1. In n8n, click **Add Credential** → Search **Confluence**
2. Configure:
   - **Email:** Your Atlassian email
   - **API Token:** Same token from Step 5
   - **Domain:** `your-site.atlassian.net`
3. Click **Save**

> 📸 **Screenshot opportunity:** n8n Confluence credential configuration

### Step 8: Create Production Workflow

Create a new workflow with these nodes:

**Node 1: Manual Trigger**
- Type: Manual Trigger
- Purpose: Start workflow on demand

**Node 2: Jira Get Issue**
- Type: Jira Software
- Operation: Get Issue
- Issue Key: `QA-1` (or use expression for dynamic)

**Node 3: Set Payload**
- Type: Set
- Assignments:
  ```
  issue_key = {{ $json.key }}
  title = {{ $json.fields.summary }}
  description = {{ $json.fields.description }}
  issue_type = {{ $json.fields.issuetype.name }}
  priority = {{ $json.fields.priority.name }}
  ```

**Node 4: Analyze Requirement**
- Type: HTTP Request
- Method: POST
- URL: `http://localhost:8000/analyze?demo_mode=false`
- Body: JSON with payload fields

**Node 5: Get Jira Comment**
- Type: HTTP Request
- Method: POST
- URL: `http://localhost:8000/analyze/jira-comment?demo_mode=false`
- Body: Same payload

**Node 6: Get Confluence Page**
- Type: HTTP Request
- Method: POST
- URL: `http://localhost:8000/analyze/confluence-page?demo_mode=false`
- Body: Same payload

**Node 7: Add Jira Comment**
- Type: Jira Software
- Operation: Add Comment
- Issue Key: `{{ $('Jira Get Issue').item.json.key }}`
- Comment: `{{ $('Get Jira Comment').item.json.comment }}`

**Node 8: Create Confluence Page**
- Type: Confluence
- Operation: Create Page
- Space Key: `QA`
- Title: `{{ $('Get Confluence Page').item.json.page_title }}`
- Content: `{{ $('Get Confluence Page').item.json.page_body }}`

> 📸 **Screenshot opportunity:** Complete workflow canvas with all nodes

### Step 9: Run the Workflow

1. Click **Execute Workflow**
2. Watch execution progress through each node
3. Verify success indicators (green checkmarks)

> 📸 **Screenshot opportunity:** Workflow execution success view

### Step 10: Verify Results in Jira

1. Open issue `QA-1` in Jira
2. Scroll to **Comments** section
3. Verify AI readiness comment is posted

**Expected Jira comment appearance:**

The comment should render with:
- Colored panel header
- Formatted score and recommendation
- Bulleted lists for concerns and questions
- Horizontal rule and footer

> 📸 **Screenshot opportunity:** Jira issue with AI comment rendered

### Step 11: Verify Results in Confluence

1. Go to Confluence space **QA**
2. Find page titled **QA-1: Requirement Readiness Report**
3. Verify full report is displayed

**Expected Confluence page sections:**
- Executive Summary
- Readiness Score with breakdown table
- Rewritten User Story
- Missing Information
- Acceptance Criteria
- Risks table
- Suggested Test Scenarios table
- Clarification Questions
- Human Review Notes

> 📸 **Screenshot opportunity:** Confluence page with full report

---

## Troubleshooting

### API Connection Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | API not running | Start with `uvicorn src.api:app --host 0.0.0.0 --port 8000` |
| `host.docker.internal not found` | n8n not in Docker | Use `localhost:8000` instead |
| `502 Bad Gateway` | LLM API error | Check `OPENAI_API_KEY` or use `demo_mode=true` |

### n8n Workflow Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `Workflow not active` | Forgot to activate | Toggle Active switch |
| `Webhook URL 404` | Wrong path | Check webhook path matches workflow |
| `Empty response` | Merge node issue | Verify all 3 API calls complete before merge |

### Jira/Confluence Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `401 Unauthorized` | Bad credentials | Regenerate API token |
| `404 Not Found` | Wrong domain | Use `site.atlassian.net` format |
| `403 Forbidden` | Permission issue | Check project/space permissions |
| `Comment not rendering` | Markup issue | Verify wiki markup syntax |

### Common Fixes

**Reset n8n workflow:**
```bash
# Stop n8n
docker stop n8n

# Clear data (optional)
rm -rf ~/.n8n/database.sqlite

# Restart
docker start n8n
```

**Verify API health:**
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","version":"1.0.0"}
```

**Test API directly:**
```bash
curl -X POST "http://localhost:8000/analyze?demo_mode=true" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","description":"Test description"}'
```

---

## 2-Minute Video Script

Use this script for a portfolio demo video or technical presentation.

### Opening (0:00 - 0:15)

> "Hi, I'm [Name]. Today I'll show you the AI Requirement Readiness Analyzer - a tool that uses LLMs to evaluate product requirements and integrates with Jira and Confluence for automated feedback."

*[Show: Project README or landing page]*

### Problem Statement (0:15 - 0:30)

> "Atlassian's 2025 State of Teams report found that teams waste 25% of their time searching for answers. Vague requirements are a major cause. This tool catches ambiguity before it causes problems."

*[Show: Atlassian stat or vague requirement example]*

### Architecture Overview (0:30 - 0:45)

> "The system has three parts: a FastAPI backend that calls OpenAI, formatter modules for Jira and Confluence output, and n8n for workflow automation."

*[Show: Architecture diagram or code structure]*

### Demo - Mode A (0:45 - 1:15)

> "Let me show you a quick demo. I'll send a vague EV charging requirement to the API."

*[Show: curl command or Postman request]*

> "The response includes a readiness score of 34 out of 100, specific concerns like 'vague quantifiers', and clarification questions the product owner should answer."

*[Show: JSON response with key fields highlighted]*

> "The Jira comment is formatted with wiki markup, ready to post. The Confluence page has the full breakdown with tables and sections."

*[Show: Formatted outputs]*

### Demo - Mode B (1:15 - 1:45)

> "For the full integration, I've connected n8n to Jira and Confluence. When I run this workflow, it fetches the issue, analyzes it, posts a comment, and creates a documentation page - all automatically."

*[Show: n8n workflow execution]*

> "Here's the result in Jira - the AI comment with colored status and action items."

*[Show: Jira issue with comment]*

> "And in Confluence - the full readiness report with risks, test scenarios, and recommendations."

*[Show: Confluence page]*

### Closing (1:45 - 2:00)

> "This tool helps QA engineers and product managers catch requirement issues early, saving development time and reducing rework. The code is on GitHub - link in the description. Thanks for watching!"

*[Show: GitHub repo or contact info]*

---

## Quick Reference

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/analyze` | POST | Full structured report |
| `/analyze/jira-comment` | POST | Jira wiki markup comment |
| `/analyze/confluence-page` | POST | Confluence page content |

### Sample Payloads

Located in `n8n/` directory:
- `sample-jira-payload-ev-charging.json`
- `sample-jira-payload-quic.json`
- `sample-jira-payload-login.json`

### Output Examples

Located in `docs/` directory:
- `jira-comment-example.md`
- `confluence-page-example.md`

---

## Next Steps

After completing this demo:

1. **Week 3:** Add real-time Jira trigger (on issue create)
2. **Week 4:** Deploy to cloud (Railway/Render + n8n Cloud)
3. **Week 5:** Add custom prompt templates per project type
