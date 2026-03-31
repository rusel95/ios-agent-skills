# Non-Fatal Error Reporting vs. Crash Reporting: What Matters More

Both are essential, but **non-fatal error reporting has a far greater impact on production app quality** than crash reporting alone. Here is why, and how to structure your investment across both.

## The Numbers Tell the Story

Crashes affect roughly 1-2% of sessions in a typical production iOS app. Non-fatal errors -- failed network requests, decoding failures, auth token expirations, database write errors -- can silently affect 10-30%+ of sessions. If you only have crash reporting, you are blind to the vast majority of production issues your users experience.

## Why Non-Fatal Reporting Matters More

Crashes are dramatic and visible. Non-fatal errors are silent and insidious. Consider what happens in practice:

- A `try?` swallows a Keychain read failure, and users silently get logged out on app launch. No crash. No report. Just a spike in support tickets.
- A `Task {}` block with no `do/catch` drops a network error on the floor. The UI shows a spinner forever. No crash.
- A Combine pipeline hits `.replaceError(with: [])` and the user sees an empty screen with no explanation. No crash.
- An HTTP 401 response is treated as a decoding error because the status code was never checked. The app retries silently until the user gives up. No crash.

These are the errors that drive 1-star reviews and churn, and crash reporting will never catch them.

## You Need Both -- But Prioritize Non-Fatal

The correct approach is a unified observability stack that handles both, with non-fatal reporting as the primary day-to-day tool:

### 1. Implement an ErrorReporter Protocol

Abstract your crash SDK behind a protocol so every error flows through a single reporting path:

```swift
protocol ErrorReporter: Sendable {
    func recordNonFatal(_ error: Error, context: [String: Any])
    func addBreadcrumb(message: String, category: String, level: BreadcrumbLevel, data: [String: Any]?)
    func setUserID(_ userID: String?)
    func setCustomKey(_ key: String, value: Any)
    func log(_ message: String)
}
```

Both Sentry and Firebase Crashlytics support non-fatal error capture through this kind of abstraction. Sentry uses `SentrySDK.capture(error:)`, Crashlytics uses `Crashlytics.crashlytics().record(error:)`.

### 2. Enforce the Catch Block Rule

Every catch block in production code must do two things -- log locally with `os.Logger` (with privacy annotations) and report remotely via your ErrorReporter:

```swift
catch {
    // 1. Local structured log
    Logger.networking.error("Profile fetch failed: \(error.localizedDescription, privacy: .public)")

    // 2. Remote non-fatal report
    ErrorReporter.shared.recordNonFatal(error, context: ["operation": "fetchProfile"])

    // 3. User feedback if appropriate
    // 4. Recovery action if appropriate
}
```

If a catch block only has `print(error)`, it is invisible in production. That error will never appear in any dashboard.

### 3. Eliminate Silent Failure Patterns

Audit for these common patterns that non-fatal reporting is designed to catch:

- **`try?` on operations where failure matters** -- network calls, persistence, auth, payments. Convert to `do/catch` with full observability.
- **`Task {}` without `do/catch`** -- if the Task body can throw, errors vanish entirely. Wrap in `do/catch` inside the Task.
- **Combine `.replaceError(with:)`** at the end of a pipeline -- move error handling inside `flatMap` so errors are captured before being replaced.
- **Unchecked HTTP status codes** -- a 401 or 500 response that successfully decodes as `Data` is not a success.

### 4. Add Breadcrumbs Before Risky Operations

Breadcrumbs are timestamped events that get attached to the next error or crash report. They answer the question crash reports alone never can: "what was the user doing before this broke?"

```swift
ErrorReporter.shared.addBreadcrumb(
    message: "Starting Core Data migration v2 to v3",
    category: "database", level: .info, data: ["storeSize": storeFileSize]
)
```

This context is equally valuable for non-fatal errors and crashes.

### 5. Use MetricKit for What Neither Can See

Some failures produce neither a crash report nor a catchable error. Out-of-memory kills (OOM), watchdog terminations (0x8BADF00D), and background task SIGKILL events are only visible through MetricKit's `MXAppExitMetric`. This is your third layer of observability for issues that escape both crash and non-fatal reporting.

## Crash Reporting Still Matters

None of this means crash reporting is unimportant. You absolutely need it for:

- **Fatal signal handlers** (SIGABRT, SIGSEGV, SIGBUS) that terminate the process
- **Unhandled NSExceptions** from Objective-C code paths
- **dSYM-symbolicated stack traces** that turn hex addresses into readable function names
- **Crash-free session rates** as a top-level app health metric

The key rule: **never run two fatal crash reporters simultaneously**. Sentry and Crashlytics both install signal handlers, and only the last one registered receives the signal. Pick one for fatal crash reporting. If you need both SDKs, disable the crash handler on the secondary and use it only for non-fatal capture and analytics.

## SDK Selection

| Scenario | Recommendation |
|---|---|
| Firebase-heavy project (Auth, Firestore, Push) | Crashlytics for crashes, since it integrates tightly with your existing Firebase stack |
| Standalone app wanting rich error context | Sentry for both crashes and non-fatals (best breadcrumb and context support) |
| Need product analytics alongside error tracking | Sentry for crashes + PostHog for analytics and session replay |

## Summary

Invest in non-fatal error reporting first. It covers the 10-30% of sessions with silent failures that crash reporting cannot see. Then layer crash reporting on top for the 1-2% of fatal events. The combination -- with breadcrumbs, structured logging via `os.Logger`, and MetricKit for OOM/watchdog detection -- gives you full production observability. The goal is zero silent failures: every error is logged, reported, and either surfaced to the user or handled with a recovery action.
