# Background Sync Task: Silent Failure Analysis

## The Problem

Your `handleSync` code has a critical silent failure pattern. The `Task {}` body contains `try await performSync()`, but there is no `do/catch` block inside the Task. When `performSync()` throws, the error is silently discarded -- no log, no crash, no report. The user's data stays stale, and you have zero visibility into why.

There is a second problem: if `performSync()` throws, `task.setTaskCompleted(success: true)` is never called either. BGTaskScheduler interprets this as the task hanging, and the system may throttle or deprioritize future scheduling of your background task. This makes the problem progressively worse over time.

## Why This Happens

`Task.init` is `@discardableResult`. The compiler never warns when errors from the returned `Task<Void, Error>` are ignored. Any thrown error inside the closure is silently swallowed -- no crash, no log, nothing reaches the caller.

This is the single most common silent failure pattern in modern Swift code.

## The Fix

```swift
import os
import BackgroundTasks

extension Logger {
    static let sync = Logger(subsystem: Bundle.main.bundleIdentifier ?? "com.app", category: "sync")
}

func handleSync(task: BGProcessingTask) {
    let syncTask = Task {
        do {
            try await performSync()
            Logger.sync.notice("Background sync completed successfully")
            task.setTaskCompleted(success: true)
        } catch is CancellationError {
            // Task was cancelled by the system (e.g., user launched app, or time expired)
            // This is normal BGTask lifecycle, not a failure
            Logger.sync.info("Background sync cancelled by system")
            task.setTaskCompleted(success: false)
        } catch {
            Logger.sync.error("Background sync failed: \(error.localizedDescription, privacy: .public)")
            ErrorReporter.shared.recordNonFatal(error, context: [
                "operation": "backgroundSync",
                "taskIdentifier": task.identifier
            ])
            task.setTaskCompleted(success: false)
        }
    }

    // Handle system expiration -- BGTaskScheduler can revoke your time
    task.expirationHandler = {
        Logger.sync.warning("Background sync expired by system before completion")
        ErrorReporter.shared.addBreadcrumb(
            message: "BGTask expired",
            category: "sync",
            level: .warning,
            data: ["taskIdentifier": task.identifier]
        )
        syncTask.cancel()
    }
}
```

## What Changed and Why

### 1. `do/catch` inside the Task

Every `Task {}` containing `try` must have an explicit `do/catch` with observability inside it. Without this, thrown errors vanish completely.

### 2. `CancellationError` handled separately

When the system revokes your background execution time (via the expiration handler), the Task is cancelled and throws `CancellationError`. This is normal BGTask lifecycle behavior, not a real failure. Reporting it as an error creates noise in your crash dashboard. Always distinguish cancellation from real errors.

### 3. `task.setTaskCompleted(success:)` called on every path

In the original code, if `performSync()` throws, `setTaskCompleted` is never called. The system treats this as a hung task and may reduce your app's background execution budget. The fixed version calls it on all three paths: success, cancellation, and failure.

### 4. `os.Logger` instead of no logging

`os.Logger` with privacy annotations integrates with the unified logging system. Logs are persisted based on level (`.error` is always persisted, `.notice` is persisted to disk, `.info` is memory-only). `print()` would be invisible on production devices with no debugger attached.

### 5. `ErrorReporter.shared.recordNonFatal` for remote visibility

Local logs alone are not enough -- you cannot access `os.Logger` output from user devices remotely. `recordNonFatal` sends the error to your crash reporting backend (Sentry, Crashlytics, etc.) so you can see failure rates, error types, and trends across your user base. This is what transforms a 3-day debugging mystery into a 15-minute investigation.

### 6. Expiration handler with breadcrumb

`BGProcessingTask` can be terminated by the system at any time. The expiration handler cancels the in-flight work and leaves a breadcrumb so that if a subsequent error occurs, you can see that the previous sync was interrupted.

## ErrorReporter Setup

If you do not already have an `ErrorReporter` protocol in your project, here is the minimal abstraction:

```swift
protocol ErrorReporter: Sendable {
    func recordNonFatal(_ error: Error, context: [String: Any])
    func addBreadcrumb(message: String, category: String, level: BreadcrumbLevel, data: [String: Any]?)
}

enum BreadcrumbLevel: String, Sendable {
    case debug, info, warning, error, fatal
}
```

Implement this protocol with your crash SDK of choice:
- **Firebase-heavy project** -- use Crashlytics (free, tight Firebase integration)
- **Standalone / wants rich error context** -- use Sentry (best breadcrumbs, error grouping, performance monitoring)
- **Need product analytics alongside errors** -- use Sentry for crashes + PostHog for analytics

Never call SDK APIs directly throughout your codebase. The protocol abstraction enables testability and vendor swapping.

## Diagnosing the "Stale Data" Reports

Once you deploy this fix, check your crash reporting dashboard for:

1. **Error frequency** -- how often does `performSync` actually fail?
2. **Error types** -- are failures network timeouts, auth expiration, server errors, or data parsing issues?
3. **Expiration rate** -- how often does the system kill your task before completion? If frequently, your sync operation may be too long for the allotted background time. Consider breaking it into smaller incremental syncs.
4. **HTTP status codes** -- if `performSync` uses URLSession, remember that URLSession does not throw for HTTP 4xx/5xx responses. A `500` response returns `(Data, URLResponse)` successfully. You must validate the status code explicitly inside `performSync`.
