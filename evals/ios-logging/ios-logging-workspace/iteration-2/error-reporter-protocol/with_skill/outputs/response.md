Your tech lead is right. Calling `SentrySDK.capture()` directly throughout your codebase is a well-known anti-pattern in iOS development. Here is why, and what you should do instead.

## The Problems with Direct SDK Calls

### 1. Vendor Lock-In

Every call site is coupled to Sentry's API. If you ever need to switch to Crashlytics, Datadog, or any other provider -- or even just upgrade to a breaking Sentry SDK version -- you must find and update every single call scattered across your codebase. In a large project this can mean dozens or hundreds of changes.

### 2. Untestable Error Reporting

You cannot unit test that errors are being reported correctly. `SentrySDK.capture()` is a concrete static call with no way to substitute a mock or spy in tests. You end up either skipping those tests entirely or spinning up the real SDK in your test target.

### 3. Inconsistent Error Context

When every developer writes their own `SentrySDK.capture()` call, there is no guarantee that error context (user ID, screen name, operation type, breadcrumbs) is attached consistently. Some call sites will include rich metadata, others will pass a bare error with no context, making production debugging much harder.

### 4. No Composite Reporting

Many production apps need to report to multiple backends -- for example, Sentry for crash reporting and PostHog for product analytics. With direct SDK calls you would need to add a second call at every site, doubling the maintenance burden.

### 5. Missing the Local Logging Half

Direct `SentrySDK.capture()` calls typically skip the local `os.Logger` step. Production error handling should always do two things: log locally with `os.Logger` (with privacy annotations) for on-device diagnostics, and report remotely to the crash SDK. Direct SDK calls encourage skipping the first half.

## The Correct Pattern: ErrorReporter Protocol

The fix is to define a protocol that abstracts any crash reporting SDK, then call the abstraction everywhere instead of the concrete SDK:

```swift
protocol ErrorReporter: Sendable {
    func recordNonFatal(_ error: Error, context: [String: Any])
    func addBreadcrumb(message: String, category: String, level: BreadcrumbLevel, data: [String: Any]?)
    func setUserID(_ userID: String?)
    func setCustomKey(_ key: String, value: Any)
    func log(_ message: String)
}
```

Then you create a concrete implementation that wraps Sentry:

```swift
final class SentryErrorReporter: ErrorReporter {
    func recordNonFatal(_ error: Error, context: [String: Any]) {
        SentrySDK.capture(error: error) { scope in
            for (key, value) in context {
                scope.setExtra(value: value, key: key)
            }
        }
    }

    func addBreadcrumb(message: String, category: String, level: BreadcrumbLevel, data: [String: Any]?) {
        let crumb = Breadcrumb(level: sentryLevel(level), category: category)
        crumb.message = message
        crumb.data = data
        SentrySDK.addBreadcrumb(crumb)
    }

    // ... remaining methods wrap Sentry APIs
}
```

Now the only file that imports `SentrySwift` is `SentryErrorReporter.swift`. Every other file in your codebase calls the protocol:

```swift
catch {
    // 1. Local structured log with privacy annotations
    Logger.networking.error("Sync failed: \(error.localizedDescription, privacy: .public)")

    // 2. Remote reporting through the abstraction
    ErrorReporter.shared.recordNonFatal(error, context: ["operation": "sync"])
}
```

## What This Gives You

- **Swap vendors in one file.** Write a `CrashlyticsErrorReporter` or `DatadogErrorReporter` conforming to the same protocol, change the assignment of `ErrorReporter.shared`, and the entire app switches over.
- **Testability.** Inject a `MockErrorReporter` in unit tests to assert that specific errors are captured with the expected context.
- **Consistent metadata.** The protocol's `context` parameter enforces that every call site passes structured context, and you can add default enrichment (user ID, app version, screen name) inside the implementation.
- **Composite reporting.** Use a `CompositeErrorReporter` that fans out to multiple backends without changing any call site:

```swift
final class CompositeErrorReporter: ErrorReporter {
    private let reporters: [ErrorReporter]

    init(_ reporters: ErrorReporter...) {
        self.reporters = reporters
    }

    func recordNonFatal(_ error: Error, context: [String: Any]) {
        reporters.forEach { $0.recordNonFatal(error, context: context) }
    }
    // ... delegate all methods
}
```

## Summary

Direct `SentrySDK.capture()` calls create vendor lock-in, prevent testing, produce inconsistent error context, and make multi-backend reporting painful. The fix is an `ErrorReporter` protocol with a single concrete Sentry implementation. Only that one implementation file should ever import the Sentry SDK. The rest of your codebase calls the abstraction, giving you testability, consistent context, and the ability to swap or compose backends by changing a single line.
