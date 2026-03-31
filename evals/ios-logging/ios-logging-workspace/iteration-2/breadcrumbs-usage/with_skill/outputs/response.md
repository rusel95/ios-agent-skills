# Breadcrumbs in Crash Reporting

## What Are Breadcrumbs?

Breadcrumbs are timestamped events that are buffered locally on the device and automatically attached to the next error or crash report sent to your crash reporting SDK (Sentry, Crashlytics, etc.). They answer the critical debugging question: **"What was the user doing right before this broke?"**

When a crash or non-fatal error occurs, the crash report includes not just the stack trace, but the trail of breadcrumbs leading up to it. This gives you a chronological timeline of user actions, navigation events, network calls, and custom markers that preceded the failure -- turning a cryptic stack trace into a story you can follow.

Crash SDKs typically auto-capture some breadcrumbs (e.g., navigation events, network requests, UI interactions), but the most valuable breadcrumbs are the ones you add manually at domain-specific decision points that the SDK cannot infer on its own.

## When to Add Breadcrumbs Manually

Add manual breadcrumbs **before risky or stateful operations** where knowing the context would be essential for debugging a subsequent failure. The key scenarios are:

### 1. Database Migrations

A failed migration can corrupt data or crash the app on every subsequent launch. Knowing which migration step was attempted is critical.

```swift
ErrorReporter.shared.addBreadcrumb(
    message: "Starting Core Data migration v2->v3",
    category: "database",
    level: .info,
    data: ["storeSize": storeFileSize]
)
```

### 2. Payment and Checkout Flows

Financial operations involve multiple steps (cart validation, payment processing, receipt generation). A breadcrumb trail shows exactly how far the user got.

```swift
ErrorReporter.shared.addBreadcrumb(
    message: "User initiated checkout",
    category: "payment",
    level: .info,
    data: ["cartItems": 3, "total": 99.99]
)
```

### 3. Authentication Flows

Auth flows involve redirects, token exchanges, and session creation -- multiple points where things can silently fail.

```swift
ErrorReporter.shared.addBreadcrumb(
    message: "Starting OAuth flow",
    category: "auth",
    level: .info,
    data: ["provider": "apple"]
)
```

### 4. Retry Attempts

When using retry logic with exponential backoff, each failed attempt should leave a breadcrumb so that the final failure report shows the full retry history.

```swift
ErrorReporter.shared.addBreadcrumb(
    message: "Retry attempt \(attempt) failed",
    category: "network",
    level: .warning,
    data: ["attempt": attempt, "operation": operation, "error": "\(error)"]
)
```

### 5. Background Task Lifecycle

Background tasks can be killed by the system at any time. Breadcrumbs mark how far the task progressed before expiration.

```swift
ErrorReporter.shared.addBreadcrumb(
    message: "BGTask expired",
    category: "background",
    level: .warning,
    data: nil
)
```

### 6. Any Multi-Step Operation Where Partial Completion Matters

This includes onboarding flows, file sync processes, data import/export, deep link resolution, and feature flag evaluation. If the operation has multiple stages and a failure at stage 3 looks different from a failure at stage 1, add breadcrumbs at each stage.

## Implementation via the ErrorReporter Protocol

Rather than calling Sentry or Crashlytics APIs directly throughout your codebase, breadcrumbs should go through a protocol-based abstraction:

```swift
protocol ErrorReporter: Sendable {
    func addBreadcrumb(
        message: String,
        category: String,
        level: BreadcrumbLevel,
        data: [String: Any]?
    )
    // ... other methods
}

enum BreadcrumbLevel: String, Sendable {
    case debug, info, warning, error, fatal
}
```

Each SDK implements this differently under the hood. Sentry supports structured breadcrumbs with categories, levels, and arbitrary data dictionaries. Crashlytics breadcrumbs are plain log strings (`Crashlytics.crashlytics().log("[\(category)] \(message)")`), so structured data is flattened. Using the protocol means your call sites stay identical regardless of which backend you use.

## Key Guidelines

- **Add breadcrumbs before the risky operation, not after.** If the operation crashes the process, a breadcrumb added afterward will never be recorded.
- **Use meaningful categories** (`"database"`, `"payment"`, `"auth"`, `"network"`, `"background"`) to make breadcrumb trails filterable in your crash dashboard.
- **Include relevant data** but avoid PII. Store sizes, item counts, provider names, and attempt numbers are useful. User emails, passwords, and payment details must never appear in breadcrumb data.
- **Breadcrumbs are not a replacement for Logger or recordNonFatal.** They complement structured logging (`os.Logger`) and non-fatal error reporting. Use all three together: Logger for local diagnostics, breadcrumbs for crash context, and `recordNonFatal` for the error itself.
