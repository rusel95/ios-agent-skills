# Querying Sentry Production Errors from Your AI Coding Assistant

You can query Sentry production errors directly from your AI coding assistant by connecting it through a **Sentry MCP (Model Context Protocol) server**. This eliminates context-switching to the Sentry web dashboard and keeps your debugging workflow inside the editor.

## Setup: Add the Sentry MCP Server

For **Claude Code**, add the Sentry MCP server to your configuration:

```bash
claude mcp add sentry
```

Alternatively, configure it manually in your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "sentry": {
      "command": "npx",
      "args": ["-y", "@sentry/mcp-server"],
      "env": {
        "SENTRY_AUTH_TOKEN": "<your-sentry-auth-token>"
      }
    }
  }
}
```

You will need a Sentry auth token with read access to your project. Generate one at **Settings > Auth Tokens** in the Sentry dashboard.

For other AI-powered IDEs (Cursor, Windsurf, etc.), the MCP server configuration follows the same pattern -- add the Sentry MCP server entry to whatever MCP configuration file that tool supports.

## What You Can Do Once Connected

With the Sentry MCP server connected, you can ask your AI assistant natural-language questions during debugging, such as:

- **"What are the most recent crashes in my iOS app?"** -- queries recent issues sorted by last seen
- **"Show me the stack trace for issue PROJ-1234"** -- retrieves full symbolicated stack traces (assuming dSYMs are uploaded)
- **"What errors happened today related to networking?"** -- searches events by keyword and time range
- **"Get the breadcrumbs for the latest crash"** -- pulls the breadcrumb trail showing what the user did before the crash occurred
- **"How many users are affected by this URLSession timeout error?"** -- retrieves impact metrics for a specific issue

This is especially powerful when combined with breadcrumbs in your error reporting. If your app records breadcrumbs before risky operations (database migrations, payments, auth flows), those breadcrumbs appear in the Sentry event data that the MCP server returns, giving your assistant full context about what led to the error.

## Verify the Integration Works

After setup, confirm connectivity by asking your assistant a simple question:

```
"Check recent crashes in Sentry"
```

or

```
"What errors happened today in Sentry for project <your-project-name>?"
```

If it returns issue data, the integration is working.

## Ensure Your App Reports Errors Properly

The MCP server can only surface errors that your app actually reports. Make sure your iOS app follows these practices to get the most value:

1. **Every catch block reports to Sentry** -- do not just `print(error)`. Use an `ErrorReporter` abstraction that calls `SentrySDK.capture(error:)` for non-fatal errors.

```swift
catch {
    Logger.networking.error("Request failed: \(error.localizedDescription, privacy: .public)")
    ErrorReporter.shared.recordNonFatal(error, context: ["operation": "fetchUserProfile"])
}
```

2. **Add breadcrumbs before risky operations** -- these show up in the Sentry event and give your AI assistant context about what the user was doing:

```swift
ErrorReporter.shared.addBreadcrumb(
    message: "Starting Core Data migration v2 to v3",
    category: "database",
    level: .info,
    data: ["storeSize": storeFileSize]
)
```

3. **Upload dSYM files** -- without them, the stack traces the MCP server returns will contain hex addresses instead of function names, making them useless for debugging. Set Build Settings > Debug Information Format to "DWARF with dSYM File" and add the Sentry dSYM upload script to your build phases.

4. **Do not silence errors with `try?`** on operations where failure matters (network, persistence, auth). Silent failures never reach Sentry and therefore cannot be queried.

## Why This Matters

Remote logging through Sentry combined with MCP connectivity transforms debugging from a multi-tool, multi-tab investigation into a single-context workflow. Instead of switching between Xcode, the Sentry dashboard, and your code editor, you ask your AI assistant to pull the exact error, stack trace, and breadcrumb trail -- then immediately apply fixes in the same session. A 3-day debugging mystery becomes a 15-minute investigation.
