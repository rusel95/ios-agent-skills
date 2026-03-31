# Querying Sentry Production Errors from an AI Coding Assistant

## Overview

To query Sentry production errors directly from your AI coding assistant during debugging, you would typically use the Sentry API or an MCP (Model Context Protocol) server that connects your assistant to Sentry. Here are the main approaches:

## Approach 1: Using the Sentry API Directly

Sentry provides a REST API that you can use to fetch issues, events, and error details. You can ask your AI assistant to make API calls on your behalf.

### Setup

1. Generate an **Auth Token** in Sentry under **Settings > Auth Tokens** (or use an internal integration token).
2. Note your **organization slug** and **project slug** from your Sentry dashboard.

### Common API Endpoints

- **List project issues:** `GET /api/0/projects/{org_slug}/{project_slug}/issues/`
- **Get issue details:** `GET /api/0/issues/{issue_id}/`
- **Get latest event for an issue:** `GET /api/0/issues/{issue_id}/events/latest/`
- **Search events:** `GET /api/0/projects/{org_slug}/{project_slug}/events/?query=<search_term>`

### Example: Fetching Recent Crashes

```bash
curl -H "Authorization: Bearer YOUR_SENTRY_AUTH_TOKEN" \
  "https://sentry.io/api/0/projects/your-org/your-ios-project/issues/?query=is:unresolved&sort=date"
```

This returns a JSON array of unresolved issues sorted by most recent.

## Approach 2: Using an MCP Server for Sentry

If your AI coding assistant supports MCP (Model Context Protocol), you can set up an MCP server that wraps the Sentry API, giving your assistant direct access to query errors conversationally.

### General Steps

1. **Find or build a Sentry MCP server.** Community MCP servers for Sentry may exist, or you can build one using the MCP SDK that wraps Sentry's REST API.
2. **Configure the MCP server** with your Sentry auth token, organization, and project details.
3. **Register the MCP server** with your AI assistant's configuration (e.g., in Claude Desktop's `claude_desktop_config.json` or a similar config file).
4. Once connected, you can ask your assistant questions like:
   - "What are the top unresolved crashes in production?"
   - "Show me the stack trace for issue PROJ-1234."
   - "How many users are affected by the latest crash?"

### Example MCP Server Configuration

```json
{
  "mcpServers": {
    "sentry": {
      "command": "npx",
      "args": ["@sentry/mcp-server"],
      "env": {
        "SENTRY_AUTH_TOKEN": "your-token-here",
        "SENTRY_ORG": "your-org-slug",
        "SENTRY_PROJECT": "your-ios-project"
      }
    }
  }
}
```

> Note: The exact package name and configuration may vary. Check the MCP server registry or Sentry's documentation for the latest available integration.

## Approach 3: Custom Scripts in Your Workflow

You can write a simple script that your AI assistant can invoke to fetch Sentry data:

```python
import requests

SENTRY_TOKEN = "your-token"
ORG_SLUG = "your-org"
PROJECT_SLUG = "your-ios-project"

def get_recent_issues(limit=10):
    url = f"https://sentry.io/api/0/projects/{ORG_SLUG}/{PROJECT_SLUG}/issues/"
    headers = {"Authorization": f"Bearer {SENTRY_TOKEN}"}
    params = {"query": "is:unresolved", "sort": "date", "limit": limit}
    response = requests.get(url, headers=headers, params=params)
    return response.json()

def get_issue_details(issue_id):
    url = f"https://sentry.io/api/0/issues/{issue_id}/"
    headers = {"Authorization": f"Bearer {SENTRY_TOKEN}"}
    response = requests.get(url, headers=headers)
    return response.json()
```

## Practical Debugging Tips

- **Filter by platform:** Add `?query=platform:cocoa` to filter for iOS-specific issues in Sentry API calls.
- **Search by error message:** Use `?query=message:*EXC_BAD_ACCESS*` to find specific crash types.
- **Correlate with your code:** Once you get a stack trace from Sentry, you can ask your AI assistant to navigate to the relevant file and line number in your codebase.
- **Check release-specific issues:** Filter with `?query=release:1.2.0` to see issues tied to a specific app version.

## Limitations

- API rate limits apply; Sentry typically allows 20 requests per second for auth tokens.
- Symbolication of iOS crash reports happens on Sentry's side, so stack traces returned via API should already be symbolicated if you have uploaded your dSYM files.
- Your AI assistant cannot access Sentry unless you explicitly provide credentials and configure the connection.
