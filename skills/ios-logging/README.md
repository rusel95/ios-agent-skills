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

## Benchmark Results

Tested on **27 scenarios** with **91 discriminating assertions**.

### Results Summary

| Model | With Skill | Without Skill | Delta | A/B Quality |
|-------|-----------|--------------|-------|-------------|
| **Sonnet 4.6** | 84/91 (92.3%) | 83/91 (91.2%) | **+1.1%** | **23W 3T 1L** (avg 9.0 vs 8.5) |
| **GPT-5.4** | 91/91 (100%) | 43/91 (47.2%) | **+52.8%** | **23W 0T 4L** (avg 8.8 vs 8.2) |
| **Gemini 3.1 Pro** | 82/82 (100%) | 68/82 (82.9%) | **+17.1%** | **24W** 0T 0L (avg 9.2 vs 6.3) |

> **Note on Gemini 3.1 Pro:** 24 of 27 evals had real responses; 3 evals were missing (centralized-error-handler-swiftui, categorized-error-routing, operational-pii-leaks) so totals are out of 82 assertions. With the skill, Gemini answered every assertion correctly (82/82). Without the skill, gaps concentrate in URLSession status validation (4/7, 57%), BGTask logging (5/7, 71%), and missing upstream Combine error handling. Privacy/crash-SDK/MetricKit topics scored 100% in both variants — strong baseline knowledge in those areas.

### Results (Sonnet 4.6)

| Config | Pass | Total | Rate |
|--------|------|-------|------|
| **With Skill** | 84 | 91 | 92.3% |
| **Without Skill** | 83 | 91 | 91.2% |
| **Delta** | | | **+1.1%** |

### Blind A/B Quality Scoring (Sonnet 4.6)

**23W 3T 1L** — avg 9.0↑8.5 (with-skill ↑ without-skill)

27 evals scored blind by a judge who doesn't know which response used the skill. Position randomized per eval.

**Interpretation:** Sonnet 4.6 already has strong logging knowledge — the baseline passes 91.2% of assertions. The skill's discriminating value concentrates in niche details (MetricKit opt-in coverage, dSYM symbolication, `.private(mask: .hash)` vs `.sensitive` distinction, `.notice` vs `.info` persistence). The A/B quality scoring shows the skill consistently produces more thorough responses (23 wins, 1 loss) — advantage is in depth and operational completeness, not missing core knowledge.

### Grader Comparison: Opus vs Sonnet

A sample re-grade of discriminating evals with Sonnet 4.6 as grader found **full agreement** on the failures, with one exception: Sonnet was **stricter** on the `.sensitive` vs `.private(mask: .hash)` distinction (Opus passed it as "equivalent concept", Sonnet correctly failed it as the wrong API). This confirmed two skill bugs that have since been fixed.

> 27 topic-based evals, 91 discriminating assertions, tested on Claude Sonnet 4.6. See `evals/ios-logging/evals.json` for prompts and assertions.

## Compatibility

- iOS 15+ / Swift 5.5+ (modern concurrency)
- Works with SwiftUI and UIKit
- Supports Sentry, Firebase Crashlytics, PostHog, and any custom crash SDK
- Compatible with all architectures (MVVM, VIPER, TCA, etc.)
