# iOS Production Error Observability

**Logging is the single most undervalued investment in iOS development.** When a bug appears in production — affecting thousands of users across different devices, OS versions, and network conditions — you can't attach a debugger. You can't set breakpoints. The only thing standing between you and days of guesswork is the quality of your observability stack.

Great remote logging turns a 3-day debugging mystery into a 15-minute investigation. Bad logging (or no logging) means you're recreating bugs from vague user reports and screenshots.

## Why This Skill Exists

AI coding assistants generate code that compiles and runs — but is **observability-blind**:

- `print(error)` in every catch block (invisible in production)
- `try?` everywhere (destroys all diagnostic information)
- `Task {}` with no error handling (errors silently vanish)
- No crash SDK integration, no breadcrumbs, no privacy annotations
- Zero consideration for MetricKit, remote logging, or PII compliance

This skill enforces production-grade error handling patterns that make every error visible, categorized, and actionable.

## The Observability Stack

A production iOS app needs **layered observability** — no single tool catches everything:

| Layer | Tool | What It Catches |
|-------|------|-----------------|
| **Structured Logging** | `os.Logger` with privacy annotations | All application events, filterable by category/level |
| **Crash Reporting** | Sentry / Firebase Crashlytics | Fatal crashes with symbolicated stacks + breadcrumbs |
| **Non-Fatal Tracking** | Sentry / Crashlytics / PostHog | Silent errors that don't crash but break features |
| **OS Diagnostics** | MetricKit | OOM kills, watchdog terminations, hangs (out-of-process) |
| **Product Analytics** | PostHog / Google Analytics / Mixpanel | User behavior context around errors |

## Remote Logging: The Game Changer

Local `os.Logger` is powerful but limited to devices you can physically stream from. **Remote logging through crash reporting SDKs is what transforms debugging from guesswork into science:**

- **Sentry** — richest error context, automatic breadcrumbs (HTTP, lifecycle, touch), structured tags/extras, session replay, performance tracing. Best for teams that want deep observability. Has MCP server and CLI tools for querying issues programmatically.
- **Firebase Crashlytics** — tight Google ecosystem integration, simple setup, free tier. Limitation: only 8 non-fatals per session. Best for Firebase-heavy projects.
- **PostHog** — product analytics + session replay + feature flags. No native iOS error tracking yet (use as analytics complement, not primary crash reporter). Has MCP server for querying analytics data.
- **Google Analytics / Firebase Analytics** — event-based analytics, user journey tracking. Use alongside a crash reporter for behavioral context.
- **Other** — Datadog, Bugsnag, Instabug, Embrace — each with different strengths. The skill's `ErrorReporter` protocol abstracts the choice.

**The skill recommends**: pick one primary crash reporter (Sentry or Crashlytics), optionally add a product analytics tool (PostHog or GA), and wrap everything behind the `ErrorReporter` protocol so you can swap vendors without touching application code.

## Connecting to Remote Services

Modern development workflows benefit from connecting to these analytics platforms via **MCP servers** or **CLI tools**, allowing your AI coding assistant to:

- Query recent crashes and non-fatal errors directly
- Search error patterns and group similar issues
- Pull breadcrumb trails for specific incidents
- Check error rates and impact metrics

Available integrations:
- **Sentry MCP** — query issues, search events, get error details
- **PostHog MCP** — query analytics, check feature flags, search events
- **Firebase CLI** (`firebase crashlytics:*`) — list recent crashes, download reports
- **Vercel Observability** — if using Vercel backend, drains + monitoring dashboards

Setting up these connections means your AI assistant can investigate production issues with real data instead of guessing.

## Three Non-Negotiable Rules

1. **No `print()` in production code** — use `os.Logger` with privacy annotations
2. **No catch block without observability** — every caught error must be logged AND reported to your remote service
3. **No `try?` on operations where failure matters** — if the user or system needs to know it failed, use `do/catch` with remote reporting

## What the Skill Covers

| Topic | Reference |
|-------|-----------|
| Silent failure patterns (`try?`, `Task {}`, Combine, `.task {}`) | `references/silent-failures.md` |
| `os.Logger` setup, log levels, privacy annotations | `references/logger-setup.md` |
| Crash SDK integration (Sentry, Crashlytics, PostHog) | `references/crash-sdk-integration.md` |
| MetricKit for OOM/watchdog/hang detection | `references/metrickit.md` |
| Objective-C exception edge cases | `references/objc-exceptions.md` |
| PII compliance, GDPR/CCPA, privacy manifests | `references/pii-compliance.md` |
| Centralized error handling, retry patterns, extensions | `references/enterprise-patterns.md` |

## Benchmark Results (Sonnet 4.6)

| Config | Pass | Total | Rate |
|--------|------|-------|------|
| **With Skill** | 89 | 91 | 97.8% |
| **Without Skill** | 58 | 91 | 63.7% |
| **Delta** | | | **+34.1%** |

### Blind A/B Quality Scoring

**25W 0T 2L** — avg 8.6↑7.4 (with-skill ↑ without-skill)

27 evals scored blind by a judge who doesn't know which response used the skill. Position randomized per eval.

### Strongest Discriminating Topics

| Topic | With Skill | Without Skill | Delta |
|-------|-----------|--------------|-------|
| centralized-error-handling | 100% | 0% | +100% |
| combine-pipeline-death | 100% | 33% | +67% |
| pii-compliance | 100% | 38% | +63% |
| crash-sdk-selection | 83% | 33% | +50% |
| metrickit | 100% | 50% | +50% |
| retry-with-backoff | 100% | 50% | +50% |
| task-error-swallowing | 100% | 50% | +50% |
| urlsession-status-codes | 100% | 50% | +50% |

### Non-Discriminating Topics (baseline already strong)

| Topic | With Skill | Without Skill | Delta |
|-------|-----------|--------------|-------|
| background-tasks | 100% | 100% | 0% |
| cancellation-error | 100% | 100% | 0% |
| error-reporter-protocol | 100% | 100% | 0% |
| notification-silent-failures | 100% | 100% | 0% |
| objc-bridge-edge-case | 100% | 100% | 0% |
| operational-pii-leaks | 100% | 100% | 0% |
| print-replacement | 100% | 100% | 0% |

> 27 topic-based evals, 91 discriminating assertions, tested on Claude Sonnet 4.6. See `evals/ios-logging/evals.json` for prompts and assertions, `evals/ios-logging/ios-logging-workspace/iteration-2/benchmark.md` for full results.

## Compatibility

- iOS 15+ / Swift 5.5+ (modern concurrency)
- Works with SwiftUI and UIKit
- Supports Sentry, Firebase Crashlytics, PostHog, and any custom crash SDK
- Compatible with all architectures (MVVM, VIPER, TCA, etc.)
