# Sentry vs. Crashlytics for iOS Crash Reporting

The right choice depends on your project's ecosystem and observability needs. Here is a concrete comparison.

## Decision Framework

```
What ecosystem is your project in?
├── Firebase-heavy (Auth, Firestore, Push) --> Crashlytics (free, tight integration)
├── Standalone / wants rich observability  --> Sentry (best error context, breadcrumbs, performance)
├── Needs product analytics + errors       --> Sentry (crashes) + PostHog (analytics, session replay)
└── Enterprise / custom backend            --> Sentry or Datadog
```

## Trade-offs at a Glance

| Dimension | Sentry | Crashlytics |
|-----------|--------|-------------|
| **Cost** | Free tier available; paid plans for volume | Completely free (part of Firebase) |
| **Error context** | Rich structured extras, tags, breadcrumbs with typed levels and metadata | Breadcrumbs are plain strings only -- no structured data support |
| **Non-fatal limit** | No per-session cap | Stores only the **8 most recent non-fatal exceptions per session** -- older ones are silently dropped |
| **Performance monitoring** | Built-in (transactions, spans, profiling) | Requires separate Firebase Performance SDK |
| **AI-assisted debugging** | MCP server available -- query issues, search events, get stack traces and breadcrumbs directly from your editor | CLI tools only (`firebase crashlytics:*`) -- less integrated into AI workflows |
| **Firebase integration** | Independent; requires separate setup | Native -- shares GoogleService-Info.plist, automatic with Firebase init |
| **Self-hosting** | Sentry can be self-hosted (on-premise option) | Cloud-only, Google-operated |
| **SPM / CocoaPods** | Both supported | Both supported |

## Non-Fatal Reporting: A Critical Difference

Crashes affect roughly 1-2% of sessions. Non-fatal errors can affect 10-30%+ of sessions silently. Non-fatal error reporting is the primary tool for detecting silent failures in production.

Crashlytics caps non-fatals at **8 per session**. If your app reports more than 8 non-fatal errors in a single session (common in apps with network-heavy flows, retries, or background sync), the oldest reports are lost. Sentry has no such per-session cap. For apps where comprehensive non-fatal visibility matters, this is a significant advantage for Sentry.

## Breadcrumb Quality

Sentry breadcrumbs carry structured data -- typed levels (`debug`, `info`, `warning`, `error`, `fatal`), categories, and arbitrary key-value metadata:

```swift
ErrorReporter.shared.addBreadcrumb(
    message: "Starting Core Data migration v2->v3",
    category: "database", level: .info,
    data: ["storeSize": storeFileSize]
)
```

Crashlytics breadcrumbs are plain log strings with no structured metadata:

```swift
Crashlytics.crashlytics().log("[database] Starting Core Data migration v2->v3")
```

This matters when debugging complex crash sequences -- structured breadcrumbs are filterable and searchable; plain strings require manual parsing.

## Architecture Recommendation: Abstract the SDK

Regardless of which SDK you choose, never call Sentry or Crashlytics APIs directly throughout your codebase. Use a protocol-based abstraction:

```swift
protocol ErrorReporter: Sendable {
    func recordNonFatal(_ error: Error, context: [String: Any])
    func addBreadcrumb(message: String, category: String, level: BreadcrumbLevel, data: [String: Any]?)
    func setUserID(_ userID: String?)
    func setCustomKey(_ key: String, value: Any)
    func log(_ message: String)
}
```

Then implement `SentryErrorReporter` or `CrashlyticsErrorReporter` behind this protocol. This gives you:

- **Vendor swapping** -- switch SDKs without touching call sites
- **Testability** -- inject a mock reporter in unit tests
- **Consistent metadata** -- enforce context dictionaries at the protocol level

## Critical Rule: Never Run Both as Fatal Crash Reporters

Running Sentry and Crashlytics simultaneously for fatal crashes causes **signal handler conflicts**. Both install handlers for SIGABRT, SIGSEGV, SIGBUS, etc., and only the last one registered receives the signal. `NSSetUncaughtExceptionHandler` supports only one handler -- the second call replaces the first.

If you need both SDKs (e.g., Crashlytics for the Firebase console and Sentry for developer workflows):

1. Pick **one** for fatal crash reporting
2. Disable the crash handler on the secondary -- e.g., `options.enableCrashHandler = false` for Sentry
3. Use the secondary only for non-fatal capture, breadcrumbs, and analytics

## dSYMs Are Non-Negotiable for Either SDK

Without dSYM files, crash reports show hex addresses instead of function names.

- Build Settings: Debug Information Format = **"DWARF with dSYM File"** for all configurations
- Apply to **all targets** (main app, extensions, widgets, watch app)
- Add the dSYM upload build phase script (both Sentry and Crashlytics provide these)

## App Extensions Require Separate Initialization

Widgets, notification service extensions, share extensions, and other extensions run in their own sandboxed processes. The crash SDK must be initialized separately in each extension's entry point. For Crashlytics, each extension also needs its own `GoogleService-Info.plist`.

## Summary Recommendation

- **Choose Crashlytics** if you are already deep in the Firebase ecosystem (Auth, Firestore, Push Notifications) and want zero-cost crash reporting with minimal setup overhead.
- **Choose Sentry** if you want richer error context, unlimited non-fatals per session, structured breadcrumbs, built-in performance monitoring, MCP server integration for AI-assisted debugging, or the option to self-host.
- **For most new projects** that are not Firebase-dependent, Sentry provides better observability out of the box.
