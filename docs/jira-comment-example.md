# Jira Comment Example

This example shows the output from `POST /analyze/jira-comment` for the EV charging requirement.

## Input

```json
{
  "issue_key": "EV-142",
  "title": "Delayed AC charging",
  "description": "User should be able to delay AC charging by 4 hours. Charging should usually resume after power interruption, but sometimes user may need to reconnect the cable."
}
```

## Output (Jira Wiki Markup)

```
h3. AI Requirement Readiness Analysis - EV-142

*Readiness Score:* 34/100
*Recommendation:* {color:red}Not Ready{color}

h4. Main Concerns
* (!) Scope creep due to vague requirements - "sometimes" and "usually" are ambiguous
* (!) No defined user persona - is this for EV owners, fleet managers, or both?
* (!) Missing success metrics - how do we measure if delay feature works correctly?

h4. Clarification Questions
* (?) What is the exact delay duration range (fixed 4 hours or configurable)?
* (?) What triggers "power interruption" - grid outage, user disconnect, or vehicle sleep?
* (?) When does "reconnect the cable" apply vs automatic resume?
* (?) Should delayed charging integrate with time-of-use electricity rates?
* (?) What happens if the delay period exceeds the departure time?

h4. QA Next Step
* (x) Not ready - return to product owner for clarification

----
_AI Note: This requirement contains ambiguous terms ("usually", "sometimes") that will cause inconsistent implementation. Recommend splitting into: 1) Scheduled charging delay, 2) Power interruption recovery, 3) Manual reconnection handling._
```

## Ambiguity Types Demonstrated

| Ambiguity | Example |
|-----------|---------|
| **Vague quantifiers** | "sometimes", "usually" |
| **Missing edge cases** | What if delay exceeds departure time? |
| **Undefined triggers** | What counts as "power interruption"? |
| **Missing user persona** | Who configures the delay? |
| **Missing acceptance criteria** | No success metrics defined |

## Usage in n8n

1. Trigger: Jira Issue Created
2. HTTP Request: POST to `/analyze/jira-comment?demo_mode=false`
3. Extract: `$.comment` from response
4. Jira: Add Comment to issue using extracted comment
