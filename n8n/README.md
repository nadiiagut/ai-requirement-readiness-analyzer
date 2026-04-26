# n8n Integration

This directory contains sample payloads and workflow exports for n8n integration.

## Files

| File | Description |
|------|-------------|
| `webhook-demo-workflow.json` | Webhook-based workflow for testing without Jira/Confluence |
| `jira-confluence-demo-workflow.json` | Full Atlassian integration workflow skeleton |
| `sample-jira-payload-ev-charging.json` | EV charging requirement example |
| `sample-jira-payload-quic.json` | QUIC configuration requirement example |
| `sample-jira-payload-login.json` | Suspicious login notification example |

---

## Workflow 1: Webhook Demo (No Atlassian Required)

Use `webhook-demo-workflow.json` for quick demos without Jira/Confluence accounts.

## Importing the Demo Workflow

### Prerequisites

1. **n8n running** (cloud or self-hosted)
2. **Analyzer API running** on port 8000

### Import Steps

1. Open n8n
2. Go to **Workflows** → **Add Workflow** → **Import from File**
3. Select `webhook-demo-workflow.json`
4. Click **Import**

### Manual Adjustments Required

After importing, you may need to adjust:

#### 1. API URL (if not using Docker)

The workflow uses `host.docker.internal:8000` which works when n8n runs in Docker and the API runs on the host machine.

**If n8n runs directly on host:**
```
Change: http://host.docker.internal:8000
To:     http://localhost:8000
```

**If API runs on a different machine:**
```
Change: http://host.docker.internal:8000
To:     http://<your-api-host>:8000
```

Update these URLs in nodes:
- `Analyze Full Report`
- `Get Jira Comment`
- `Get Confluence Page`

#### 2. Demo Mode Toggle

By default, `demo_mode=true` is set. To use real LLM analysis:

1. Set `OPENAI_API_KEY` in your API environment
2. Change `demo_mode` query parameter from `true` to `false` in all HTTP Request nodes

#### 3. Webhook URL

After activating the workflow, n8n will provide a webhook URL like:
```
https://your-n8n-instance/webhook/analyze-requirement
```

Or for test mode:
```
https://your-n8n-instance/webhook-test/analyze-requirement
```

## Testing the Workflow

### Using curl

```bash
# Get webhook URL from n8n after activating workflow
WEBHOOK_URL="http://localhost:5678/webhook-test/analyze-requirement"

# Test with sample payload
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d @sample-jira-payload-ev-charging.json
```

### Expected Response

```json
{
  "issue_key": "EV-142",
  "readiness_score": 34,
  "recommendation": "not_ready",
  "summary": "This requirement lacks specifics...",
  "jira_comment": "h3. AI Requirement Readiness Analysis...",
  "confluence_page_title": "EV-142: Requirement Readiness Report",
  "confluence_page_body": "## Executive Summary\n\n..."
}
```

## Workflow Architecture

```
┌─────────────────┐
│ Webhook Trigger │ POST /webhook/analyze-requirement
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Normalize Payload│ Extracts: issue_key, title, description, etc.
└────────┬────────┘
         │
    ┌────┴────┬────────────┐
    │         │            │
    ▼         ▼            ▼
┌───────┐ ┌────────┐ ┌──────────┐
│/analyze│ │/jira-  │ │/confluence│
│       │ │comment │ │-page     │
└───┬───┘ └───┬────┘ └────┬─────┘
    │         │            │
    └────┬────┴────────────┘
         │
         ▼
┌─────────────────┐
│  Merge Results  │ Combines all API responses
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Respond Webhook │ Returns combined JSON
└─────────────────┘
```

## Extending the Workflow

### Add Jira Integration

Insert after "Merge Results":

1. **Jira Software Node** → Add Comment
   - Issue Key: `{{ $json.issue_key }}`
   - Comment: `{{ $json.jira_comment }}`

### Add Confluence Integration

Insert after "Merge Results":

1. **Confluence Node** → Create Page
   - Title: `{{ $json.confluence_page_title }}`
   - Content: `{{ $json.confluence_page_body }}`

### Add Slack Notification

Insert after "Merge Results":

1. **Slack Node** → Send Message
   - Message: `Requirement {{ $json.issue_key }} analyzed: {{ $json.readiness_score }}/100 ({{ $json.recommendation }})`

## Troubleshooting

### "Connection refused" Error

- Ensure API is running: `uvicorn src.api:app --host 0.0.0.0 --port 8000`
- Check URL matches your setup (Docker vs direct host)

### "Invalid JSON" Error

- Ensure payload includes required fields: `title`, `description`
- Check sample payloads for correct format

### Empty Response

- Verify workflow is activated (not just saved)
- Use "Execute Workflow" in n8n to test with manual input

---

## Workflow 2: Jira & Confluence Integration

Use `jira-confluence-demo-workflow.json` for full Atlassian integration with real Jira and Confluence accounts.

### Prerequisites

1. **Atlassian account** (free trial at [atlassian.com/try](https://www.atlassian.com/try))
2. **Jira project** created (recommended key: `QA`)
3. **Confluence space** created (recommended key: `QA`)
4. **Jira issue** created for testing
5. **API token** from [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

### Import Steps

1. Open n8n
2. Go to **Workflows** → **Add Workflow** → **Import from File**
3. Select `jira-confluence-demo-workflow.json`
4. Click **Import**

### ⚠️ Required Changes After Import

This workflow uses placeholder values that **must be updated** before running:

#### 1. Jira Credential

The workflow references `Jira Trial Credential` which does not exist.

1. Go to **Settings** → **Credentials** → **Add Credential**
2. Search for **Jira Software Cloud**
3. Configure:
   - **Email:** Your Atlassian email
   - **API Token:** Your API token
   - **Domain:** `your-site.atlassian.net`
4. Save as `Jira Trial Credential` (or update node references)

#### 2. Confluence Credential

The workflow references `Confluence Trial Credential` which does not exist.

1. Go to **Settings** → **Credentials** → **Add Credential**
2. Search for **Confluence**
3. Configure:
   - **Email:** Your Atlassian email
   - **API Token:** Same API token
   - **Domain:** `your-site.atlassian.net`
4. Save as `Confluence Trial Credential` (or update node references)

#### 3. Issue Key (Jira Get Issue node)

Update the placeholder issue key:

```
Change: QA-123
To:     Your actual issue key (e.g., QA-1)
```

#### 4. Space Key (Confluence Create Page node)

Update the placeholder space key:

```
Change: QA
To:     Your actual Confluence space key
```

#### 5. API URL (if not using Docker)

Same as Webhook workflow - update `host.docker.internal:8000` if needed.

#### 6. Demo Mode

Set `demo_mode=false` in HTTP Request nodes for real LLM analysis.

### Workflow Architecture

```
┌─────────────────┐
│  Manual Trigger │ Click "Execute Workflow" to start
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Jira Get Issue │ Fetches issue QA-123 from Jira
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Extract Fields   │ Extracts: issue_key, title, description, etc.
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Analyze Requirement│ POST /analyze
└────────┬────────┘
         │
    ┌────┴────────────┐
    │                 │
    ▼                 ▼
┌──────────┐    ┌───────────────┐
│Get Jira  │    │Get Confluence │
│Comment   │    │Page           │
└────┬─────┘    └───────┬───────┘
     │                  │
     ▼                  ▼
┌──────────┐    ┌───────────────┐
│Jira Add  │    │Confluence     │
│Comment   │    │Create Page    │
└──────────┘    └───────────────┘
```

### Running the Workflow

1. Ensure API is running: `uvicorn src.api:app --host 0.0.0.0 --port 8000`
2. Click **Execute Workflow** in n8n
3. Watch execution progress through nodes
4. Verify:
   - Comment added to Jira issue
   - Page created in Confluence space

### Expected Results

**In Jira:**
- New comment on issue with AI readiness analysis
- Formatted with wiki markup (colored panels, bullets)

**In Confluence:**
- New page titled `{issue_key}: Requirement Readiness Report`
- Full markdown report with all sections

### Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `Credentials not found` | Placeholder credentials | Create credentials with exact names or update node references |
| `Issue not found` | Wrong issue key | Update `QA-123` to your actual issue |
| `Space not found` | Wrong space key | Update `QA` to your actual space key |
| `401 Unauthorized` | Bad API token | Regenerate token in Atlassian |
| `403 Forbidden` | Permission issue | Check project/space permissions for your user |
